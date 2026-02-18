import time
import numpy as np

from .view_base import ViewBase

from functools import partial

_wheel_refresh_time = 0.1

# TODO sam : check the on_params_changed in change params and remove initialize_plot()


class WaveformView(ViewBase):
    id = "waveform"
    _supported_backend = ["qt", "panel"]

    _settings = [
        {"name": "overlap", "type": "bool", "value": True},
        {
            "name": "plot_selected_spike",
            "type": "bool",
            "value": False,
        },  # true here can be very slow because it loads traces
        {"name": "plot_waveforms_samples", "type": "bool", "value": False},
        {"name": "waveforms_alpha", "type": "float", "value": 0.3},
        {"name": "num_waveforms", "type": "int", "value": 20},
        {"name": "auto_zoom_on_unit_selection", "type": "bool", "value": False},
        {"name": "auto_move_on_unit_selection", "type": "bool", "value": True},
        {"name": "show_only_selected_cluster", "type": "bool", "value": True},
        {"name": "plot_limit_for_flatten", "type": "bool", "value": True},
        {"name": "plot_std", "type": "bool", "value": True},
        {"name": "show_channel_id", "type": "bool", "value": False},
        {"name": "sparse_display", "type": "bool", "value": True},
        {"name": "x_scalebar", "type": "bool", "value": False},
        {"name": "y_scalebar", "type": "bool", "value": False},
        {"name": "scalebar_y_uv", "type": "int", "value": 50},
        {"name": "scalebar_x_ms", "type": "int", "value": 1},
    ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent, backend=backend)

        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        num_chan = len(self.controller.channel_ids)
        self.xvect = np.zeros((num_chan, width), dtype="float32")
        self.contact_location = self.controller.get_contact_location().copy()
        xpos = self.contact_location[:,0]
        ypos = self.contact_location[:,1]

        # copied directly from spikeinterface.widgets.unit_waveform
        if num_chan == 1:
            self.delta_x = 10
        else:
            manh = np.abs(
                self.contact_location[None, :] - self.contact_location[:, None]
            )  # vertical and horizontal distances between each channel
            eucl = np.linalg.norm(manh, axis=2)  # Euclidean distance matrix
            np.fill_diagonal(eucl, np.inf)  # the distance of a channel to itself is not considered
            gaus = np.exp(-0.5 * (eucl / eucl.min()) ** 2)  # sigma uses the min distance between channels
            weight = manh[..., 0] / eucl * gaus
            if weight.sum() == 0:
                self.delta_x = 10
            else:
                self.delta_x = (manh[..., 0] * weight).sum() / weight.sum()

        unique_y = np.sort(np.unique(np.round(ypos)))
        if unique_y.size > 1:
            self.delta_y = np.min(np.diff(unique_y))
        else:
            self.delta_y = 40.0  # um
        self.gain_y = 0.02
        self.factor_x = 1.0
        espx = self.delta_x / 2.5
        for chan_ind, chan_id in enumerate(self.controller.channel_ids):
            x, y = self.contact_location[chan_ind, :]
            self.xvect[chan_ind, :] = np.linspace(x - espx, x + espx, num=width)
        self.wf_min, self.wf_max = self.controller.get_waveforms_range()

        self.last_wheel_event_time = None

    def get_common_channels(self):
        sparse = self.settings["sparse_display"]
        visible_unit_ids = self.controller.get_visible_unit_ids()
        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                common_channel_indexes = None
        else:
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype="int64")

        return common_channel_indexes

    def get_spike_waveform(self, ind):
        if not self.controller.has_extension("recording") or not self.controller.with_traces:
            return None, None
        seg_num = self.controller.spikes["segment_index"][ind]
        peak_ind = self.controller.spikes["sample_index"][ind]

        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter

        # TODO handle return_scaled
        wf = self.controller.get_traces(
            trace_source="preprocessed",
            segment_index=seg_num,
            start_frame=peak_ind - nbefore,
            end_frame=peak_ind + nafter,
            return_in_uV=self.controller.return_in_uV,
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
                xvects.append(
                    np.array(
                        [np.linspace(x[sample_start], x[sample_end], num_x_samples, endpoint=True) for x in xvectors]
                    )
                )
        else:
            xvects = [xvectors] * num_visible_units
        return xvects

    def compute_scalebar_x_width(self, scalebar_x_ms):
        nbefore, nafter = self.controller.get_waveform_sweep()
        xvects = self.get_xvectors_not_overlap(self.xvect, len(self.controller.get_visible_unit_ids()))
        xvect_len = np.ptp(xvects[0][0]) * self.factor_x
        sampling_rate = self.controller.sampling_frequency
        xvect_len_ms = (nbefore + nafter) * 1e3 / sampling_rate
        scalebar_x_width = int(scalebar_x_ms * xvect_len / xvect_len_ms)
        return scalebar_x_width

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import add_stretch_to_qtoolbar

        self.layout = QT.QVBoxLayout()

        tb = self.qt_widget.view_toolbar

        # Mode flatten or geometry
        self.combo_mode = QT.QComboBox()
        tb.addWidget(self.combo_mode)
        self.mode = "geometry"
        self.combo_mode.addItems(["geometry", "flatten"])
        self.combo_mode.currentIndexChanged.connect(self._qt_on_combo_mode_changed)
        add_stretch_to_qtoolbar(tb)

        but = QT.QPushButton("scale")
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

    def _qt_initialize_plot(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleclickAndGain

        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter

        self.viewBox1 = ViewBoxHandlingDoubleclickAndGain()
        self.viewBox1.disableAutoRange()

        grid = pg.GraphicsLayout(border=(100, 100, 100))
        self.graphicsview.setCentralItem(grid)

        self.plot1 = grid.addPlot(row=0, col=0, rowspan=2, viewBox=self.viewBox1)
        self.plot1.hideButtons()
        self.plot1.showAxis("left", True)

        # Clear any existing waveforms samples curves
        if hasattr(self, "curve_waveforms_samples"):
            self._qt_clear_waveforms_samples()

        self.curve_waveforms = pg.PlotCurveItem([], [], pen=pg.mkPen(QT.QColor("white"), width=1), connect="finite")
        self.plot1.addItem(self.curve_waveforms)

        # List to hold multiple curve items for waveform samples (one per unit)
        self.curve_waveforms_samples = []

        # List for scalebar items
        self.scalebar_items = []

        if self.mode == "flatten":
            grid.nextRow()
            grid.nextRow()
            self.viewBox2 = ViewBoxHandlingDoubleclickAndGain()
            self.viewBox2.disableAutoRange()
            self.plot2 = grid.addPlot(row=2, col=0, rowspan=1, viewBox=self.viewBox2)
            self.plot2.hideButtons()
            self.plot2.showAxis("left", True)
            self.viewBox2.setXLink(self.viewBox1)

            self._common_channel_indexes_flat = None

        elif self.mode == "geometry":
            self.plot2 = None

        self._x_range = None
        self._y1_range = None
        self._y2_range = None

        self.viewBox1.gain_zoom.connect(self._qt_gain_zoom)
        self.viewBox1.limit_zoom.connect(self._qt_limit_zoom)
        self.viewBox1.widen_narrow.connect(self._qt_widen_narrow)
        self.viewBox1.heighten_shorten.connect(self._qt_heighten_shorten)

        shortcut_scale_waveforms_up = QT.QShortcut(self.qt_widget)
        shortcut_scale_waveforms_up.setKey(QT.QKeySequence("ctrl+="))
        shortcut_scale_waveforms_up.activated.connect(partial(self._qt_gain_zoom, 1.3))

        shortcut_scale_waveforms_down = QT.QShortcut(self.qt_widget)
        shortcut_scale_waveforms_down.setKey(QT.QKeySequence("ctrl+-"))
        shortcut_scale_waveforms_down.activated.connect(partial(self._qt_gain_zoom, 1 / 1.3))

        shortcut_overlap = QT.QShortcut(self.qt_widget)
        shortcut_overlap.setKey(QT.QKeySequence("ctrl+o"))
        shortcut_overlap.activated.connect(self.toggle_overlap)

        shortcut_waveforms = QT.QShortcut(self.qt_widget)
        shortcut_waveforms.setKey(QT.QKeySequence("ctrl+p"))
        shortcut_waveforms.activated.connect(self.toggle_waveforms)

    def toggle_overlap(self):
        self.settings["overlap"] = not self.settings["overlap"]
        self.refresh()

    def toggle_waveforms(self):
        self.settings["plot_waveforms_samples"] = not self.settings["plot_waveforms_samples"]
        self.refresh()

    def _qt_widen_narrow(self, factor_ratio):
        if self.mode == "geometry":
            self.factor_x *= factor_ratio
            self._qt_refresh(keep_range=True)

    def _qt_heighten_shorten(self, factor_ratio):
            import pyqtgraph as pg
            if self.mode == "geometry":
                vb = self.plot1.getViewBox()

                # Disable auto-range properly (must be on ViewBox!)
                vb.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=False)
                vb.setAspectLocked(False)

                # Get current ranges
                _, (ymin, ymax) = vb.viewRange()

                # Scale Y only
                yrange = ymax - ymin
                ymid = (ymin + ymax) / 2.0
                new_yrange = yrange * factor_ratio
                ymin = ymid - new_yrange / 2.0
                ymax = ymid + new_yrange / 2.0
                vb.setYRange(ymin, ymax, padding=0.0)

    def _qt_gain_zoom(self, factor_ratio):
        if self.mode == "geometry":
            self.gain_y *= factor_ratio
            self._qt_refresh(keep_range=True, auto_zoom=False)

    def _qt_limit_zoom(self, factor_ratio):
        if self.mode == "geometry":
            if self._x_range is None:
                self._x_range = tuple(self.viewBox1.state["viewRange"][0])
            l0, l1 = self._x_range
            mid = (l0 + l1) / 2.0
            hw = (l1 - l0) / 2.0
            l0 = mid - hw * factor_ratio
            l1 = mid + hw * factor_ratio
            self._x_range = (l0, l1)
            self.plot1.setXRange(*self._x_range, padding=0.0)
            self._qt_add_scalebars()

    def _qt_zoom_range(self):
        self._x_range = None
        self._y1_range = None
        self._y2_range = None
        self._qt_refresh(keep_range=False)

    def _qt_refresh(self, keep_range=False, auto_zoom=False):

        if not hasattr(self, "viewBox1"):
            self._qt_initialize_plot()

        if not hasattr(self, "viewBox1"):
            return

        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size

        dict_visible_units = {k: False for k in self.controller.unit_ids}
        if self.settings["show_only_selected_cluster"] and n_selected == 1:
            ind = selected_inds[0]
            unit_index = self.controller.spikes[ind]["unit_index"]
            unit_id = self.controller.unit_ids[unit_index]
            dict_visible_units[unit_id] = True
        else:
            for unit_id in self.controller.get_visible_unit_ids():
                dict_visible_units[unit_id] = True

        if self.mode == "flatten":
            self.plot1.setAspectLocked(lock=False, ratio=None)
            self._qt_refresh_mode_flatten(dict_visible_units, keep_range)
        elif self.mode == "geometry":
            self.plot1.setAspectLocked(lock=True, ratio=1)
            self._qt_refresh_mode_geometry(dict_visible_units, keep_range, auto_zoom)
            self._qt_add_scalebars()

        if self.controller.with_traces:
            self._qt_refresh_with_spikes()

    def _qt_refresh_mode_flatten(self, dict_visible_units, keep_range):
        import pyqtgraph as pg
        from .myqt import QT

        if self._x_range is not None and keep_range:
            # this may change with pyqtgraph
            self._x_range = tuple(self.viewBox1.state["viewRange"][0])
            self._y1_range = tuple(self.viewBox1.state["viewRange"][1])
            self._y2_range = tuple(self.viewBox2.state["viewRange"][1])

        self.plot1.clear()
        self.plot2.clear()
        self.plot1.addItem(self.curve_waveforms)

        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter

        sparse = self.settings["sparse_display"]

        visible_unit_ids = [unit_id for unit_id, v in dict_visible_units.items() if v]

        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                return
        else:
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype="int64")

        self._common_channel_indexes_flat = common_channel_indexes

        # lines
        def addSpan(plot):
            white = pg.mkColor(255, 255, 255, 20)
            for i, c in enumerate(common_channel_indexes):
                if i % 2 == 1:
                    region = pg.LinearRegionItem([width * i, width * (i + 1) - 1], movable=False, brush=white)
                    plot.addItem(region, ignoreBounds=True)
                    for l in region.lines:
                        l.setPen(white)
                vline = pg.InfiniteLine(pos=nbefore + width * i, angle=90, movable=False, pen=pg.mkPen("w"))
                plot.addItem(vline)

        if self.settings["plot_limit_for_flatten"]:
            addSpan(self.plot1)
            addSpan(self.plot2)

        shape = (width, len(common_channel_indexes))
        xvect = np.arange(shape[0] * shape[1])
        min_std = 0
        max_std = 0
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not dict_visible_units[unit_id]:
                continue

            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            template_std = self.controller.templates_std[unit_index, :, :][:, common_channel_indexes]

            color = self.get_unit_color(unit_id)
            curve = pg.PlotCurveItem(xvect, template_avg.T.ravel(), pen=pg.mkPen(color, width=2))
            self.plot1.addItem(curve)

            # Don't plot std when waveform samples are being plotted (to avoid clutter)
            if self.settings["plot_std"] and not self.settings["plot_waveforms_samples"]:
                color2 = QT.QColor(color)
                color2.setAlpha(self.alpha)
                curve1 = pg.PlotCurveItem(xvect, template_avg.T.ravel() + template_std.T.ravel(), pen=color2)
                curve2 = pg.PlotCurveItem(xvect, template_avg.T.ravel() - template_std.T.ravel(), pen=color2)
                self.plot1.addItem(curve1)
                self.plot1.addItem(curve2)

                fill = pg.FillBetweenItem(curve1=curve1, curve2=curve2, brush=color2)
                self.plot1.addItem(fill)

            if template_std is not None:
                template_std_flatten = template_std.T.ravel()
                curve = pg.PlotCurveItem(xvect, template_std_flatten, pen=color)
                self.plot2.addItem(curve)
                min_std = min(min_std, template_std_flatten.min())
                max_std = max(max_std, template_std_flatten.max())
        if self.settings["show_channel_id"]:
            for i, chan_ind in enumerate(common_channel_indexes):
                chan_id = self.controller.channel_ids[chan_ind]
                itemtxt = pg.TextItem(f"{chan_id}", anchor=(0.5, 0.5), color="#FFFF00")
                itemtxt.setFont(QT.QFont("", pointSize=12))
                self.plot1.addItem(itemtxt)
                itemtxt.setPos(width * i + nbefore, 0)

        if self._x_range is None or not keep_range:
            if xvect.size > 0:
                self._x_range = xvect[0], xvect[-1]
                self._y1_range = self.wf_min * 1.1, self.wf_max * 1.1
                self._y2_range = min_std * 0.9, max_std * 1.1

        if self._x_range is not None:
            self.plot1.setXRange(*self._x_range, padding=0.0)
            self.plot1.setYRange(*self._y1_range, padding=0.0)
            self.plot2.setYRange(*self._y2_range, padding=0.0)

    def _qt_refresh_mode_geometry(self, dict_visible_units, keep_range, auto_zoom):
        from .myqt import QT
        import pyqtgraph as pg

        self.plot1.clear()

        if self.xvect is None:
            return

        sparse = self.settings["sparse_display"]
        visible_unit_ids = self.controller.get_visible_unit_ids()
        visible_unit_indices = self.controller.get_visible_unit_indices()
        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                return
        else:
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype="int64")

        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter

        if width != self.xvect.shape[1]:
            self._qt_initialize_plot()

        self.plot1.addItem(self.curve_waveforms)

        xvectors = self.xvect[common_channel_indexes, :] * self.factor_x
        xvects = self.get_xvectors_not_overlap(xvectors, len(visible_unit_ids))

        if auto_zoom is True:
            self.gain_y = 0.02

        for xvect, unit_index, unit_id in zip(xvects, visible_unit_indices, visible_unit_ids):
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            template_std = self.controller.templates_std

            ypos = self.contact_location[common_channel_indexes, 1]

            wf = template_avg
            wf = wf * self.gain_y * self.delta_y + ypos[None, :]

            connect = np.ones(wf.shape, dtype="bool")
            connect[0, :] = 0
            connect[-1, :] = 0

            # color = self.controller.qcolors.get(unit_id, QT.QColor( 'white'))
            color = self.get_unit_color(unit_id)

            curve = pg.PlotCurveItem(
                xvect.ravel(), wf.T.ravel(), pen=pg.mkPen(color, width=2), connect=connect.T.ravel()
            )

            # Don't plot std when waveform samples are being plotted (to avoid clutter)
            if self.settings["plot_std"] and (template_std is not None) and not self.settings["plot_waveforms_samples"]:

                wv_std = template_std[unit_index, :, :][:, common_channel_indexes]

                wf_std_p = wf + wv_std * self.gain_y * self.delta_y
                wf_std_m = wf - wv_std * self.gain_y * self.delta_y

                curve_p = pg.PlotCurveItem(xvect.ravel(), wf_std_p.T.ravel(), connect=connect.T.ravel())
                curve_m = pg.PlotCurveItem(xvect.ravel(), wf_std_m.T.ravel(), connect=connect.T.ravel())

                color2 = QT.QColor(color)
                color2.setAlpha(80)
                fill = pg.FillBetweenItem(curve1=curve_m, curve2=curve_p, brush=color2)
                self.plot1.addItem(fill)

            self.plot1.addItem(curve)

        if self.settings["show_channel_id"]:
            for chan_ind in common_channel_indexes:
                chan_id = self.controller.channel_ids[chan_ind]
                x, y = self.contact_location[chan_ind, :]
                itemtxt = pg.TextItem(f"{chan_id}", anchor=(0.5, 0.5), color="#FFFF00")
                itemtxt.setFont(QT.QFont("", pointSize=12))
                self.plot1.addItem(itemtxt)
                itemtxt.setPos(x, y)

        if not keep_range:
            self.plot1.autoRange(padding=0.1)

    def _qt_refresh_with_spikes(self):
        from .myqt import QT

        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size

        common_channel_indexes = self.get_common_channels()
        if common_channel_indexes is None:
            self.curve_waveforms.setData([], [])
            self._qt_clear_waveforms_samples()
            return

        # Clear previous waveform samples
        self._qt_clear_waveforms_samples()

        if self.settings["plot_selected_spike"]:
            if n_selected != 1:
                self.curve_waveforms.setData([], [])
                return
            else:
                selected_inds = self.controller.get_indices_spike_selected()
                ind = selected_inds[0]
                wf, width = self.get_spike_waveform(ind)
                if wf is None:
                    return
                wf = wf[:, common_channel_indexes]
        elif self.settings["plot_waveforms_samples"]:
            if not self.controller.has_extension("waveforms"):
                self.curve_waveforms.setData([], [])
                return
            num_waveforms = self.settings["num_waveforms"]
            if num_waveforms <= 0:
                self.curve_waveforms.setData([], [])
                return
            wf_ext = self.controller.analyzer.get_extension("waveforms")
            visible_unit_ids = self.controller.get_visible_unit_ids()

            # Process waveforms per unit to maintain color association
            unit_waveforms_data = []
            width = None

            for unit_id in visible_unit_ids:
                waveforms = wf_ext.get_waveforms_one_unit(unit_id, force_dense=True)
                if waveforms is None or len(waveforms) == 0:
                    continue

                if width is None:
                    width = waveforms.shape[1]

                # downsample waveforms for this unit
                if len(waveforms) > num_waveforms:
                    inds = np.random.choice(len(waveforms), num_waveforms, replace=False)
                    waveforms = waveforms[inds, :, :]

                # Select only the common channels
                waveforms = waveforms[:, :, common_channel_indexes]
                unit_waveforms_data.append((unit_id, waveforms))

            if len(unit_waveforms_data) == 0:
                self.curve_waveforms.setData([], [])
                return

            # Get x-vectors with proper overlap handling (same as templates)
            xvectors = self.xvect[common_channel_indexes, :] * self.factor_x
            xvects = self.get_xvectors_not_overlap(xvectors, len(unit_waveforms_data))

            # Create separate curve items for each unit with unit-specific colors
            for i, (unit_id, waveforms) in enumerate(unit_waveforms_data):
                color = self.get_unit_color(unit_id)
                color_with_alpha = QT.QColor(color)
                alpha = self.settings["waveforms_alpha"]
                color_with_alpha.setAlpha(int(alpha * 255))  # 30% alpha

                # Get the x-vector for this specific unit (handles overlap setting)
                unit_xvect = xvects[i]
                self._plot_waveforms_for_unit(waveforms, color_with_alpha, width, common_channel_indexes, unit_xvect)

            # Clear the main curve since we're using separate curves for samples
            self.curve_waveforms.setData([], [])
            return
        else:
            # No waveforms to plot
            self.curve_waveforms.setData([], [])
            return

        # Handle plotting for single spike (plot_selected_spike case)
        if self.settings["plot_selected_spike"]:
            # Plot single spike only available in overlap mode
            if not self.settings["overlap"]:
                self.curve_waveforms.setData([], [])
                return

            # Single spike case - wf.shape[0] should equal width
            if wf.shape[0] != width:
                self.curve_waveforms.setData([], [])
                return

            if self.mode == "flatten":
                wf_flat = wf.T.ravel()
                xvect = np.arange(wf_flat.size)
                self.curve_waveforms.setData(xvect, wf_flat)
            elif self.mode == "geometry":
                ypos = self.contact_location[common_channel_indexes, 1]
                wf_plot = wf * self.gain_y * self.delta_y + ypos[None, :]

                connect = np.ones(wf_plot.shape, dtype="bool")
                connect[0, :] = 0
                connect[-1, :] = 0
                xvect = self.xvect[common_channel_indexes, :] * self.factor_x

                self.curve_waveforms.setData(xvect.ravel(), wf_plot.T.ravel(), connect=connect.T.ravel())

    def _qt_add_scalebars(self):
        """Add scale bars to the plot based on current settings"""
        import pyqtgraph as pg
        from .myqt import QT

        if not self.settings["x_scalebar"] and not self.settings["y_scalebar"]:
            # If neither scalebar is enabled, remove existing ones and return
            for item in self.scalebar_items:
                self.plot1.removeItem(item)
            self.scalebar_items.clear()
            return

        # Remove existing scalebars
        for item in self.scalebar_items:
            self.plot1.removeItem(item)
        self.scalebar_items = []        

        # Get scalebar values from settings
        scalebar_y_uv = self.settings["scalebar_y_uv"]
        scalebar_x_ms = self.settings["scalebar_x_ms"]

        # Convert time to samples
        scalebar_x_width = self.compute_scalebar_x_width(scalebar_x_ms)

        # Position scalebar in bottom-left corner of the view
        view_range = self.viewBox1.viewRange()
        x_min, x_max = view_range[0]
        y_min, y_max = view_range[1]
        
        # Scalebar position (offset from corner)
        x_offset = (x_max - x_min) * 0.2
        x_text_offset = (x_max - x_min) * 0.05
        y_offset = (y_max - y_min) * 0.2
        y_text_offset = (y_max - y_min) * 0.05

        scalebar_x_pos = x_min + x_offset
        scalebar_y_pos = y_min + y_offset
        x_text_pos = x_min + x_text_offset
        y_text_pos = y_min + y_text_offset
        
        # X scalebar (time)
        if self.settings["x_scalebar"]:
            
            x_line = pg.PlotCurveItem(
                [scalebar_x_pos, scalebar_x_pos + scalebar_x_width],
                [scalebar_y_pos, scalebar_y_pos],
                pen=pg.mkPen('white', width=3)
            )
            self.plot1.addItem(x_line)
            self.scalebar_items.append(x_line)
            
            # X scalebar label
            x_label = pg.TextItem(f"{scalebar_x_ms} ms", anchor=(0, 1), color='white')
            x_label.setPos(scalebar_x_pos, y_text_pos)
            self.plot1.addItem(x_label)
            self.scalebar_items.append(x_label)
        
        # Y scalebar (voltage)
        if self.settings["y_scalebar"]:
            y_scalebar_length = scalebar_y_uv * self.gain_y * self.delta_y
            y_line = pg.PlotCurveItem(
                [scalebar_x_pos, scalebar_x_pos],
                [scalebar_y_pos, scalebar_y_pos + y_scalebar_length],
                pen=pg.mkPen('white', width=3)
            )
            self.plot1.addItem(y_line)
            self.scalebar_items.append(y_line)
            
            # Y scalebar label
            y_label = pg.TextItem(f"{scalebar_y_uv} µV", anchor=(0.5, 0), color='white')
            y_label.setRotation(-90)
            y_label.setPos(x_text_pos, scalebar_y_pos + y_scalebar_length / 4)
            self.plot1.addItem(y_label)
            self.scalebar_items.append(y_label)

    def _qt_clear_waveforms_samples(self):
        """Clear all waveform sample curves from the plot"""
        for curve in self.curve_waveforms_samples:
            self.plot1.removeItem(curve)
        self.curve_waveforms_samples.clear()

    def _plot_waveforms_for_unit(self, waveforms, color, width, common_channel_indexes, unit_xvect):
        """Plot waveforms for a single unit with the specified color and x-vector"""
        import pyqtgraph as pg

        n_waveforms = waveforms.shape[0]
        if n_waveforms == 0:
            return

        if self.mode == "flatten":
            # For flatten mode, plot all waveforms as continuous lines
            all_x = []
            all_y = []
            for i in range(n_waveforms):
                wf_single = waveforms[i]  # (width, n_channels)
                wf_flat = wf_single.T.ravel()
                xvect = np.arange(len(wf_flat))
                all_x.extend(xvect)
                all_x.append(np.nan)  # Disconnect between waveforms
                all_y.extend(wf_flat)
                all_y.append(np.nan)

            curve = pg.PlotCurveItem(all_x, all_y, pen=pg.mkPen(color, width=1))
            self.plot1.addItem(curve)
            self.curve_waveforms_samples.append(curve)

        elif self.mode == "geometry":
            ypos = self.contact_location[common_channel_indexes, 1]

            all_x = []
            all_y = []
            all_connect = []

            for i in range(n_waveforms):
                wf_single = waveforms[i]  # (width, n_channels)
                wf_plot = wf_single * self.gain_y * self.delta_y + ypos[None, :]

                connect = np.ones(wf_plot.shape, dtype="bool")
                connect[0, :] = 0
                connect[-1, :] = 0

                all_x.extend(unit_xvect.ravel())
                all_y.extend(wf_plot.T.ravel())
                all_connect.extend(connect.T.ravel())

            all_x = np.array(all_x)
            all_y = np.array(all_y)
            all_connect = np.array(all_connect, dtype="bool")

            alpha = self.settings["waveforms_alpha"]
            curve = pg.PlotCurveItem(all_x, all_y, pen=pg.mkPen(color, width=1, alpha=int(alpha * 255)), connect=all_connect)
            self.plot1.addItem(curve)
            self.curve_waveforms_samples.append(curve)

    def _qt_on_spike_selection_changed(self):
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size
        if n_selected == 1 and self.settings["plot_selected_spike"]:
            self._qt_refresh(keep_range=True)
        else:
            # remove the line
            self.curve_waveforms.setData([], [])
            self._qt_clear_waveforms_samples()

    def _qt_on_unit_visibility_changed(self):
        keep_range = not (self.settings["auto_move_on_unit_selection"])
        auto_zoom = self.settings["auto_zoom_on_unit_selection"]
        self._qt_refresh(keep_range=keep_range, auto_zoom=auto_zoom)

    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import WheelZoomTool, Range1d, ColumnDataSource
        from bokeh.events import MouseWheel

        from .utils_panel import _bg_color, KeyboardShortcut, KeyboardShortcuts

        contact_locations = self.controller.get_contact_location()
        x = contact_locations[:, 0]
        y = contact_locations[:, 1]

        self.mode_selector = pn.widgets.Select(name="mode", options=["geometry", "flatten"])
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

        self.lines_data_source_geom = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.lines_geom = self.figure_geom.multi_line('xs', 'ys', source=self.lines_data_source_geom,
                                                      line_color='colors', line_width=2)
        self.patch_ys_lower_data_source = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.patch_ys_upper_data_source = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.lines_ys_lower = self.figure_geom.multi_line('xs', 'ys', source=self.patch_ys_lower_data_source,
                                                         line_color='colors', line_width=1, line_alpha=0.3)
        self.lines_ys_upper = self.figure_geom.multi_line('xs', 'ys', source=self.patch_ys_upper_data_source,
                                                         line_color='colors', line_width=1, line_alpha=0.3)

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

        self.lines_data_source_avg = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.lines_flatten_avg = self.figure_avg.multi_line('xs', 'ys', source=self.lines_data_source_avg,
                                                            line_color='colors', line_width=2)
        self.lines_data_source_std = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.lines_flatten_std = self.figure_std.multi_line('xs', 'ys', source=self.lines_data_source_std,
                                                            line_color='colors', line_width=2)
        self.vlines_data_source_avg = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.vlines_flatten_avg = self.figure_avg.multi_line('xs', 'ys', source=self.vlines_data_source_avg,
                                                             line_color='colors', line_width=1, line_dash='dashed')
        self.vlines_data_source_std = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.vlines_flatten_std = self.figure_std.multi_line('xs', 'ys', source=self.vlines_data_source_std,
                                                             line_color='colors', line_width=1, line_dash='dashed')

        self.scalebar_lines = []
        self.scalebar_labels = []

        # instantiate sources and lines for waveforms samples
        self.lines_data_source_wfs_flatten = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.lines_data_source_wfs_geom = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))

        waveforms_alpha = self.settings["waveforms_alpha"]
        self.lines_waveforms_samples_flatten = self.figure_avg.multi_line('xs', 'ys', source=self.lines_data_source_wfs_flatten,
                                                                          line_color='colors', line_width=1, line_alpha=waveforms_alpha)
        self.lines_waveforms_samples_geom = self.figure_geom.multi_line('xs', 'ys', source=self.lines_data_source_wfs_geom,
                                                                        line_color='colors', line_width=1, line_alpha=waveforms_alpha)

        self.geom_pane = pn.Column(
            self.figure_geom,  # Start with geometry
            sizing_mode="stretch_both"
        )
        self.flatten_pane = pn.Column(self.figure_avg, self.figure_std, sizing_mode="stretch_both")
        # Start with flatten hidden
        self.flatten_pane.visible = False

        # overlap shortcut
        shortcuts = [
            KeyboardShortcut(name="overlap", key="o", ctrlKey=True),
            KeyboardShortcut(name="waveforms", key="p", ctrlKey=True)
        ]
        shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        shortcuts_component.on_msg(self._panel_handle_shortcut)

        self.layout = pn.Column(
            pn.Row(self.mode_selector),
            self.geom_pane,
            self.flatten_pane,
            shortcuts_component,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

    def _panel_refresh(self, keep_range=False):
        self.mode = self.mode_selector.value
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size
        dict_visible_units = {k: False for k in self.controller.unit_ids}
        if self.settings["show_only_selected_cluster"] and n_selected == 1:
            ind = selected_inds[0]
            unit_index = self.controller.spikes[ind]["unit_index"]
            unit_id = self.controller.unit_ids[unit_index]
            dict_visible_units[unit_id] = True
        else:
            for unit_id in self.controller.get_visible_unit_ids():
                dict_visible_units[unit_id] = True

        if self.mode == "geometry":
            # zoom factor is reset
            if self.settings["auto_zoom_on_unit_selection"]:
                self.factor_x = 1.0
                self.gain_y = 0.02
            self._panel_refresh_mode_geometry(dict_visible_units, keep_range=keep_range)
        elif self.mode == "flatten":
            self._panel_refresh_mode_flatten(dict_visible_units, keep_range=keep_range)

        self._panel_refresh_spikes()

    def _panel_clear_scalebars(self):
        for line in self.scalebar_lines:
            if line in self.figure_geom.renderers:
                self.figure_geom.renderers.remove(line)
        self.scalebar_lines = []
        for label in self.scalebar_labels:
            if label in self.figure_geom.center:
                self.figure_geom.center.remove(label)
        self.scalebar_labels = []

    def _panel_add_scalebars(self):
        from bokeh.models import Span, Label

        if not self.settings["x_scalebar"] and not self.settings["y_scalebar"]:
            return

        # Get scalebar values from settings
        scalebar_y_uv = self.settings["scalebar_y_uv"]
        scalebar_x_ms = self.settings["scalebar_x_ms"]

        # Convert time to width
        scalebar_x_width = self.compute_scalebar_x_width(scalebar_x_ms)

        # Position scalebar in bottom-left corner of the view
        x_start = self.figure_geom.x_range.start
        x_end = self.figure_geom.x_range.end
        y_start = self.figure_geom.y_range.start
        y_end = self.figure_geom.y_range.end

        x_offset = (x_end - x_start) * 0.15
        x_text_offset = (x_end - x_start) * 0.1
        y_offset = (y_end - y_start) * 0.2
        y_text_offset = (y_end - y_start) * 0.1

        scalebar_x_pos = x_start + x_offset
        scalebar_y_pos = y_start + y_offset
        x_text_pos = x_start + x_text_offset
        y_text_pos = y_start + y_text_offset

        # X scalebar (time)
        if self.settings["x_scalebar"]:
            # Create x scalebar using line method
            x_line = self.figure_geom.line(
                [scalebar_x_pos, scalebar_x_pos + scalebar_x_width],
                [scalebar_y_pos, scalebar_y_pos],
                line_color='white',
                line_width=3
            )
            self.scalebar_lines.append(x_line)

            # X scalebar label
            x_label = Label(
                x=scalebar_x_pos + scalebar_x_width / 4,
                y=y_text_pos,
                text=f"{scalebar_x_ms} ms",
                text_color='white',
                text_align='center',
            )
            self.figure_geom.add_layout(x_label)
            self.scalebar_labels.append(x_label)

        if self.settings["y_scalebar"]:
            # Y scalebar (voltage)
            y_scalebar_length = scalebar_y_uv * self.gain_y * self.delta_y
            y_line = self.figure_geom.line(
                [scalebar_x_pos, scalebar_x_pos],
                [scalebar_y_pos, scalebar_y_pos + y_scalebar_length],
                line_color='white',
                line_width=3
            )
            self.scalebar_lines.append(y_line)

            # Y scalebar label
            y_label = Label(
                x=x_text_pos,
                y=scalebar_y_pos + y_scalebar_length / 4,
                text=f"{scalebar_y_uv} µV",
                text_color='white',
                angle=np.pi / 2,
                text_align='center'
            )
            self.figure_geom.add_layout(y_label)
            self.scalebar_labels.append(y_label)

    def _panel_on_mode_selector_changed(self, event):
        import panel as pn

        self.mode = self.mode_selector.value
        # Toggle visibility instead of swapping objects
        if self.mode == "flatten":
            self.geom_pane.visible = False
            self.flatten_pane.visible = True
        else:
            self.geom_pane.visible = True
            self.flatten_pane.visible = False
        self.refresh()

    def _panel_gain_zoom(self, event):
        import panel as pn

        current_time = time.perf_counter()
        if self.last_wheel_event_time is not None:
            time_elapsed = current_time - self.last_wheel_event_time
        else:
            time_elapsed = 1000
        if time_elapsed > _wheel_refresh_time:
            modifiers = event.modifiers

            def _enable_active_scroll(tool):
                self.figure_geom.toolbar.active_scroll = self.zoom_tool

            def _disable_active_scroll():
                self.figure_geom.toolbar.active_scroll = None

            if modifiers["shift"] and modifiers["alt"]:
                if self.mode == "geometry":
                    factor_ratio = 1.3 if event.delta > 0 else 1 / 1.3
                    # adjust y range and keep center
                    ymin = self.figure_geom.y_range.start
                    ymax = self.figure_geom.y_range.end
                    yrange = ymax - ymin
                    ymid = 0.5 * (ymin + ymax)
                    new_yrange = yrange * factor_ratio
                    new_ymin = ymid - new_yrange / 2.
                    new_ymax = ymid + new_yrange / 2.

                    def _do_range_update():
                        self.figure_geom.toolbar.active_scroll = None
                        self.figure_geom.y_range.start = new_ymin
                        self.figure_geom.y_range.end = new_ymax

                    pn.state.execute(_do_range_update, schedule=True)
                else:
                    pn.state.execute(_disable_active_scroll, schedule=True)
            elif modifiers["shift"]:
                pn.state.execute(_enable_active_scroll, schedule=True)
            elif modifiers["alt"]:
                if self.mode == "geometry":
                    factor = 1.3 if event.delta > 0 else 1 / 1.3
                    self.factor_x *= factor
                    self._panel_refresh_mode_geometry(keep_range=True)
                    self._panel_refresh_spikes()
                pn.state.execute(_disable_active_scroll, schedule=True)
            elif not modifiers["ctrl"]:
                if self.mode == "geometry":
                    factor = 1.3 if event.delta > 0 else 1 / 1.3
                    self.gain_y *= factor
                    self._panel_refresh_mode_geometry(keep_range=True)
                    self._panel_refresh_spikes()
                pn.state.execute(_disable_active_scroll, schedule=True)
        else:
            # Ignore the event if it occurs too quickly
            pn.state.execute(_disable_active_scroll, schedule=True)
        self.last_wheel_event_time = current_time

    def _panel_refresh_mode_geometry(self, dict_visible_units=None, keep_range=False):
        self._panel_clear_scalebars()

        dict_visible_units = dict_visible_units or self.controller.get_dict_unit_visible()
        visible_unit_ids = self.controller.get_visible_unit_ids()
        visible_unit_indices = self.controller.get_visible_unit_indices()

        if len(visible_unit_ids) == 0:
            self._panel_clear_data_sources()
            return

        common_channel_indexes = self.get_common_channels()
        if common_channel_indexes is None:
            self._panel_clear_data_sources()
            return

        xvectors = self.xvect[common_channel_indexes, :] * self.factor_x
        xvects = self.get_xvectors_not_overlap(xvectors, len(visible_unit_ids))

        xs = []
        ys = []
        colors = []

        patch_xs = []
        patch_ys_lower = []
        patch_ys_higher = []
        patch_colors = []
        for xvect, unit_index, unit_id in zip(xvects, visible_unit_indices, visible_unit_ids):
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            template_std = self.controller.templates_std

            ypos = self.contact_location[common_channel_indexes, 1]

            wf = template_avg
            wf = wf * self.gain_y * self.delta_y + ypos[None, :]
            # this disconnects each channel
            wf[0, :] = np.nan
            wf[-1, :] = np.nan

            color = self.get_unit_color(unit_id)

            xs.append(xvect.ravel())
            ys.append(wf.T.ravel())
            colors.append(color)

            # Don't plot std when waveform samples are being plotted (to avoid clutter)
            if self.settings["plot_std"] and (template_std is not None) and not self.settings["plot_waveforms_samples"]:

                wv_std = template_std[unit_index, :, :][:, common_channel_indexes]

                wv_lower = wf - wv_std * self.gain_y * self.delta_y
                wv_higher = wf + wv_std * self.gain_y * self.delta_y

                patch_xs.append(xvect.ravel())
                patch_ys_lower.append(wv_lower.T.ravel())
                patch_ys_higher.append(wv_higher.T.ravel())
                patch_colors.append(color)

        # self.lines_geom = self.figure_geom.multi_line(xs, ys, line_color=colors, line_width=2)
        self.lines_data_source_geom.data = dict(xs=xs, ys=ys, colors=colors)

        # # plot the mean plus/minus the std as semi-transparent lines
        self.patch_ys_lower_data_source.data = dict(xs=patch_xs, ys=patch_ys_lower, colors=patch_colors)
        self.patch_ys_upper_data_source.data = dict(xs=patch_xs, ys=patch_ys_higher, colors=patch_colors)

        if not keep_range:
            self.figure_geom.x_range.start = np.min(xvects) - 50
            self.figure_geom.x_range.end = np.max(xvects) + 50
            self.figure_geom.y_range.start = np.min(ypos) - 50
            self.figure_geom.y_range.end = np.max(ypos) + 50

        self._panel_add_scalebars()

    def _panel_refresh_mode_flatten(self, dict_visible_units=None, keep_range=False):
        if not self.settings["plot_selected_spike"] and not self.settings["plot_waveforms_samples"]:
            self.lines_data_source_wfs_flatten.data = dict(xs=[], ys=[], colors=[])

        dict_visible_units = dict_visible_units or self.controller.get_dict_unit_visible()

        common_channel_indexes = self.get_common_channels()
        if common_channel_indexes is None:
            self.lines_data_source_wfs_flatten.data = dict(xs=[], ys=[], colors=[])

        if len(self.controller.get_visible_unit_ids()) == 0:
            self._panel_clear_data_sources()
            return

        xs = []
        y_avgs = []
        y_stds = []
        colors = []
        for unit_index, (unit_id, visible) in enumerate(dict_visible_units.items()):
            if not visible:
                continue
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            template_std = self.controller.templates_std[unit_index, :, :][:, common_channel_indexes]
            nsamples, nchannels = template_avg.shape

            y_avg = template_avg.T.ravel()
            y_std = template_std.T.ravel()
            x = np.arange(y_avg.size)

            color = self.get_unit_color(unit_id)
            xs.append(x)
            y_avgs.append(y_avg)
            y_stds.append(y_std)
            colors.append(color)

        self.lines_data_source_avg.data = dict(xs=xs, ys=y_avgs, colors=colors)
        self.lines_data_source_std.data = dict(xs=xs, ys=y_stds, colors=colors)

        # add dashed vertical lines corresponding to the channels
        xs, ys_avg, ys_std, colors = [], [], [], []
        start = self.figure_avg.y_range.start
        if np.isnan(start):
            # estimate from the data
            start_avg = np.min(y_avgs) - 0.1 * np.ptp(y_avgs)
            end_avg = np.max(y_avgs) + 0.1 * np.ptp(y_avgs)
            start_std = 0
            end_std = np.max(y_stds) + 0.1 * np.ptp(y_stds)
        else:
            start_avg = self.figure_avg.y_range.start
            end_avg = self.figure_avg.y_range.end
            start_std = self.figure_std.y_range.start
            end_std = self.figure_std.y_range.end
        for ch in range(nchannels - 1):
            xline = (ch + 1) * nsamples
            xs.append([xline, xline])
            ys_avg.append([start_avg, end_avg])
            ys_std.append([start_std, end_std])
            colors.append("grey")
        self.vlines_data_source_avg.data = dict(xs=xs, ys=ys_avg, colors=colors)
        self.vlines_data_source_std.data = dict(xs=xs, ys=ys_std, colors=colors)

        self.shared_x_range.end = x[-1]
        self.figure_avg.x_range = self.shared_x_range
        self.figure_std.x_range = self.shared_x_range

    def _panel_refresh_one_spike(self):
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size

        if n_selected == 1 and self.settings["overlap"]:
            ind = selected_inds[0]
            common_channel_indexes = self.get_common_channels()
            wf, width = self.get_spike_waveform(ind)
            if wf is None:
                return
            wf = wf[:, common_channel_indexes]

            if wf.shape[0] == width:
                # this avoid border bugs
                if self.mode == "flatten":
                    wf = wf.T.ravel()
                    x = np.arange(wf.size)

                    color = "white"
                    source = self.lines_data_source_wfs_flatten
                    xs = [x]
                    ys = [wf]
                    colors = [color]
                elif self.mode == "geometry":
                    ypos = self.contact_location[common_channel_indexes, 1]

                    wf = wf * self.gain_y * self.delta_y + ypos[None, :]

                    # this disconnect
                    wf[0, :] = np.nan
                    xvect = self.xvect[common_channel_indexes, :] * self.factor_x

                    color = "white"
                    xs = [xvect.ravel()]
                    ys = [wf.T.ravel()]
                    colors = [color]
                    source = self.lines_data_source_wfs_geom
                source.data = dict(xs=xs, ys=ys, colors=colors)
        else:
            # clean existing lines
            if self.mode == "flatten":
                source = self.lines_data_source_wfs_flatten
            else:
                source = self.lines_data_source_wfs_geom
            source.data = dict(xs=[], ys=[], colors=[])

    def _panel_refresh_spikes(self):
        """Refresh spikes plotting for panel backend"""
        if self.settings["plot_selected_spike"] and self.settings["overlap"]:
            self._panel_refresh_one_spike()
        else:
            self._panel_refresh_waveforms_samples()

    def _panel_refresh_waveforms_samples(self):
        """Handle waveform samples plotting for panel backend"""
        if not self.settings["plot_waveforms_samples"]:
            self.lines_data_source_wfs_flatten.data = dict(xs=[], ys=[], colors=[])
            self.lines_data_source_wfs_geom.data = dict(xs=[], ys=[], colors=[])
            return

        if not self.controller.has_extension("waveforms"):
            self.lines_data_source_wfs_flatten.data = dict(xs=[], ys=[], colors=[])
            self.lines_data_source_wfs_geom.data = dict(xs=[], ys=[], colors=[])
            return

        num_waveforms = self.settings["num_waveforms"]
        if num_waveforms <= 0:
            self.lines_data_source_wfs_flatten.data = dict(xs=[], ys=[], colors=[])
            self.lines_data_source_wfs_geom.data = dict(xs=[], ys=[], colors=[])
            return

        common_channel_indexes = self.get_common_channels()
        if common_channel_indexes is None:
            self.lines_data_source_wfs_flatten.data = dict(xs=[], ys=[], colors=[])
            self.lines_data_source_wfs_geom.data = dict(xs=[], ys=[], colors=[])
            return

        wf_ext = self.controller.analyzer.get_extension("waveforms")
        visible_unit_ids = self.controller.get_visible_unit_ids()

        # Process waveforms per unit to maintain color association
        unit_waveforms_data = []
        width = None

        for unit_id in visible_unit_ids:
            waveforms = wf_ext.get_waveforms_one_unit(unit_id, force_dense=True)
            if waveforms is None or len(waveforms) == 0:
                continue

            if width is None:
                width = waveforms.shape[1]

            # downsample waveforms for this unit
            if len(waveforms) > num_waveforms:
                inds = np.random.choice(len(waveforms), num_waveforms, replace=False)
                waveforms = waveforms[inds, :, :]

            # Select only the common channels
            waveforms = waveforms[:, :, common_channel_indexes]
            unit_waveforms_data.append((unit_id, waveforms))

        if len(unit_waveforms_data) == 0:
            return

        # Get x-vectors with proper overlap handling (same as templates)
        xvectors = self.xvect[common_channel_indexes, :] * self.factor_x
        xvects = self.get_xvectors_not_overlap(xvectors, len(unit_waveforms_data))

        # Create separate lines for each unit with unit-specific colors
        for i, (unit_id, waveforms) in enumerate(unit_waveforms_data):
            color = self.get_unit_color(unit_id)
            # Convert to hex format and add alpha
            if hasattr(color, "name"):
                color_hex = color.name()
            else:
                color_hex = str(color)

            # Get the x-vector for this specific unit (handles overlap setting)
            unit_xvect = xvects[i]
            self._panel_plot_waveforms_for_unit(waveforms, color_hex, width, common_channel_indexes, unit_xvect)

    def _panel_plot_waveforms_for_unit(self, waveforms, color, width, common_channel_indexes, unit_xvect):
        """Plot waveforms for a single unit with the specified color and x-vector in panel backend"""
        n_waveforms = waveforms.shape[0]
        if n_waveforms == 0:
            return

        alpha = self.settings["waveforms_alpha"]

        if self.mode == "flatten":
            current_alpha = self.lines_waveforms_samples_flatten.glyph.line_alpha
            if current_alpha != alpha:
                self.lines_waveforms_samples_flatten.glyph.line_alpha = alpha
            # For flatten mode, plot all waveforms as continuous lines
            all_x = []
            all_y = []
            for i in range(n_waveforms):
                wf_single = waveforms[i]  # (width, n_channels)
                wf_flat = wf_single.T.ravel()
                xvect = np.arange(len(wf_flat))
                all_x.extend(xvect.tolist())
                all_x.append(None)  # Bokeh uses None for disconnection
                all_y.extend(wf_flat.tolist())
                all_y.append(None)

            source = self.lines_data_source_wfs_flatten

        elif self.mode == "geometry":
            current_alpha = self.lines_waveforms_samples_geom.glyph.line_alpha
            if current_alpha != alpha:
                self.lines_waveforms_samples_geom.glyph.line_alpha = alpha
            ypos = self.contact_location[common_channel_indexes, 1]

            all_x = []
            all_y = []

            for i in range(n_waveforms):
                wf_single = waveforms[i]  # (width, n_channels)
                wf_plot = wf_single * self.gain_y * self.delta_y + ypos[None, :]

                # Disconnect channels (first sample of each channel is NaN)
                wf_plot[0, :] = np.nan
                wf_plot[-1, :] = np.nan

                all_x.extend(unit_xvect.ravel().tolist())
                all_y.extend(wf_plot.T.ravel().tolist())

            source = self.lines_data_source_wfs_geom
        source.data = dict(xs=[all_x], ys=[all_y], colors=[color])

    def _panel_clear_data_sources(self):
        """Clear all data sources related to waveform samples in panel backend"""
        # geometry mode
        self.lines_data_source_geom.data = dict(xs=[], ys=[], colors=[])
        self.patch_ys_lower_data_source.data = dict(xs=[], ys=[], colors=[])
        self.patch_ys_upper_data_source.data = dict(xs=[], ys=[], colors=[])
        self.lines_data_source_wfs_geom.data = dict(xs=[], ys=[], colors=[])
        # flatten mode
        self.lines_data_source_avg.data = dict(xs=[], ys=[], colors=[])
        self.lines_data_source_std.data = dict(xs=[], ys=[], colors=[])
        self.lines_data_source_wfs_flatten.data = dict(xs=[], ys=[], colors=[])
        self.vlines_data_source_avg.data = dict(xs=[], ys=[], colors=[])
        self.vlines_data_source_std.data = dict(xs=[], ys=[], colors=[])

    def _panel_on_spike_selection_changed(self):
        import panel as pn
        pn.state.execute(self._panel_refresh_one_spike, schedule=True)

    def _panel_on_channel_visibility_changed(self):
        import panel as pn

        keep_range = not self.settings["auto_move_on_unit_selection"]
        pn.state.execute(lambda: self._panel_refresh(keep_range=keep_range), schedule=True)

    def _panel_handle_shortcut(self, event):
        if event.data == "overlap":
            self.toggle_overlap()
        elif event.data == "waveforms":
            self.toggle_waveforms()


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
* **ctrl + p** : toggle plot waveform samples
* **mouse wheel** : scale waveform amplitudes
* **alt + mouse wheel** : widen/narrow x axis
* **shift + mouse wheel** : zoom
* **shift + alt + mouse wheel** : scale vertical spacing between channels
"""
