import time
import numpy as np

from .view_base import ViewBase



_wheel_refresh_time = 0.1

# TODO sam : check the on_params_changed in change params and remove initialize_plot()


class WaveformView(ViewBase):
    _supported_backend = ['qt', 'panel']

    _settings = [
        {'name': 'overlap', 'type': 'bool', 'value': True},
        {'name': 'plot_selected_spike', 'type': 'bool', 'value': False }, # true here can be very slow because it loads traces
        {'name': 'auto_zoom_on_unit_selection', 'type': 'bool', 'value': True},
        {'name': 'show_only_selected_cluster', 'type': 'bool', 'value': True},
        {'name': 'plot_limit_for_flatten', 'type': 'bool', 'value': True },
        {'name': 'fillbetween', 'type': 'bool', 'value': True },
        {'name': 'show_channel_id', 'type': 'bool', 'value': False},
        {'name': 'sparse_display', 'type': 'bool', 'value' : True },
    ]
    
    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        num_chan = len(self.controller.channel_ids)
        self.xvect = np.zeros((num_chan, width), dtype='float32')
        self.contact_location = self.controller.get_contact_location().copy()
        xpos = self.contact_location[:,0]
        ypos = self.contact_location[:,1]
        unique_x = np.sort(np.unique(np.round(xpos)))
        if unique_x.size>1:
            self.delta_x = np.min(np.diff(unique_x))
        else:
            self.delta_x = 40. # um
        unique_y = np.sort(np.unique(np.round(ypos)))
        if unique_y.size>1:
            self.delta_y = np.min(np.diff(unique_y))
        else:
            self.delta_y = 40. # um
        self.factor_y = .05
        self.factor_x = 1.0
        espx = self.delta_x / 2.5
        for chan_ind, chan_id in enumerate(self.controller.channel_ids):
            x, y = self.contact_location[chan_ind, :]
            self.xvect[chan_ind, :] = np.linspace(x-espx, x+espx, num=width)
        self.wf_min, self.wf_max = self.controller.get_waveforms_range()

        self.last_wheel_event_time = None


    def get_common_channels(self):
        sparse = self.settings['sparse_display']
        visible_unit_ids = self.controller.get_visible_unit_ids()
        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                common_channel_indexes = None
        else:
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype='int64')

        return common_channel_indexes

    def get_spike_waveform(self, ind):
        seg_num = self.controller.spikes['segment_index'][ind]
        peak_ind = self.controller.spikes['sample_index'][ind]
        
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        
        # TODO handle return_scaled
        wf = self.controller.get_traces(
            trace_source='preprocessed', 
            segment_index=seg_num, 
            start_frame=peak_ind - nbefore, end_frame=peak_ind + nafter,
        )
        return wf, width

    def get_xvectors_not_overlap(self, xvectors, num_visible_units):
        num_x_samples = xvectors.shape[1]
        if not self.settings["overlap"] and num_visible_units > 1:
            xvects = []
            # split xvectors into sub-vectors based on the number of visible units
            num_samples_per_unit = int(num_x_samples // num_visible_units)
            for i in range(num_visible_units):
                sample_start = i * num_samples_per_unit
                sample_end = min((i + 1) * num_samples_per_unit, len(xvectors[0])) - 1
                xvects.append(np.array([np.linspace(x[sample_start], x[sample_end], num_x_samples, endpoint=True) for x in xvectors]))
        else:
            xvects = [xvectors] * num_visible_units
        return xvects


    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import add_stretch_to_qtoolbar
        
        self.layout = QT.QVBoxLayout()
        

        tb = self.qt_widget.view_toolbar
        
        #Mode flatten or geometry
        self.combo_mode = QT.QComboBox()
        tb.addWidget(self.combo_mode)
        self.mode = 'geometry'
        self.combo_mode.addItems([ 'geometry', 'flatten'])
        self.combo_mode.currentIndexChanged.connect(self._qt_on_combo_mode_changed)
        add_stretch_to_qtoolbar(tb)
        
        but = QT.QPushButton('scale')
        but.clicked.connect(self._qt_zoom_range)
        tb.addWidget(but)

        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        self._qt_initialize_plot()
        
        self.alpha = 60
    
    
    def _qt_on_combo_mode_changed(self):
        self.mode = str(self.combo_mode.currentText())
        self._qt_initialize_plot()
        self.refresh()
    
    # def _qt_on_settings_changed(self, params, changes):
    #     for param, change, data in changes:
    #         if change != 'value': continue
    #     self.refresh()

    def _qt_initialize_plot(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleclickAndGain
        
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        
        self.viewBox1 = ViewBoxHandlingDoubleclickAndGain()
        self.viewBox1.disableAutoRange()

        grid = pg.GraphicsLayout(border=(100,100,100))
        self.graphicsview.setCentralItem(grid)
        
        self.plot1 = grid.addPlot(row=0, col=0, rowspan=2, viewBox=self.viewBox1)
        self.plot1.hideButtons()
        self.plot1.showAxis('left', True)

        self.curve_one_waveform = pg.PlotCurveItem([], [], pen=pg.mkPen(QT.QColor( 'white'), width=1), connect='finite')
        self.plot1.addItem(self.curve_one_waveform)
        
        if self.mode=='flatten':
            grid.nextRow()
            grid.nextRow()
            self.viewBox2 = ViewBoxHandlingDoubleclickAndGain()
            self.viewBox2.disableAutoRange()
            self.plot2 = grid.addPlot(row=2, col=0, rowspan=1, viewBox=self.viewBox2)
            self.plot2.hideButtons()
            self.plot2.showAxis('left', True)
            self.viewBox2.setXLink(self.viewBox1)
            
            self._common_channel_indexes_flat = None

        elif self.mode=='geometry':
            self.plot2 = None

        self._x_range = None
        self._y1_range = None
        self._y2_range = None
        
        self.viewBox1.gain_zoom.connect(self._qt_gain_zoom)
        self.viewBox1.limit_zoom.connect(self._qt_limit_zoom)
        
        self.viewBox1.widen_narrow.connect(self._qt_widen_narrow)

        shortcut_overlap = QT.QShortcut(self.qt_widget)
        shortcut_overlap.setKey(QT.QKeySequence("ctrl+o"))
        shortcut_overlap.activated.connect(self.toggle_overlap)

    def toggle_overlap(self):
        self.settings['overlap'] = not self.settings['overlap']
        self.refresh()
        
    def _qt_widen_narrow(self, factor_ratio):
        if self.mode=='geometry':
            self.factor_x *= factor_ratio
            self._qt_refresh(keep_range=True)

    def _qt_gain_zoom(self, factor_ratio):
        if self.mode=='geometry':
            self.factor_y *= factor_ratio
            self._qt_refresh(keep_range=True)
    
    def _qt_limit_zoom(self, factor_ratio):
        if self.mode=='geometry':
            l0, l1 = self._x_range
            mid = (l0 + l1) / 2.
            hw = (l1 - l0) / 2.
            l0  = mid - hw * factor_ratio
            l1  = mid + hw * factor_ratio
            self._x_range = (l0, l1)
            self.plot1.setXRange(*self._x_range, padding = 0.0)

    
    def _qt_zoom_range(self):
        self._x_range = None
        self._y1_range = None
        self._y2_range = None
        self._qt_refresh(keep_range=False)
    
    def _qt_refresh(self, keep_range=False):
        
        if not hasattr(self, 'viewBox1'):
            self._qt_initialize_plot()
        
        if not hasattr(self, 'viewBox1'):
            return
        
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size
        
        dict_visible_units = {k:False for k in self.controller.unit_ids}
        if self.settings['show_only_selected_cluster'] and n_selected==1:
            ind = selected_inds[0]
            unit_index = self.controller.spikes[ind]['unit_index']
            unit_id = self.controller.unit_ids[unit_index]
            dict_visible_units[unit_id] = True
        else:
            for unit_id in self.controller.get_visible_unit_ids():
                dict_visible_units[unit_id] = True
        
        if self.mode=='flatten':
            self.plot1.setAspectLocked(lock=False, ratio=None)
            self._qt_refresh_mode_flatten(dict_visible_units, keep_range)
        elif self.mode=='geometry':
            self.plot1.setAspectLocked(lock=True, ratio=1)
            self._qt_refresh_mode_geometry(dict_visible_units, keep_range)
        
        if self.controller.with_traces:
            self._qt_refresh_one_spike()
    
    def _qt_refresh_mode_flatten(self, dict_visible_units, keep_range):
        import pyqtgraph as pg
        from .myqt import QT
        if self._x_range is not None and keep_range:
            #this may change with pyqtgraph
            self._x_range = tuple(self.viewBox1.state['viewRange'][0])
            self._y1_range = tuple(self.viewBox1.state['viewRange'][1])
            self._y2_range = tuple(self.viewBox2.state['viewRange'][1])
        
        
        self.plot1.clear()
        self.plot2.clear()
        self.plot1.addItem(self.curve_one_waveform)
        
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        
        
        sparse = self.settings['sparse_display']
        
        visible_unit_ids = [unit_id for unit_id, v in dict_visible_units.items() if v ]
        
        
        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                return
        else:
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype='int64')
        
        self._common_channel_indexes_flat = common_channel_indexes
        
        #lines
        def addSpan(plot):
            white = pg.mkColor(255, 255, 255, 20)
            for i, c in enumerate(common_channel_indexes):
                if i%2==1:
                    region = pg.LinearRegionItem([width*i, width*(i+1)-1], movable = False, brush = white)
                    plot.addItem(region, ignoreBounds=True)
                    for l in region.lines:
                        l.setPen(white)
                vline = pg.InfiniteLine(pos = nbefore + width*i, angle=90, movable=False, pen = pg.mkPen('w'))
                plot.addItem(vline)
        
        if self.settings['plot_limit_for_flatten']:
            addSpan(self.plot1)
            addSpan(self.plot2)
        
        shape = (width, len(common_channel_indexes))
        xvect = np.arange(shape[0]*shape[1])
        min_std = 0
        max_std = 0
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not dict_visible_units[unit_id]:
                continue
            
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            template_std = self.controller.templates_std[unit_index, :, :][:, common_channel_indexes]
            
            color = self.get_unit_color(unit_id)
            curve = pg.PlotCurveItem(xvect, template_avg.T.flatten(), pen=pg.mkPen(color, width=2))
            self.plot1.addItem(curve)
            
            
            if self.settings['fillbetween']:
                color2 = QT.QColor(color)
                color2.setAlpha(self.alpha)
                curve1 = pg.PlotCurveItem(xvect, template_avg.T.flatten() + template_std.T.flatten(), pen=color2)
                curve2 = pg.PlotCurveItem(xvect, template_avg.T.flatten() - template_std.T.flatten(), pen=color2)
                self.plot1.addItem(curve1)
                self.plot1.addItem(curve2)
                
                fill = pg.FillBetweenItem(curve1=curve1, curve2=curve2, brush=color2)
                self.plot1.addItem(fill)
            
            if template_std is not None:
                template_std_flatten = template_std.T.flatten()
                curve = pg.PlotCurveItem(xvect, template_std_flatten, pen=color)
                self.plot2.addItem(curve)
                min_std = min(min_std,template_std_flatten.min())
                max_std = max(max_std,template_std_flatten.max())
        if self.settings['show_channel_id']:
            for i, chan_ind in enumerate(common_channel_indexes):
                chan_id = self.controller.channel_ids[chan_ind]
                itemtxt = pg.TextItem(f'{chan_id}', anchor=(.5,.5), color='#FFFF00')
                itemtxt.setFont(QT.QFont('', pointSize=12))
                self.plot1.addItem(itemtxt)
                itemtxt.setPos(width * i +nbefore, 0)

        
        if self._x_range is None or not keep_range:
            if xvect.size>0:
                self._x_range = xvect[0], xvect[-1]
                self._y1_range = self.wf_min*1.1, self.wf_max*1.1
                self._y2_range = min_std*0.9, max_std*1.1
                
        if self._x_range is not None:
            self.plot1.setXRange(*self._x_range, padding = 0.0)
            self.plot1.setYRange(*self._y1_range, padding = 0.0)
            self.plot2.setYRange(*self._y2_range, padding = 0.0)

    def _qt_refresh_mode_geometry(self, dict_visible_units, keep_range):
        from .myqt import QT
        import pyqtgraph as pg

        if self._x_range is not None and keep_range:
            #this may change with pyqtgraph
            self._x_range = tuple(self.viewBox1.state['viewRange'][0])
            self._y1_range = tuple(self.viewBox1.state['viewRange'][1])

        self.plot1.clear()
        
        if self.xvect is None:
            return

        sparse = self.settings['sparse_display']
        visible_unit_ids = self.controller.get_visible_unit_ids()
        visible_unit_indices = self.controller.get_visible_unit_indices()
        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                return
        else:
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype='int64')

        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter

        if width != self.xvect.shape[1]:
            self._qt_initialize_plot()
        
        self.plot1.addItem(self.curve_one_waveform)

        xvectors = self.xvect[common_channel_indexes, :] * self.factor_x
        xvects = self.get_xvectors_not_overlap(xvectors, len(visible_unit_ids))


        for (xvect, unit_index, unit_id) in zip(xvects, visible_unit_indices, visible_unit_ids):
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            
            ypos = self.contact_location[common_channel_indexes,1]
            
            wf = template_avg
            wf = wf * self.factor_y * self.delta_y + ypos[None, :]
            
            connect = np.ones(wf.shape, dtype='bool')
            connect[0, :] = 0
            connect[-1, :] = 0

            # color = self.controller.qcolors.get(unit_id, QT.QColor( 'white'))
            color = self.get_unit_color(unit_id)
            
            curve = pg.PlotCurveItem(xvect.flatten(), wf.T.flatten(), pen=pg.mkPen(color, width=2), connect=connect.T.flatten())
            self.plot1.addItem(curve)
        
        if self.settings['show_channel_id']:
            for chan_ind in common_channel_indexes:
                chan_id = self.controller.channel_ids[chan_ind]
                x, y = self.contact_location[chan_ind, : ]
                itemtxt = pg.TextItem(f'{chan_id}', anchor=(.5,.5), color='#FFFF00')
                itemtxt.setFont(QT.QFont('', pointSize=12))
                self.plot1.addItem(itemtxt)
                itemtxt.setPos(x, y)
        
        if self._x_range is None or not keep_range:

            x_margin =50
            y_margin =150
            self._x_range = np.min(xvects) - x_margin , np.max(xvects) + x_margin
            visible_mask = self.controller.get_units_visibility_mask()
            visible_pos = self.controller.unit_positions[visible_mask, :]
            self._y1_range = np.min(visible_pos[:,1]) - y_margin , np.max(visible_pos[:,1]) + y_margin
        
        self.plot1.setXRange(*self._x_range, padding = 0.0)
        self.plot1.setYRange(*self._y1_range, padding = 0.0)
        
    
    def _qt_refresh_one_spike(self):
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size

        if n_selected != 1 or not self.settings['plot_selected_spike']: 
            self.curve_one_waveform.setData([], [])
            return
        
        selected_inds = self.controller.get_indices_spike_selected()
        ind = selected_inds[0]

        common_channel_indexes = self.get_common_channels()
        if common_channel_indexes is None:
            self.curve_one_waveform.setData([], [])
            return
        wf, width = self.get_spike_waveform(ind)
        wf = wf[:, common_channel_indexes]
        
        if wf.shape[0] == width:
            #this avoid border bugs
            if self.mode=='flatten':
                wf = wf.T.flatten()
                xvect = np.arange(wf.size)
                self.curve_one_waveform.setData(xvect, wf)
            elif self.mode=='geometry':
                ypos = self.contact_location[common_channel_indexes, 1]
                wf = wf*self.factor_y*self.delta_y + ypos[None, :]
                
                connect = np.ones(wf.shape, dtype='bool')
                connect[0, :] = 0
                connect[-1, :] = 0
                xvect = self.xvect[common_channel_indexes, :]

                self.curve_one_waveform.setData(xvect.flatten(), wf.T.flatten(), connect=connect.T.flatten())
    
    def _qt_on_spike_selection_changed(self):
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size
        if n_selected == 1 and self.settings['plot_selected_spike']:
            self._qt_refresh(keep_range=True)
        else:
            # remove the line
            self.curve_one_waveform.setData([], [])
    
    def _qt_on_unit_visibility_changed(self):
        keep_range = not(self.settings['auto_zoom_on_unit_selection'])
        self._qt_refresh(keep_range=keep_range)

    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import WheelZoomTool, Range1d
        from bokeh.events import MouseWheel

        from .utils_panel import _bg_color, KeyboardShortcut, KeyboardShortcuts

        contact_locations = self.controller.get_contact_location()
        x = contact_locations[:, 0]
        y = contact_locations[:, 1]

        self.mode_selector = pn.widgets.Select(name='mode', options=['geometry', 'flatten'])
        self.mode_selector.param.watch(self._panel_on_mode_selector_changed, "value")

        # Create figures with basic tools
        self.figure_geom = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset",
            y_axis_type="auto",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
        )
        self.zoom_tool = WheelZoomTool()
        self.figure_geom.toolbar.logo = None
        self.figure_geom.add_tools(self.zoom_tool)
        self.figure_geom.toolbar.active_scroll = None
        self.figure_geom.grid.visible = False
        self.figure_geom.on_event(MouseWheel, self._panel_gain_zoom)
        self.figure_geom.x_range = Range1d(np.min(x) - 50, np.max(x) + 50)
        self.figure_geom.y_range = Range1d(np.min(y) - 50, np.max(y) + 50)

        self.lines_geom = None

        # figures for flatten
        self.shared_x_range = Range1d(start=0, end=1500)
        self.figure_avg = bpl.figure(
            sizing_mode="stretch_both",
            tools="wheel_zoom,reset",
            active_scroll="wheel_zoom",
            y_axis_type="auto",
            x_range=self.shared_x_range,
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"},
        )
        self.figure_avg.toolbar.logo = None
        self.figure_avg.grid.visible = False
        self.lines_avg = {}

        self.figure_std = bpl.figure(
            sizing_mode="stretch_both",
            tools="",
            y_axis_type="auto",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            x_range=self.shared_x_range,
            styles={"flex": "0.5"},
        )
        self.figure_std.toolbar.logo = None
        self.figure_std.grid.visible = False
        self.figure_std.toolbar.active_scroll = None
        self.lines_std = {}

        self.lines_wfs = []

        self.figure_pane = pn.Column(
            self.figure_geom
        )

        # overlap shortcut
        shortcuts = [KeyboardShortcut(name="overlap", key="o", ctrlKey=True)]
        shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        shortcuts_component.on_msg(self._panel_handle_shortcut)

        self.layout = pn.Column(
            pn.Row(
                self.mode_selector
            ),
            self.figure_pane,
            shortcuts_component,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both"
        )

    def _panel_refresh(self, keep_range=False):
        self.mode = self.mode_selector.value
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size
        dict_visible_units = {k: False for k in self.controller.unit_ids}
        if self.settings['show_only_selected_cluster'] and n_selected == 1:
            ind = selected_inds[0]
            unit_index = self.controller.spikes[ind]['unit_index']
            unit_id = self.controller.unit_ids[unit_index]
            dict_visible_units[unit_id] = True
        else:
            for unit_id in self.controller.get_visible_unit_ids():
                dict_visible_units[unit_id] = True

        if self.mode=='geometry':
            # zoom factor is reset
            if self.settings["auto_zoom_on_unit_selection"]:
                self.factor_x = 1.0
                self.factor_y = .05
            self._panel_refresh_mode_geometry(dict_visible_units, keep_range=keep_range)
        elif self.mode=='flatten':
            self._panel_refresh_mode_flatten(dict_visible_units, keep_range=keep_range)

        self._panel_refresh_one_spike()


    def _panel_on_mode_selector_changed(self, event):
        import panel as pn
        self.mode = self.mode_selector.value
        self.layout[1] = self.figure_geom if self.mode == 'geometry' else pn.Column(self.figure_avg, self.figure_std)
        self.refresh()

    def _panel_gain_zoom(self, event):
        self.figure_geom.toolbar.active_scroll = None
        current_time = time.perf_counter()
        if self.last_wheel_event_time is not None:
            time_elapsed = current_time - self.last_wheel_event_time
        else:
            time_elapsed = 1000
        if time_elapsed > _wheel_refresh_time:
            modifiers = event.modifiers
            if modifiers["shift"]:
                self.figure_geom.toolbar.active_scroll = self.zoom_tool
            elif modifiers["alt"]:
                self.figure_geom.toolbar.active_scroll = None
                if self.mode == 'geometry':
                    factor = 1.3 if event.delta > 0 else 1 / 1.3
                    self.factor_x *= factor
                    self._panel_refresh_mode_geometry(keep_range=True)
            elif not modifiers["ctrl"]:
                self.figure_geom.toolbar.active_scroll = None
                if self.mode == 'geometry':
                    factor = 1.3 if event.delta > 0 else 1 / 1.3
                    self.factor_y *= factor
                    self._panel_refresh_mode_geometry(keep_range=True)
        else:
            # Ignore the event if it occurs too quickly
            self.figure_geom.toolbar.active_scroll = None
        self.last_wheel_event_time = current_time

    def _panel_refresh_mode_geometry(self, dict_visible_units=None, keep_range=False):
        # this clear the figure
        self.figure_geom.renderers = []
        self.lines_geom = None
        dict_visible_units = dict_visible_units or self.controller.get_dict_unit_visible()

        common_channel_indexes = self.get_common_channels()
        if common_channel_indexes is None:
            return
        
        visible_unit_ids = self.controller.get_visible_unit_ids()
        visible_unit_indices = self.controller.get_visible_unit_indices()

        if len(visible_unit_ids) == 0:
            return

        xvectors = self.xvect[common_channel_indexes, :] * self.factor_x
        xvects = self.get_xvectors_not_overlap(xvectors, len(visible_unit_ids))

        xs = []
        ys = []
        colors = []
        for (xvect, unit_index, unit_id) in zip(xvects, visible_unit_indices, visible_unit_ids):
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            
            ypos = self.contact_location[common_channel_indexes,1]
            
            wf = template_avg
            wf = wf * self.factor_y * self.delta_y + ypos[None, :]
            # this disconnects each channel
            wf[0, :] = np.nan

            color = self.get_unit_color(unit_id)

            xs.append(xvect.flatten())
            ys.append(wf.T.flatten())
            colors.append(color)

        self.lines_geom = self.figure_geom.multi_line(xs, ys, line_color=colors, line_width=2)

        if self.settings["plot_selected_spike"]:
            self._panel_refresh_one_spike()

        if not keep_range:
            self.figure_geom.x_range.start = np.min(xvects) - 50
            self.figure_geom.x_range.end = np.max(xvects) + 50
            self.figure_geom.y_range.start = np.min(ypos) - 50
            self.figure_geom.y_range.end = np.max(ypos) + 50

    def _panel_refresh_mode_flatten(self, dict_visible_units=None, keep_range=False):
        from bokeh.models import Span
        # this clear the figure
        self.figure_avg.renderers = []
        self.figure_std.renderers = []
        self.lines_avg = {}
        self.lines_std = {}
        dict_visible_units = dict_visible_units or self.controller.get_dict_unit_visible()

        common_channel_indexes = self.get_common_channels()
        if common_channel_indexes is None:
            return

        for unit_index, (unit_id, visible) in enumerate(dict_visible_units.items()):
            if not visible:
                continue
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            template_std = self.controller.templates_std[unit_index, :, :][:, common_channel_indexes]
            nsamples, nchannels = template_avg.shape

            y_avg = template_avg.T.flatten()
            y_std = template_std.T.flatten()
            x = np.arange(y_avg.size)
            
            color = self.get_unit_color(unit_id)
            self.lines_avg[unit_id] = self.figure_avg.line("x", "y", source=dict(x=x, y=y_avg), line_color=color, line_width=2)
            self.lines_std[unit_id] = self.figure_std.line("x", "y", source=dict(x=x, y=y_std), line_color=color, line_width=2)

            # add dashed vertical lines corresponding to the channels
            for ch in range(nchannels - 1):
                # Add vertical line at x=5
                vline = Span(location=(ch + 1) * nsamples, dimension='height', line_color='grey', line_width=1, line_dash='dashed')
                self.figure_avg.add_layout(vline)
                self.figure_std.add_layout(vline)

        if self.settings["plot_selected_spike"]:
            self._panel_refresh_one_spike()

        self.shared_x_range.end = x[-1]
        self.figure_avg.x_range = self.shared_x_range
        self.figure_std.x_range = self.shared_x_range

    def _panel_refresh_one_spike(self):
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size
        # clean existing lines
        for line in self.lines_wfs:
            if line in self.figure_geom.renderers:
                self.figure_geom.renderers.remove(line)
            if line in self.figure_avg.renderers:
                self.figure_avg.renderers.remove(line)

        if self.settings["plot_selected_spike"] and n_selected == 1:
            ind = selected_inds[0]
            common_channel_indexes = self.get_common_channels()
            wf, width = self.get_spike_waveform(ind)
            wf = wf[:, common_channel_indexes]
        
            if wf.shape[0] == width:
                #this avoid border bugs
                if self.mode=='flatten':
                    wf = wf.T.flatten()
                    x = np.arange(wf.size)
                    
                    color = "white"
                    line = self.figure_avg.line("x", "y", source=dict(x=x, y=wf), line_color=color, line_width=0.5)
                    self.lines_wfs.append(line)
                elif self.mode=='geometry':
                    ypos = self.contact_location[common_channel_indexes,1]
            
                    wf = wf * self.factor_y * self.delta_y + ypos[None, :]
            
                    # this disconnect
                    wf[0, :] = np.nan
                    xvect = self.xvect[common_channel_indexes, :] * self.factor_x
                    
                    color = "white"
                    
                    source = {"x": xvect.flatten(), "y" : wf.T.flatten() }
                    line = self.figure_geom.line("x", "y", source=source, line_color=color, line_width=0.5)
                    self.lines_wfs.append(line)

    def _panel_on_spike_selection_changed(self):
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size
        if n_selected == 1 and self.settings['plot_selected_spike']:
            self._panel_refresh(keep_range=True)
        else:
            # remove the line
            for line in self.lines_wfs:
                if line in self.figure_geom.renderers:
                    self.figure_geom.renderers.remove(line)
                if line in self.figure_avg.renderers:
                    self.figure_avg.renderers.remove(line)

    def _panel_on_channel_visibility_changed(self):
        keep_range = not self.settings['auto_zoom_on_unit_selection']
        self._panel_refresh(keep_range=keep_range)

    def _panel_handle_shortcut(self, event):
        if event.data == "overlap":
            self.toggle_overlap()

WaveformView._gui_help_txt = """
## Waveform View

Display average template for visible units.
If one spike is selected (in spike list) then the spike is super-imposed (white trace)
(when the 'plot_selected_spike' setting is True)

There are 2 modes of display:
  * 'geometry' : snippets are displayed centered on the contact position
  * 'flatten' : snippets are concatenated in a flatten way (better to check the variance)

### Controls
* **mode** : change displaye mode (geometry or flatten)
* **ctrl + o** : toggle overlap mode
* **mouse wheel** : scale waveform amplitudes
* **alt + mouse wheel** : widen/narrow x axis
* **shift + mouse wheel** : zoom
"""

