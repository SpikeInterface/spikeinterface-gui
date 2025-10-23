import numpy as np
from matplotlib.path import Path as mpl_path

from .view_base import ViewBase


class BaseScatterView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _depend_on = None
    _settings = [
            {'name': "auto_decimate", 'type': 'bool', 'value' : True },
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

        self._data_min = np.nanmin(spike_data)
        self._data_max = np.nanmax(spike_data)
        eps = (self._data_max - self._data_min) / 100.0
        self._data_max += eps
        self._max_count = None
        self._lasso_vertices = {segment_index: None for segment_index in range(controller.num_segments)}
        # this is used in panel
        self._current_selected = 0

        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)


    def get_unit_data(self, unit_id, segment_index=0):
        inds = self.controller.get_spike_indices(unit_id, segment_index=segment_index)
        spike_indices = self.controller.spikes["sample_index"][inds]
        spike_times = self.controller.sample_index_to_time(spike_indices)
        spike_data = self.spike_data[inds]
        ptp = np.ptp(spike_data)
        hist_min, hist_max = [np.min(spike_data) - 0.2 * ptp, np.max(spike_data) + 0.2 * ptp]

        hist_count, hist_bins = np.histogram(spike_data, bins=np.linspace(hist_min, hist_max, self.settings['num_bins']))

        if self.settings["auto_decimate"] and spike_times.size > self.settings['max_spikes_per_unit']:
            step = spike_times.size // self.settings['max_spikes_per_unit']
            spike_times = spike_times[::step]
            spike_data = spike_data[::step]
            inds = inds[::step]

        return spike_times, spike_data, hist_count, hist_bins, inds

    def get_selected_spikes_data(self, segment_index=0, visible_inds=None):
        sl = self.controller.segment_slices[segment_index]
        spikes_in_seg = self.controller.spikes[sl]
        selected_indices = self.controller.get_indices_spike_selected()
        if visible_inds is not None:
            selected_indices = np.intersect1d(selected_indices, visible_inds)
        mask = np.isin(sl.start + np.arange(len(spikes_in_seg)), selected_indices)
        selected_spikes = spikes_in_seg[mask]
        spike_times = selected_spikes['sample_index'] / self.controller.sampling_frequency
        spike_data = self.spike_data[sl][mask]
        return (spike_times, spike_data)


    def select_all_spikes_from_lasso(self, keep_already_selected=False):
        """
        Select all spikes within the lasso vertices.

        This method updates the selected spike indices in the controller based on the lasso vertices.
        It only works if one unit is visible.
        If `keep_already_selected` is True, it retains previously selected spikes.
        """
        visible_unit_ids = self.controller.get_visible_unit_ids()
        if len(visible_unit_ids) != 1:
            self.warning("Lasso selection is only possible if one unit is visible.")
            return
        visible_unit_id = visible_unit_ids[0]

        indices = []
        fs = self.controller.sampling_frequency
        for segment_index, vertices in self._lasso_vertices.items():
            if vertices is None:
                continue
            spike_inds = self.controller.get_spike_indices(visible_unit_id, segment_index=segment_index)
            spike_times = self.controller.spikes["sample_index"][spike_inds] / fs
            spike_data = self.spike_data[spike_inds]

            points = np.column_stack((spike_times, spike_data))
            indices_in_segment = []
            for polygon in vertices:
                # Check if points are inside the polygon
                inside = mpl_path(polygon).contains_points(points)
                if np.any(inside):
                    # If any point is inside, we can proceed with the split
                    indices_in_segment.extend(spike_inds[inside])
            indices.extend(indices_in_segment)

        if keep_already_selected:
            already_selected = self.controller.get_indices_spike_selected()
            indices = np.sort(np.unique(np.concatenate((already_selected, indices))))
        self.controller.set_indices_spike_selected(indices)
        # self.refresh()
        self.notify_spike_selection_changed()

    def split(self):
        """
        Add a split to the curation data based on the lasso vertices.
        """
        # split is only possible if one unit is visible
        visible_unit_ids = self.controller.get_visible_unit_ids()
        if len(visible_unit_ids) != 1:
            self.warning("Split is only possible if one unit is visible.")
            return
        visible_unit_id = visible_unit_ids[0]

        if self.controller.num_segments > 1:
            # check that lasso vertices are defined for all segments
            if not all(self._lasso_vertices[segment_index] is not None for segment_index in range(self.controller.num_segments)):
                # Use the new continue_from_user pattern
                self.continue_from_user(
                    "Not all segments have lasso selection. "
                    "Do you want to proceed with the split for the segments with selection only?",
                    self._perform_split, visible_unit_id
                )
                return  # Exit early - risky_action will be called if user continues
            else:
                self._perform_split(visible_unit_id)
        else:
            self._perform_split(visible_unit_id)

        visible_unit_id = visible_unit_ids[0]

    def _perform_split(self, visible_unit_id):
        """
        Perform the actual split operation.
        """
        success = self.controller.make_manual_split_if_possible(
            unit_id=visible_unit_id,
        )
        if not success:
            self.warning(
                "Split could not be performed. Ensure split unit ids are not "
                "removed, merged, or split already.")
            return
        
        # Clear the lasso vertices after splitting
        self._lasso_vertices = {segment_index: None for segment_index in range(self.controller.num_segments)}
        self.refresh()
        self.notify_manual_curation_updated()
        

    def on_unit_visibility_changed(self):
        self._lasso_vertices = {segment_index: None for segment_index in range(self.controller.num_segments)}
        visible_unit_ids = self.controller.get_visible_unit_ids()
        if len(visible_unit_ids) == 1:
            visible_unit_id = visible_unit_ids[0]
            split_unit_ids = self.controller.get_split_unit_ids()
            if visible_unit_id in split_unit_ids:
                self._current_selected = self.controller.get_indices_spike_selected().size
        self.refresh()

    def on_time_info_updated(self):
        return self.refresh()

    def on_use_times_updated(self):
        return self.refresh()

    ## QT zone ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import add_stretch_to_qtoolbar

        self.layout = QT.QVBoxLayout()

        tb = self.qt_widget.view_toolbar
        self.combo_seg = QT.QComboBox()
        tb.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {segment_index}' for segment_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self._qt_change_segment)
        add_stretch_to_qtoolbar(tb)
        self.lasso_but = QT.QPushButton("select", checkable = True)
        tb.addWidget(self.lasso_but)
        self.lasso_but.clicked.connect(self._qt_enable_disable_lasso)
        if self.controller.curation:
            self.split_but = QT.QPushButton("split")
            tb.addWidget(self.split_but)
            self.split_but.clicked.connect(self.split)
            shortcut_split = QT.QShortcut(self.qt_widget)
            shortcut_split.setKey(QT.QKeySequence("ctrl+s"))
            shortcut_split.activated.connect(self.split)
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        self.graphicsview = pg.GraphicsView()
        h.addWidget(self.graphicsview, 3)
        self.graphicsview2 = pg.GraphicsView()
        h.addWidget(self.graphicsview2, 1)

        self._qt_initialize_plot()
        
        # Add lasso curve
        self.lasso = pg.PlotCurveItem(pen='#7FFF00')
        self.plot.addItem(self.lasso)
        
        # Add selection scatter
        brush = QT.QColor('white')
        brush.setAlpha(200)
        self.scatter_select = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=brush, size=11, pxMode=True)
        self.plot.addItem(self.scatter_select)
        self.scatter_select.setZValue(1000)


    def _qt_initialize_plot(self):
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingLasso

        self.viewBox = ViewBoxHandlingLasso()
        self.viewBox.lasso_drawing.connect(self._qt_on_lasso_drawing)
        self.viewBox.lasso_finished.connect(self._qt_on_lasso_finished)
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
    
        self.viewBox2 = ViewBoxHandlingLasso()
        self.plot2 = pg.PlotItem(viewBox=self.viewBox2)
        self.graphicsview2.setCentralItem(self.plot2)
        self.plot2.hideButtons()
        self.plot2.setYLink(self.plot)
        
        self.scatter = pg.ScatterPlotItem(size=self.settings['scatter_size'], pxMode = True)
        self.plot.addItem(self.scatter)
        
        self._text_items = []


    def _qt_on_spike_selection_changed(self):
        self.refresh()

    def _qt_change_segment(self):
        segment_index = self.combo_seg.currentIndex()
        self.controller.set_time(segment_index=segment_index)
        self.refresh()
        self.notify_time_info_updated()

    def _qt_refresh(self):
        from .myqt import QT
        import pyqtgraph as pg
        
        self.scatter.clear()
        self.plot2.clear()
        self.scatter_select.clear()
        
        if self.spike_data is None:
            return

        segment_index = self.controller.get_time()[1]
        # Update combo_seg if it doesn't match the current segment index
        if self.combo_seg.currentIndex() != segment_index:
            self.combo_seg.setCurrentIndex(segment_index)

        max_count = 1
        all_inds = []
        for unit_id in self.controller.get_visible_unit_ids():

            spike_times, spike_data, hist_count, hist_bins, inds = self.get_unit_data(
                unit_id, 
                segment_index=segment_index
            )

            # make a copy of the color
            color = QT.QColor(self.get_unit_color(unit_id))
            color.setAlpha(int(self.settings['alpha']*255))
            self.scatter.addPoints(x=spike_times, y=spike_data,  pen=pg.mkPen(None), brush=color)

            color = self.get_unit_color(unit_id)
            curve = pg.PlotCurveItem(hist_count, hist_bins[:-1], fillLevel=None, fillOutline=True, brush=color, pen=color)
            self.plot2.addItem(curve)

            max_count = max(max_count, np.max(hist_count))
            all_inds.extend(inds)

        self._max_count = max_count
        
        self.plot.getViewBox().autoRange(padding = 0.0)
        self.plot2.setXRange(0, self._max_count, padding = 0.0)

        # explicitly set the y-range of the histogram to match the spike data
        y_range_plot_1 = self.plot.getViewBox().viewRange()
        self.viewBox2.setYRange(y_range_plot_1[1][0], y_range_plot_1[1][1], padding = 0.0)

        spike_times, spike_data = self.get_selected_spikes_data(segment_index=self.combo_seg.currentIndex(), visible_inds=all_inds)

        self.scatter_select.setData(spike_times, spike_data)

    def _qt_enable_disable_lasso(self, checked):
        if checked and len(self.controller.get_visible_unit_ids()) == 1:
            self.viewBox.lasso_active = checked
        else:
            self.viewBox.lasso_active = False
            self.lasso_but.setChecked(False)
            self.scatter_select.clear()

    def _qt_on_lasso_drawing(self, points):
        points = np.array(points)
        self.lasso.setData(points[:, 0], points[:, 1])

    def _qt_on_lasso_finished(self, points, shift_held=False):
        self.lasso.setData([], [])
        vertices = np.array(points)
        
        segment_index = self.combo_seg.currentIndex()
        sl = self.controller.segment_slices[segment_index]
        spikes_in_seg = self.controller.spikes[sl]
        
        # Create mask for visible units
        visible_mask = np.zeros(len(spikes_in_seg), dtype=bool)
        for unit_index, unit_id in self.controller.iter_visible_units():
            visible_mask |= (spikes_in_seg['unit_index'] == unit_index)
        
        # Only consider spikes from visible units
        visible_spikes = spikes_in_seg[visible_mask]
        if len(visible_spikes) == 0:
            # Clear selection if no visible spikes and shift not held
            if not shift_held:
                self.controller.set_indices_spike_selected([])
                self.refresh()
                self.notify_spike_selection_changed()
            return

        if self._lasso_vertices[segment_index] is None:
            self._lasso_vertices[segment_index] = []

        if shift_held:
            # If shift is held, append the vertices to the current lasso vertices
            self._lasso_vertices[segment_index].append(vertices)
            keep_already_selected = True
        else:
            # If shift is not held, clear the existing lasso vertices for this segment
            self._lasso_vertices[segment_index] = [vertices]
            keep_already_selected = False

        self.select_all_spikes_from_lasso(keep_already_selected=keep_already_selected)
        
        self.refresh()


    ## Panel zone ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, LassoSelectTool, Range1d
        from .utils_panel import _bg_color #, slow_lasso

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

        if self.controller.curation:
            self.split_button = pn.widgets.Button(name="Split", button_type="primary")
            self.split_button.on_click(self._panel_split)

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

        # Add SelectionGeometry event handler to capture lasso vertices
        self.scatter_fig.on_event('selectiongeometry', self._on_panel_selection_geometry)

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

        toolbar_elements = [self.segment_selector, self.select_toggle_button]
        if self.controller.curation:
            toolbar_elements.append(self.split_button)

        if self.controller.curation:
            from .utils_panel import KeyboardShortcut, KeyboardShortcuts
            shortcuts = [KeyboardShortcut(key="s", name="split", ctrlKey=True)]
            shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
            shortcuts_component.on_msg(self._panel_handle_shortcut)
            toolbar_elements.append(shortcuts_component)

        self.layout = pn.Column(
            pn.Row(*toolbar_elements, sizing_mode="stretch_width"),
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

        segment_index = self.controller.get_time()[1]

        visible_unit_ids = self.controller.get_visible_unit_ids()
        for unit_id in visible_unit_ids:
            spike_times, spike_data, hist_count, hist_bins, inds = self.get_unit_data(
                unit_id,
                segment_index=segment_index
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
        if self.select_toggle_button.value:
            self.scatter_fig.toolbar.active_drag = self.lasso_tool
        else:
            self.scatter_fig.toolbar.active_drag = None
            self.scatter_source.selected.indices = []


    def _panel_change_segment(self, event):
        self._current_selected = 0
        self.segment_index = int(self.segment_selector.value.split()[-1])
        self.controller.set_time(segment_index=self.segment_index)
        t_start, t_end = self.controller.get_t_start_t_end()
        self.scatter_fig.x_range.start = t_start
        self.scatter_fig.x_range.end = t_end
        self.refresh()
        self.notify_time_info_updated()

    def _on_panel_selection_geometry(self, event):
        """
        Handle SelectionGeometry event to capture lasso polygon vertices.
        """
        if event.final:
            xs = np.array(event.geometry["x"])
            ys = np.array(event.geometry["y"])
            polygon = np.column_stack((xs, ys))

            selected = self.scatter_source.selected.indices
            if len(selected) == 0:
                self.controller.set_indices_spike_selected([])
                self.notify_spike_selection_changed()
                return

            # Append the current polygon to the lasso vertices if shift is held
            segment_index = self.segment_index
            if self._lasso_vertices[segment_index] is None:
                self._lasso_vertices[segment_index] = []
            if len(selected) > self._current_selected:
                self._current_selected = len(selected)
                # Store the current polygon for the current segment
                self._lasso_vertices[segment_index].append(polygon)
                keep_already_selected = True
            else:
                self._lasso_vertices[segment_index] = [polygon]
                keep_already_selected = False

            self.select_all_spikes_from_lasso(keep_already_selected)
            self.refresh()

    def _panel_split(self, event):
        """
        Handle split button click in panel mode.
        """
        self.split()

    def _panel_update_selected_spikes(self):
        # handle selected spikes
        selected_spike_indices = self.controller.get_indices_spike_selected()
        selected_spike_indices = np.intersect1d(selected_spike_indices, self.plotted_inds)
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
            if self.settings["auto_decimate"] and len(selected_indices) > 0:
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

    def _panel_handle_shortcut(self, event):
        if event.data == "split":
            if len(self.controller.get_visible_unit_ids()) == 1:
                self.split()