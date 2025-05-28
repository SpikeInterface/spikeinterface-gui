import numpy as np
from matplotlib.path import Path as mpl_path

from .view_base import ViewBase


class BaseScatterView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _depend_on = None
    _settings = [
            {'name': 'auto_decimate', 'type': 'bool', 'value' : True },
            {'name': 'max_spikes_per_unit', 'type': 'int', 'value' : 10_000 },
            {'name': 'alpha', 'type': 'float', 'value' : 0.7, 'limits':(0, 1.), 'step':0.05 },
            {'name': 'scatter_size', 'type': 'float', 'value' : 2., 'step':0.5 },
            {'name': 'num_bins', 'type': 'int', 'value' : 400, 'step': 1 },
        ]
    _need_compute = False
    
    def __init__(self, spike_data, y_label, controller=None, parent=None, backend="qt"):
        
        # compute data bounds
        assert len(spike_data) == len(controller.spikes), "spike_data must have the same length as spikes"
        assert spike_data.ndim == 1, "spike_data must be 1D"
        self.spike_data = spike_data
        self.y_label = y_label

        self._data_min = np.min(spike_data)
        self._data_max = np.max(spike_data)
        eps = (self._data_max - self._data_min) / 100.0
        self._data_max += eps
        self._max_count = None

        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)


    def get_unit_data(self, unit_id, seg_index=0):
        inds = self.controller.get_spike_indices(unit_id, seg_index=seg_index)
        spike_times = self.controller.spikes["sample_index"][inds] / self.controller.sampling_frequency
        spike_data = self.spike_data[inds]
        ptp = np.ptp(spike_data)
        hist_min, hist_max = [np.min(spike_data) - 0.2 * ptp, np.max(spike_data) + 0.2 * ptp]

        hist_count, hist_bins = np.histogram(spike_data, bins=np.linspace(hist_min, hist_max, self.settings['num_bins']))

        if self.settings['auto_decimate'] and spike_times.size > self.settings['max_spikes_per_unit']:
            step = spike_times.size // self.settings['max_spikes_per_unit']
            spike_times = spike_times[::step]
            spike_data = spike_data[::step]
            inds = inds[::step]

        return spike_times, spike_data, hist_count, hist_bins, inds

    def get_selected_spikes_data(self, seg_index=0):
        sl = self.controller.segment_slices[seg_index]
        spikes_in_seg = self.controller.spikes[sl]
        selected_indices = self.controller.get_indices_spike_selected()
        mask = np.isin(sl.start + np.arange(len(spikes_in_seg)), selected_indices)
        selected_spikes = spikes_in_seg[mask]
        spike_times = selected_spikes['sample_index'] / self.controller.sampling_frequency
        spike_data = self.spike_data[sl][mask]
        return (spike_times, spike_data)


    ## QT zone ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import add_stretch_to_qtoolbar

        self.layout = QT.QVBoxLayout()

        tb = self.qt_widget.view_toolbar
        self.combo_seg = QT.QComboBox()
        tb.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {seg_index}' for seg_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self.refresh)
        add_stretch_to_qtoolbar(tb)
        self.lasso_but = QT.QPushButton("select", checkable = True)

        tb.addWidget(self.lasso_but)
        self.lasso_but.clicked.connect(self.enable_disable_lasso)
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        self.graphicsview = pg.GraphicsView()
        h.addWidget(self.graphicsview, 3)

        self.graphicsview2 = pg.GraphicsView()
        h.addWidget(self.graphicsview2, 1)

        self.initialize_plot()
        
        # Add lasso curve
        self.lasso = pg.PlotCurveItem(pen='#7FFF00')
        self.plot.addItem(self.lasso)
        
        # Add selection scatter
        brush = QT.QColor('white')
        brush.setAlpha(200)
        self.scatter_select = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=brush, size=11, pxMode=True)
        self.plot.addItem(self.scatter_select)
        self.scatter_select.setZValue(1000)


    
    def initialize_plot(self):
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingLasso

        self.viewBox = ViewBoxHandlingLasso()
        self.viewBox.lasso_drawing.connect(self.on_lasso_drawing)
        self.viewBox.lasso_finished.connect(self.on_lasso_finished)
        self.viewBox.disableAutoRange()
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
    
        self.viewBox2 = ViewBoxHandlingLasso()
        self.viewBox2.disableAutoRange()
        self.plot2 = pg.PlotItem(viewBox=self.viewBox2)
        self.graphicsview2.setCentralItem(self.plot2)
        self.plot2.hideButtons()
        self.plot2.setYLink(self.plot)

        
        self.scatter = pg.ScatterPlotItem(size=self.settings['scatter_size'], pxMode = True)
        self.plot.addItem(self.scatter)
        
        self._text_items = []
        
        self.plot.setYRange(self._data_min,self._data_max, padding = 0.0)

    def _qt_on_spike_selection_changed(self):
        self.refresh()

    def _qt_refresh(self):
        from .myqt import QT
        import pyqtgraph as pg
        
        self.scatter.clear()
        self.plot2.clear()
        self.scatter_select.clear()
        
        if self.spike_data is None:
            return

        max_count = 1
        for unit_id in self.controller.get_visible_unit_ids():

            spike_times, spike_data, hist_count, hist_bins, _ = self.get_unit_data(unit_id)

            # make a copy of the color
            color = QT.QColor(self.get_unit_color(unit_id))
            color.setAlpha(int(self.settings['alpha']*255))
            self.scatter.addPoints(x=spike_times, y=spike_data,  pen=pg.mkPen(None), brush=color)

            color = self.get_unit_color(unit_id)
            curve = pg.PlotCurveItem(hist_count, hist_bins[:-1], fillLevel=None, fillOutline=True, brush=color, pen=color)
            self.plot2.addItem(curve)

            max_count = max(max_count, np.max(hist_count))

        self._max_count = max_count
        seg_index =  self.combo_seg.currentIndex()
        time_max = self.controller.get_num_samples(seg_index) / self.controller.sampling_frequency

        self.plot.setXRange( 0., time_max, padding = 0.0)
        self.plot2.setXRange(0, self._max_count, padding = 0.0)
        
        spike_times, spike_data = self.get_selected_spikes_data()
        self.scatter_select.setData(spike_times, spike_data)

    def enable_disable_lasso(self, checked):
        if checked and len(self.controller.get_visible_unit_ids()) == 1:
            self.viewBox.lasso_active = checked
        else:
            self.viewBox.lasso_active = False
            self.lasso_but.setChecked(False)
            self.scatter_select.clear()

    def on_lasso_drawing(self, points):
        points = np.array(points)
        self.lasso.setData(points[:, 0], points[:, 1])
    
    def on_lasso_finished(self, points):
        self.lasso.setData([], [])
        vertices = np.array(points)
        
        seg_index = self.combo_seg.currentIndex()
        sl = self.controller.segment_slices[seg_index]
        spikes_in_seg = self.controller.spikes[sl]
        fs = self.controller.sampling_frequency
        
        # Create mask for visible units
        visible_mask = np.zeros(len(spikes_in_seg), dtype=bool)
        for unit_index, unit_id in self.controller.iter_visible_units():
            visible_mask |= (spikes_in_seg['unit_index'] == unit_index)
        
        # Only consider spikes from visible units
        visible_spikes = spikes_in_seg[visible_mask]
        if len(visible_spikes) == 0:
            # Clear selection if no visible spikes
            self.controller.set_indices_spike_selected([])
            self.refresh()
            self.notify_spike_selection_changed()
            return
            
        spike_times = visible_spikes['sample_index'] / fs
        spike_data = self.spike_data[sl][visible_mask]
        
        points = np.column_stack((spike_times, spike_data))
        inside = mpl_path(vertices).contains_points(points)
        
        # Clear selection if no spikes inside lasso
        if not np.any(inside):
            self.controller.set_indices_spike_selected([])
            self.refresh()
            self.notify_spike_selection_changed()
            return

        # Map back to original indices
        visible_indices = np.nonzero(visible_mask)[0]
        selected_indices = sl.start + visible_indices[inside]
        self.controller.set_indices_spike_selected(selected_indices)
        self.refresh()
        self.notify_spike_selection_changed()



    ## Panel zone ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, LassoSelectTool, Range1d
        from .utils_panel import _bg_color, slow_lasso

        self.lasso_tool = LassoSelectTool()

        self.segment_index = 0
        self.segment_selector = pn.widgets.Select(
            name="",
            options=[f"Segment {i}" for i in range(self.controller.num_segments)],
            value=f"Segment {self.segment_index}",
        )
        self.segment_selector.param.watch(self._panel_change_segment, 'value')

        self.select_toggle_button = pn.widgets.Toggle(name="Select")
        self.select_toggle_button.param.watch(self._panel_on_select_button, 'value')        

        self.y_range = Range1d(self._data_min, self._data_max)
        self.scatter_source = ColumnDataSource(data={"x": [], "y": [], "color": []})
        self.scatter_fig = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset,wheel_zoom",
            active_scroll="wheel_zoom",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            y_range=self.y_range,
            styles={"flex": "1"}
        )
        self.scatter = self.scatter_fig.scatter(
            "x",
            "y",
            source=self.scatter_source,
            size=self.settings['scatter_size'],
            color="color",
            fill_alpha=self.settings['alpha'],
        )
        self.scatter_fig.toolbar.logo = None
        self.scatter_fig.add_tools(self.lasso_tool)
        self.scatter_fig.toolbar.active_drag = None
        self.scatter_fig.xaxis.axis_label = "Time (s)"
        self.scatter_fig.yaxis.axis_label = self.y_label
        time_max = self.controller.get_num_samples(self.segment_index) / self.controller.sampling_frequency
        self.scatter_fig.x_range = Range1d(0., time_max)

        slow_lasso(self.scatter_source, self._on_panel_lasso_selected)

        self.hist_fig = bpl.figure(
            tools="reset,wheel_zoom",
            sizing_mode="stretch_both",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            y_range=self.y_range,
            styles={"flex": "1"}  # Make histogram narrower than scatter plot
        )
        self.hist_fig.toolbar.logo = None
        self.hist_fig.yaxis.axis_label = self.y_label
        self.hist_fig.xaxis.axis_label = "Count"
        self.hist_fig.x_range = Range1d(0, 1000)  # Initial x range for histogram

        self.layout = pn.Column(
            pn.Row(self.segment_selector, self.select_toggle_button, sizing_mode="stretch_width"),
            pn.Row(
                pn.Column(
                    self.scatter_fig,
                    styles={"flex": "1"},
                    sizing_mode="stretch_both"
                ),
                pn.Column(
                    self.hist_fig,
                    styles={"flex": "0.3"},
                    sizing_mode="stretch_both"
                ),
            )
        )
        self.hist_lines = []
        self.noise_harea = []
        self.plotted_inds = []

    def _panel_refresh(self):
        from bokeh.models import ColumnDataSource, Range1d

        # clear figures
        for renderer in self.hist_lines:
            self.hist_fig.renderers.remove(renderer)
        self.hist_lines = []
        self.plotted_inds = []

        max_count = 1
        xs = []
        ys = []
        colors = []

        visible_unit_ids = self.controller.get_visible_unit_ids()
        for unit_id in visible_unit_ids:
            spike_times, spike_data, hist_count, hist_bins, inds = self.get_unit_data(
                unit_id,
                seg_index=self.segment_index
            )
            color = self.get_unit_color(unit_id)
            xs.extend(spike_times)
            ys.extend(spike_data)
            colors.extend([color] * len(spike_times))
            max_count = max(max_count, np.max(hist_count))
            self.plotted_inds.extend(inds)

            hist_lines = self.hist_fig.line(
                "x",
                "y",
                source=ColumnDataSource(
                    {"x":hist_count,
                     "y":hist_bins[:-1],
                     }
                ),
                line_color=color,
                line_width=2,
            )
            self.hist_lines.append(hist_lines)

        self._max_count = max_count

        # Add scatter plot with correct alpha parameter
        self.scatter_source.data = {
            "x": xs,
            "y": ys,
            "color": colors
        }
        self.scatter.glyph.size = self.settings['scatter_size']
        self.scatter.glyph.fill_alpha = self.settings['alpha']

        # handle selected spikes
        self._panel_update_selected_spikes()

        # set y range to min and max of visible spike amplitudes plus a margin
        margin = 50
        all_amps = ys
        if len(all_amps) > 0:
            self.y_range.start = np.min(all_amps) - margin
            self.y_range.end = np.max(all_amps) + margin
            self.hist_fig.x_range.end = max_count

    def _panel_on_select_button(self, event):
        if self.select_toggle_button.value and len(self.controller.get_visible_unit_ids()) == 1:
            self.scatter_fig.toolbar.active_drag = self.lasso_tool
        else:
            self.scatter_fig.toolbar.active_drag = None
            self.scatter_source.selected.indices = []
            self._on_panel_lasso_selected(None, None, None)

    def _panel_change_segment(self, event):
        self.segment_index = int(self.segment_selector.value.split()[-1])
        time_max = self.controller.get_num_samples(self.segment_index) / self.controller.sampling_frequency
        self.scatter_fig.x_range.end = time_max
        self.refresh()

    def _on_panel_lasso_selected(self, attr, old, new):
        """
        Handle selection changes in the scatter plot.
        """
        if self.select_toggle_button.value:
            selected = self.scatter_source.selected.indices
            if len(selected) == 0:
                self.controller.set_indices_spike_selected([])
                self.notify_spike_selection_changed()
                return

            # Map back to original indices
            sl = self.controller.segment_slices[self.segment_index]
            spikes_in_seg = self.controller.spikes[sl]
            # Create mask for visible units
            visible_mask = np.zeros(len(spikes_in_seg), dtype=bool)
            for unit_index, unit_id in self.controller.iter_visible_units():
                visible_mask |= (spikes_in_seg['unit_index'] == unit_index)
            
            # Map back to original indices
            visible_indices = np.nonzero(visible_mask)[0]
            selected_indices = sl.start + visible_indices[selected]
            self.controller.set_indices_spike_selected(selected_indices)
            self.notify_spike_selection_changed()


    def _panel_update_selected_spikes(self):
        # handle selected spikes
        selected_spike_indices = self.controller.get_indices_spike_selected()
        if len(selected_spike_indices) > 0:
            # map absolute indices to visible spikes
            sl = self.controller.segment_slices[self.segment_index]
            spikes_in_seg = self.controller.spikes[sl]
            visible_mask = np.zeros(len(spikes_in_seg), dtype=bool)
            for unit_index, unit_id in self.controller.iter_visible_units():
                visible_mask |= (spikes_in_seg['unit_index'] == unit_index)
            visible_indices = sl.start + np.nonzero(visible_mask)[0]
            selected_indices = np.nonzero(np.isin(visible_indices, selected_spike_indices))[0]
            # set selected spikes in scatter plot
            if self.settings["auto_decimate"]:
                selected_indices, = np.nonzero(np.isin(self.plotted_inds, selected_spike_indices))
            self.scatter_source.selected.indices = list(selected_indices)
        else:
            self.scatter_source.selected.indices = []


    def _panel_on_spike_selection_changed(self):
        # set selection in scatter plot
        selected_indices = self.controller.get_indices_spike_selected()
        if len(selected_indices) == 0:
            self.scatter_source.selected.indices = []
            return
        elif len(selected_indices) == 1:
            selected_segment = self.controller.spikes[selected_indices[0]]['segment_index']
            if selected_segment != self.segment_index:
                self.segment_selector.value = f"Segment {selected_segment}"
                self._panel_change_segment(None)
        # update selected spikes
        self._panel_update_selected_spikes()

