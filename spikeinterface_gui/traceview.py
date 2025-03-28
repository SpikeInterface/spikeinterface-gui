import numpy as np
import time

from .view_base import ViewBase

from .utils_qt import add_stretch_to_qtoolbar


# This MixinViewTrace is used both in TraceView and TraceMapView) handling:
#   * toolbar
#   * time slider
#   * xsize
#   * zoom
#   * segment change
#   * 

class MixinViewTrace:
    ## Qt ##
    def _qt_create_toolbar(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import TimeSeeker

        tb = self.qt_widget.view_toolbar

        #Segment selection
        self.combo_seg = QT.QComboBox()
        tb.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {seg_index}' for seg_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self._qt_on_combo_seg_changed)
        add_stretch_to_qtoolbar(tb)
        
        # time slider
        self.timeseeker = TimeSeeker(show_slider=False)
        tb.addWidget(self.timeseeker)
        self.timeseeker.time_changed.connect(self._qt_seek)
        
        # winsize
        self.xsize = .5
        tb.addWidget(QT.QLabel(u'X size (s)'))
        self.spinbox_xsize = pg.SpinBox(value = self.xsize, bounds = [0.001, self.settings['xsize_max']],
                                        suffix = 's', siPrefix = True, step = 0.1, dec = True)
        self.spinbox_xsize.sigValueChanged.connect(self._qt_on_xsize_changed)
        tb.addWidget(self.spinbox_xsize)
        add_stretch_to_qtoolbar(tb)
        self.spinbox_xsize.sigValueChanged.connect(self.refresh)
        
        but = QT.QPushButton('auto scale')
        but.clicked.connect(self.auto_scale)

        tb.addWidget(but)
        
    def _qt_initialize_plot(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxForTrace


        self.viewBox = ViewBoxForTrace()
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        self.plot.showAxis('left', False)
        
        self.viewBox.doubleclicked.connect(self._qt_scatter_item_clicked)
        
        self.viewBox.gain_zoom.connect(self.apply_gain_zoom)
        self.viewBox.xsize_zoom.connect(self._qt_xsize_zoom)
        
        self.signals_curve = pg.PlotCurveItem(pen='#7FFF00', connect='finite')
        self.plot.addItem(self.signals_curve)

        self.channel_labels = []
        self.threshold_lines =[]
        for i, channel_id in enumerate(self.controller.channel_ids):
            label = pg.TextItem(f'{i}: {channel_id}', color='#FFFFFF', anchor=(0, 0.5), border=None, fill=pg.mkColor((128,128,128, 180)))
            self.plot.addItem(label)
            self.channel_labels.append(label)
        
        pen = pg.mkPen(color=(128,0,128, 120), width=3, style=QT.Qt.DashLine)
        self.selection_line = pg.InfiniteLine(pos = 0., angle=90, movable=False, pen = pen)
        self.plot.addItem(self.selection_line)
        self.selection_line.hide()
        
        self.gains = None
        self.offsets = None

    def _qt_update_scroll_limits(self):
        length = self.controller.get_num_samples(self.seg_index)
        t_start = 0.
        t_stop = length/self.controller.sampling_frequency
        self.timeseeker.set_start_stop(t_start, t_stop, seek=False)
        self.scroll_time.setMinimum(0)
        self.scroll_time.setMaximum(length)

    def _qt_change_segment(self, seg_index):
        #TODO: dirty because now seg_pos IS seg_index
        self.seg_index = seg_index

        self._qt_update_scroll_limits()
        if self.is_view_visible():
            self.refresh()

    def _qt_on_combo_seg_changed(self):
        s =  self.combo_seg.currentIndex()
        self._qt_change_segment(s)
    
    def _qt_on_xsize_changed(self):
        self.xsize = self.spinbox_xsize.value()
        if self.is_view_visible():
            self.refresh()

    def _qt_xsize_zoom(self, xmove):
        factor = xmove/100.
        newsize = self.xsize*(factor+1.)
        limits = self.spinbox_xsize.opts['bounds']
        if newsize>0. and newsize<limits[1]:
            self.spinbox_xsize.setValue(newsize)

    def _qt_on_scroll_time(self, val):
        sr = self.controller.sampling_frequency
        self.timeseeker.seek(val/sr)

    def _qt_seek_with_selected_spike(self):
        ind_selected = self.controller.get_indices_spike_selected()
        n_selected = ind_selected.size
        
        if self.settings['auto_zoom_on_select'] and n_selected==1:
            ind = ind_selected[0]
            peak_ind = self.controller.spikes[ind]['sample_index']
            seg_index = self.controller.spikes[ind]['segment_index']
            peak_time = peak_ind / self.controller.sampling_frequency
            unit_index = self.controller.spikes[ind]['unit_index']
            unit_id = self.controller.unit_ids[unit_index ]
            
            if seg_index != self.seg_index:
                self.combo_seg.setCurrentIndex(seg_index)
            
            self.spinbox_xsize.sigValueChanged.disconnect(self._qt_on_xsize_changed)
            self.spinbox_xsize.setValue(self.settings['zoom_size'])
            self.xsize = self.settings['zoom_size']
            self.spinbox_xsize.sigValueChanged.connect(self._qt_on_xsize_changed)
            
            self._qt_seek(peak_time)
            
        else:
            self.refresh()
    
    ## panel ##
    def _panel_create_toolbar(self):
        import panel as pn

        self.segment_selector = pn.widgets.Select(
            name="Segment",
            options=[f"Segment {i}" for i in range(self.controller.num_segments)],
            value=f"Segment {self.seg_index}",
        )

        # Window size control
        self.xsize_spinner = pn.widgets.FloatInput(
            name="Window Size (s)", value=self.xsize, start=0.001, end=self.settings['xsize_max'], step=0.1
        )

        # Auto scale button
        self.auto_scale_button = pn.widgets.Button(name="Auto Scale", button_type="default")

        # Time slider
        length = self.controller.get_num_samples(self.seg_index)
        t_start = 0
        t_stop = length / self.controller.sampling_frequency
        self.time_slider = pn.widgets.FloatSlider(name="Time (s)", start=t_start, end=t_stop, value=0, step=0.1)

        # TODO sam
        # Connect events
        self.segment_selector.param.watch(self._panel_on_segment_changed, "value")
        self.xsize_spinner.param.watch(self._panel_on_xsize_changed, "value")
        self.auto_scale_button.on_click(lambda event: self.auto_scale)
        self.time_slider.param.watch(self._panel_on_time_slider_changed, "value")

        # TODO generic toolbar
        # self.toolbar = pn.Column(
        #     pn.Row(self.segment_selector, self.xsize_spinner, self.auto_scale_button),
        #     pn.Row(self.time_slider, width=800),
        # )
        self.toolbar = pn.Row(
            self.segment_selector,
            self.xsize_spinner,
            self.auto_scale_button
        )

    def _panel_on_segment_changed(self, event):
        seg_index = int(event.new.split()[-1])
        self._panel_change_segment(seg_index)

    def _panel_change_segment(self, seg_index):
        self.seg_index = seg_index
        self.segment_selector.value = f"Segment {self.seg_index}"

        # Update time slider range
        length = self.controller.get_num_samples(self.seg_index)
        t_stop = length / self.controller.sampling_frequency
        self.time_slider.start = 0
        self.time_slider.end = t_stop
        self.time_slider.value = 0

        # # Update plot ranges
        # self.figure.x_range.start = 0
        # self.figure.x_range.end = t_stop

        # # Reset data sources
        # self.signal_source.data.update({"xs": [], "ys": [], "channel_id": []})

        # self.spike_source.data.update({"x": [], "y": [], "color": [], "unit_id": []})

        # # Reset selection line
        # self.selection_line.visible = False
        # self.selection_line.data_source.data.update({"x": [], "y": []})

        self.refresh()

    def _panel_on_xsize_changed(self, event):
        self.xsize = event.new
        self.refresh()

    def _panel_on_time_slider_changed(self, event):
        self.time_by_seg[self.seg_index] = event.new
        self.refresh()




class TraceView(ViewBase, MixinViewTrace):
    _supported_backend = ['qt', 'panel']

    _depend_on = ['recording']
    _settings = [
        {'name': 'auto_zoom_on_select', 'type': 'bool', 'value': True },
        {'name': 'zoom_size', 'type': 'float', 'value':  0.08, 'step' : 0.001 },
        {'name': 'plot_threshold', 'type': 'bool', 'value':  True },
        {'name': 'alpha', 'type': 'float', 'value' : 0.8, 'limits':(0, 1.), 'step':0.05 },
        {'name': 'xsize_max', 'type': 'float', 'value': 4.0, 'step': 1.0, 'limits':(1.0, np.inf)},
        {'name': 'max_visible_channel', 'type': 'int', 'value':  16},
    ]


    def __init__(self, controller=None, parent=None, backend="qt"):

        self.time_by_seg = np.array([0.]*controller.num_segments, dtype='float64')
        self.seg_index = 0
        self.mad = controller.noise_levels.astype("float32").copy()
        # we make the assumption that the signal is center on zero (HP filtered)
        self.med = np.zeros(self.mad.shape, dtype="float32")
        self.factor = 15.0
        self.xsize = 0.5


        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        MixinViewTrace.__init__(self)

    
    def on_channel_visibility_changed(self):
        self.refresh()

    def get_visible_channel_inds(self):
        # TODO add option to order by depth
        inds = self.controller.visible_channel_inds
        n_max =self.settings['max_visible_channel']
        if inds.size > n_max:
            inds = inds[:n_max]
        return inds
    
    def auto_scale(self):
        self.factor = 15.
        self.refresh()

    def apply_gain_zoom(self, factor_ratio):
        self.factor *= factor_ratio
        self.refresh()

    def get_data_in_chunk(self, t1, t2, segment_index):
        t_start = 0.0
        sr = self.controller.sampling_frequency

        ind1 = max(0, int((t1 - t_start) * sr))
        ind2 = min(self.controller.get_num_samples(segment_index), int((t2 - t_start) * sr))

        traces_chunk = self.controller.get_traces(segment_index=segment_index, start_frame=ind1, end_frame=ind2)

        sl = self.controller.segment_slices[segment_index]
        spikes_seg = self.controller.spikes[sl]
        i1, i2 = np.searchsorted(spikes_seg["sample_index"], [ind1, ind2])
        spikes_chunk = spikes_seg[i1:i2].copy()
        spikes_chunk["sample_index"] -= ind1

        visible_channel_inds = self.get_visible_channel_inds()
        
        data_curves = traces_chunk[:, visible_channel_inds].T.copy()

        if data_curves.dtype != "float32":
            data_curves = data_curves.astype("float32")
        
        n = visible_channel_inds.size
        gains = np.ones(n, dtype=float) * 1.0 / (self.factor * max(self.mad[visible_channel_inds]))
        offsets = np.arange(n)[::-1] - self.med[visible_channel_inds] * gains
        
        data_curves *= gains[:, None]
        data_curves += offsets[:, None]

        times_chunk = np.arange(traces_chunk.shape[0], dtype='float64')/self.controller.sampling_frequency+max(t1, 0)

        scatter_x = []
        scatter_y = []
        scatter_colors = []
        scatter_unit_ids = []

        global_to_local_chan_inds = np.zeros(self.controller.channel_ids.size, dtype='int64')
        global_to_local_chan_inds[visible_channel_inds] = np.arange(visible_channel_inds.size, dtype='int64')
        
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                continue

            inds = np.flatnonzero(spikes_chunk["unit_index"] == unit_index)
            if inds.size == 0:
                continue

            # Get spikes for this unit
            unit_spikes = spikes_chunk[inds]
            channel_inds = unit_spikes["channel_index"]
            sample_inds = unit_spikes["sample_index"]

            
            chan_mask = np.isin(channel_inds, visible_channel_inds)
            if not np.any(chan_mask):
                continue

            sample_inds = sample_inds[chan_mask]
            channel_inds = channel_inds[chan_mask]
            # Map channel indices to their positions in visible_channel_inds
            local_channel_inds = global_to_local_chan_inds[channel_inds]


            # Calculate y values using signal values
            x = times_chunk[sample_inds]
            y = data_curves[local_channel_inds, sample_inds]

            # This should both for qt (QTColor) and panel (html color)
            color = self.get_unit_color(unit_id)

            scatter_x.extend(x)
            scatter_y.extend(y)
            scatter_colors.extend([color] * len(x))
            scatter_unit_ids.extend([str(unit_id)] * len(x))

        return times_chunk, data_curves, scatter_x, scatter_y, scatter_colors, scatter_unit_ids



    # TODO sam refactor Qt and this
    def find_nearest_spike(self, x, segment_index, max_distance_samples=None):
        if max_distance_samples is None:
            max_distance_samples = self.controller.sampling_frequency // 30

        ind_click = int(x * self.controller.sampling_frequency)
        (in_seg,) = np.nonzero(self.controller.spikes["segment_index"] == segment_index)

        if len(in_seg) == 0:
            return None

        nearest = np.argmin(np.abs(self.controller.spikes[in_seg]["sample_index"] - ind_click))
        ind_spike_nearest = in_seg[nearest]
        sample_index = self.controller.spikes[ind_spike_nearest]["sample_index"]

        if np.abs(ind_click - sample_index) > max_distance_samples:
            return None

        return ind_spike_nearest



    ## qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg


        self.layout = QT.QVBoxLayout()
        # self.setLayout(self.layout)
        
        self._qt_create_toolbar()
        
        
        # create graphic view and 2 scroll bar
        g = QT.QGridLayout()
        self.layout.addLayout(g)
        self.graphicsview = pg.GraphicsView()
        g.addWidget(self.graphicsview, 0,1)

        MixinViewTrace._qt_initialize_plot(self)
        self.scatter = pg.ScatterPlotItem(size=10, pxMode = True)
        self.plot.addItem(self.scatter)

        self.scroll_time = QT.QScrollBar(orientation=QT.Qt.Horizontal)
        g.addWidget(self.scroll_time, 1,1)
        self.scroll_time.valueChanged.connect(self._qt_on_scroll_time)
        

        self._qt_update_scroll_limits()


    def _qt_on_settings_changed(self):
        # adjust xsize spinbox bounds, and adjust xsize if out of bounds
        self.spinbox_xsize.opts['bounds'] = [0.001, self.settings['xsize_max']]
        if self.xsize > self.settings['xsize_max']:
            self.spinbox_xsize.sigValueChanged.disconnect(self._qt_on_xsize_changed)
            self.spinbox_xsize.setValue(self.settings['xsize_max'])
            self.xsize = self.settings['xsize_max']
            self.spinbox_xsize.sigValueChanged.connect(self._qt_on_xsize_changed)
        
        # self.reset_gain_and_offset()
        self.refresh()

    def _qt_on_spike_selection_changed(self):
        MixinViewTrace._qt_seek_with_selected_spike(self)

    def _qt_scatter_item_clicked(self, x, y):
        # TODO sam : make it faster without boolean mask
        ind_click = int(x*self.controller.sampling_frequency )
        in_seg, = np.nonzero(self.controller.spikes['segment_index'] == self.seg_index)
        nearest = np.argmin(np.abs(self.controller.spikes[in_seg]['sample_index'] - ind_click))
        
        ind_spike_nearest = in_seg[nearest]
        sample_index = self.controller.spikes[ind_spike_nearest]['sample_index']
        
        if np.abs(ind_click - sample_index) > (self.controller.sampling_frequency // 30):
            return
        
        #~ self.controller.spikes['selected'][:] = False
        #~ self.controller.spikes['selected'][ind_spike_nearest] = True
        self.controller.set_indices_spike_selected([ind_spike_nearest])
        
        self.notify_spike_selection_changed()
        self.refresh()


    def _qt_refresh(self):
        self._qt_seek(self.time_by_seg[self.seg_index])

    def _qt_seek(self, t):
        from .myqt import QT
        import pyqtgraph as pg

        if self.qt_widget.sender() is not self.timeseeker:
            self.timeseeker.seek(t, emit=False)
        
        self.time_by_seg[self.seg_index] = t
        t1,t2 = t-self.xsize/3. , t+self.xsize*2/3.
        t_start = 0.
        sr = self.controller.sampling_frequency

        self.scroll_time.valueChanged.disconnect(self._qt_on_scroll_time)
        self.scroll_time.setValue(int(sr*t))
        self.scroll_time.setPageStep(int(sr*self.xsize))
        self.scroll_time.valueChanged.connect(self._qt_on_scroll_time)

        visible_channel_inds = self.get_visible_channel_inds()

        times_chunk, data_curves, scatter_x, scatter_y, scatter_colors, scatter_unit_ids = \
            self.get_data_in_chunk(t1, t2, self.seg_index)
        connect = np.ones(data_curves.shape, dtype='bool')
        connect[:, -1] = 0


        times_chunk_tile = np.tile(times_chunk, visible_channel_inds.size)
        self.signals_curve.setData(times_chunk_tile, data_curves.flatten(), connect=connect.flatten())

        self.scatter.setData(x=scatter_x, y=scatter_y, brush=scatter_colors)

        # TODO sam : scatter selection
        
        #channel labels
        for chan_ind, chan_id in enumerate(self.controller.channel_ids):
            self.channel_labels[chan_ind].hide()
        
        for i, chan_ind in enumerate(visible_channel_inds):
            self.channel_labels[chan_ind].setPos(t1, visible_channel_inds.size - 1 - i)
            self.channel_labels[chan_ind].show()

        #ranges
        self.plot.setXRange( t1, t2, padding = 0.0)
        self.plot.setYRange(-.5, visible_channel_inds.size-.5, padding = 0.0)


    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from .utils_panel import _bg_color
        from bokeh.models import ColumnDataSource, Range1d, HoverTool
        from bokeh.events import Tap, MouseWheel

        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="box_zoom,reset",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        
        length = self.controller.get_num_samples(self.seg_index)
        t_stop = length / self.controller.sampling_frequency
        # self.figure.x_range = Range1d(start=0, end=t_stop)
        # self.figure.y_range = Range1d(start=-0.5, end=len(self.controller.channel_ids) - 0.5)

        self.figure.grid.visible = False
        self.figure.toolbar.logo = None
        self.figure.on_event(MouseWheel, self._panel_gain_zoom)

        # Configure axes
        self.figure.xaxis.axis_label = "Time (s)"
        self.figure.xaxis.axis_label_text_color = "white"
        self.figure.xaxis.axis_line_color = "white"
        self.figure.xaxis.major_label_text_color = "white"
        self.figure.xaxis.major_tick_line_color = "white"
        self.figure.yaxis.visible = False

        # Add data sources
        self.signal_source = ColumnDataSource({"xs": [], "ys": [], "channel_id": []})

        self.spike_source = ColumnDataSource({"x": [], "y": [], "color": [], "unit_id": []})

        # Plot signals
        self.signal_renderer = self.figure.multi_line(
            xs="xs", ys="ys", source=self.signal_source, line_color="#7FFF00", line_width=1, line_alpha=0.8
        )

        # Plot spikes
        self.spike_renderer = self.figure.scatter(
            x="x", y="y", size=10, fill_color="color", fill_alpha=self.settings['alpha'], source=self.spike_source
        )

        self.figure.on_event(Tap, self._panel_on_tap)

        self._panel_create_toolbar()
        
        self.layout = pn.Column(
                self.toolbar,
                self.figure,
                self.time_slider,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both"
        )


    def _panel_refresh(self):
        t = self.time_by_seg[self.seg_index]
        t1, t2 = t - self.xsize / 3.0, t + self.xsize * 2 / 3.0

        # TODO handle segment
        times_chunk, data_curves, scatter_x, scatter_y, scatter_colors, scatter_unit_ids = \
            self.get_data_in_chunk(t1, t2, self.seg_index)

        visible_channel_inds = self.get_visible_channel_inds()

        n = visible_channel_inds.size
        self.signal_source.data.update({   
            "xs": [times_chunk]*n,
            "ys": [data_curves[i, :] for i in range(n)],
            "channel_id": self.get_visible_channel_inds(),
        })

        self.spike_source.data.update({
            "x": scatter_x,
            "y": scatter_y,
            "color": scatter_colors,
            "unit_id": scatter_unit_ids,
        })

        # Update plot ranges for x-axis too
        self.figure.x_range.start = t1
        self.figure.x_range.end = t2
        self.figure.y_range.start = 0 - 1.5 
        self.figure.y_range.end = n + 0.5

    def _panel_on_tap(self, event):
        if not hasattr(event, "x") or not hasattr(event, "y"):
            return

        ind_spike_nearest = self.find_nearest_spike(event.x, self.seg_index)
        if ind_spike_nearest is not None:
            self.controller.set_indices_spike_selected([ind_spike_nearest])
            self.seek_with_selected_spike()

    # def _panel_on_double_tap(self, event):
    #     self._panel_on_tap(event)

    def _panel_seek_with_selected_spike(self):
        ind_selected = self.controller.get_indices_spike_selected()
        n_selected = ind_selected.size

        if self.settings['auto_zoom_on_select'] and n_selected == 1:
            ind = ind_selected[0]
            peak_ind = self.controller.spikes[ind]["sample_index"]
            seg_index = self.controller.spikes[ind]["segment_index"]
            peak_time = peak_ind / self.controller.sampling_frequency

            if seg_index != self.seg_index:
                self.change_segment(seg_index)

            self.xsize = self.settings['zoom_size']
            self.xsize_spinner.value = self.xsize

            # Update time slider
            self.time_slider.value = peak_time

            # Center view on spike
            margin = self.xsize / 3
            self.figure.x_range.start = peak_time - margin
            self.figure.x_range.end = peak_time + 2 * margin
            self.refresh()

    def _panel_on_spike_selection_changed(self):
        self._panel_seek_with_selected_spike()

    def _panel_gain_zoom(self, event):
        factor = 1.3 if event.delta > 0 else 1 / 1.3
        self.apply_gain_zoom(factor)

    
TraceView._gui_help_txt = """Trace view
Show trace and spike (on best channel) of visible units.
Mouse right lick : zoom
Scroll bar at bottom : navigate on time
channel visibility is done vwith probe view
double click : pick on spike"""
