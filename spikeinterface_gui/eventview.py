import numpy as np
from .view_base import ViewBase

class EventView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _depend_on = ["events"]
    _settings = [
        {'name': 'max_trials', 'type': 'int', 'value' : 50 },
        {'name': 'window_start', 'type': 'float', 'value': -0.2},
        {'name': 'window_end', 'type': 'float', 'value': 0.5},
        {'name': 'alpha_psth', 'type': 'float', 'value': 0.5},
        {'name': 'num_bins', 'type': 'int', 'value': 50},
    ]
    _need_compute = False

    def __init__(self, controller=None, parent=None, backend="qt"):
        self.mode = 'rasters'  # or 'psth'
        self.selected_unit = None
        self.selected_event_key = None
        ViewBase.__init__(self, controller=controller, parent=parent, backend=backend)


    def get_aligned_spikes(self, unit_ids):
        event_times = np.array(self.controller.get_events(self.selected_event_key))
        window_s = [self.settings['window_start'], self.settings['window_end']]
        window_samples = [int(w * self.controller.sampling_frequency) for w in window_s]

        if len(event_times) > self.settings['max_trials']:
            event_times = event_times[np.random.choice(len(event_times), self.settings['max_trials'], replace=False)]

        aligned_spikes_dict = {}
        for selected_unit in unit_ids:
            aligned_spikes = []
            # TODO: deal with this!!! (at controller level)
            segment_index = 0
            inds = self.controller.get_spike_indices(selected_unit, segment_index=segment_index)
            spike_times = self.controller.spikes["sample_index"][inds]

            for et in event_times:
                rel_spikes = spike_times - et
                rel_spikes = rel_spikes[(rel_spikes >= window_samples[0]) & (rel_spikes <= window_samples[1])]
                aligned_spikes.append(rel_spikes / self.controller.sampling_frequency)  # convert to seconds
            aligned_spikes_dict[selected_unit] = aligned_spikes
        return aligned_spikes_dict

    def _qt_make_layout(self):
        import pyqtgraph as pg
        from .myqt import QT, QtWidgets

        layout = QtWidgets.QVBoxLayout()
        # Mode selection
        toolbar = QtWidgets.QHBoxLayout()
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(['Rasters', 'PSTH'])
        self.mode_combo.currentIndexChanged.connect(self._qt_on_mode_changed)
        toolbar.addWidget(self.mode_combo)
        # Event key selection
        event_keys = list(self.controller.events.keys())
        if len(event_keys) > 1:
            self.event_combo = QtWidgets.QComboBox()
            self.event_combo.addItems(event_keys)
            self.event_combo.currentIndexChanged.connect(self._qt_on_event_changed)
            toolbar.addWidget(self.event_combo)
        self.selected_event_key = event_keys[0] if event_keys else None
        layout.addLayout(toolbar)
        # Pyqtgraph PlotWidget
        self.pg_plot = pg.PlotWidget()
        self.scatter = pg.ScatterPlotItem(size=10, pxMode=True)
        self.pg_plot.addItem(self.scatter)
        
        # Create vertical line at x=0 once
        self.zero_line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('gray', width=2, style=QT.Qt.DashLine))
        self.pg_plot.addItem(self.zero_line)

        layout.addWidget(self.pg_plot)
        self.layout = layout

    def _qt_on_mode_changed(self, idx):
        self.mode = 'rasters' if idx == 0 else 'psth'
        self._qt_refresh()

    def _qt_on_event_changed(self, idx):
        self.selected_event_key = self.event_combo.currentText()
        self._qt_refresh()

    def _qt_refresh(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.scatter.clear()
        # Clear everything including scatter
        self.pg_plot.clear()
        self.pg_plot.addItem(self.zero_line)

        if self.mode == 'rasters':
            # Clear all plot items except scatter
            self.pg_plot.addItem(self.scatter)

        # Get visible units from controller
        visible_units = self.controller.get_visible_unit_ids()
        if not visible_units or self.selected_event_key is None:
            return

        aligned_spikes_by_unit = self.get_aligned_spikes(visible_units)
        window_s = [self.settings['window_start'], self.settings['window_end']]
        
        for selected_unit in visible_units:
            aligned_spikes = aligned_spikes_by_unit[selected_unit]
            color = QT.QColor(self.get_unit_color(selected_unit))
            
            if self.mode == 'rasters':
                all_x = []
                all_y = []
                for i, trial in enumerate(aligned_spikes):
                    if len(trial) > 0:
                        all_x.extend(trial)
                        y = [i]*len(trial)
                        all_y.extend(y)
                if all_x:
                    self.scatter.addPoints(x=np.array(all_x), y=np.array(all_y), pen=pg.mkPen(None), brush=color, symbol="|")
            else:
                from pyqtgraph import BarGraphItem

                all_spikes = np.concatenate(aligned_spikes) if aligned_spikes else np.array([])
                all_y_hists = []
                if len(all_spikes) > 0:
                    bins = np.linspace(window_s[0], window_s[1], 51)
                    y, x = np.histogram(all_spikes, bins=bins)
                    # Use bin centers for plotting
                    bin_centers = (x[:-1] + x[1:]) / 2
                    # Create a bar graph item instead of using stepMode
                    width = (x[1] - x[0]) * 0.8  # 80% of bin width
                    color.setAlpha(int(self.settings['alpha_psth']*255))
                    bg = BarGraphItem(x=bin_centers, height=y, width=width, brush=color, pen=pg.mkPen(color, width=2))
                    self.pg_plot.addItem(bg)
                    all_y_hists.extend(y)
                    # Set ranges
        if self.mode == 'rasters':
            self.pg_plot.setYRange(-0.5, len(aligned_spikes)+0.5, padding=0)
            self.pg_plot.setXRange(window_s[0], window_s[1], padding=0)
            self.pg_plot.setLabel('left', 'Event #')
            self.pg_plot.setLabel('bottom', 'Time (s)')
            self.pg_plot.setTitle(f'Rasters aligned to {self.selected_event_key}')
        else:
            self.pg_plot.setXRange(window_s[0], window_s[1], padding=0.05)
            if len(all_y_hists) > 0:
                self.pg_plot.setYRange(0, max(all_y_hists)*1.1, padding=0)
            self.pg_plot.setLabel('left', 'Spike count')
            self.pg_plot.setLabel('bottom', 'Time (s)')
            self.pg_plot.setTitle(f'PSTH aligned to {self.selected_event_key}')
            

    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, Span, Range1d
        from .utils_panel import _bg_color

        top_items = []
        self.panel_mode_select = pn.widgets.Select(name="Mode", value="Rasters", options=["Rasters", "PSTH"])
        self.panel_mode_select.param.watch(self._panel_on_mode_changed, 'value')
        top_items.append(self.panel_mode_select)
        event_keys = list(self.controller.events.keys())
        if len(event_keys) > 1:
            self.panel_event_select = pn.widgets.Select(name="Event", value=event_keys[0], options=event_keys)
            self.panel_event_select.param.watch( self._panel_on_event_changed, 'value')
            top_items.append(self.panel_event_select)
        self.selected_event_key = event_keys[0]

        top_bar = pn.Row(*top_items, sizing_mode="stretch_width")
        self.bins = np.linspace(
            self.settings["window_start"],
            self.settings["window_end"],
            self.settings["num_bins"]
        )
        self.bin_centers = (self.bins[:-1] + self.bins[1:]) / 2
        self.scatter_source = ColumnDataSource(data={"x": [], "y": [], "color": []})
        self.hist_source = ColumnDataSource(data={"center": [], "height": [], "color": []})
        self.x_range = Range1d(start=self.settings['window_start'], end=self.settings['window_end'])
        self.panel_fig = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset,wheel_zoom",
            active_scroll="wheel_zoom",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            x_range=self.x_range,
            styles={"flex": "1"}
        )
        self.scatter = self.panel_fig.scatter(
            "x",
            "y",
            source=self.scatter_source,
            color="color",
        )
        self.bar = self.panel_fig.vbar(
            x="center",
            top="height",
            width=self.bins[1] - self.bins[0],
            color="color",
            source=self.hist_source,
            alpha=self.settings['alpha_psth']
        )
        self.vline = Span(location=0, dimension='height', line_color='white', line_width=2, line_dash='dashed')

        self.panel_fig.yaxis.axis_label = 'Event #'
        self.panel_fig.xaxis.axis_label = 'Time (s)'
        self.panel_fig.toolbar.logo = None
        self.panel_fig.add_layout(self.vline)
        self.panel_plot_pane = pn.pane.Bokeh(self.panel_fig, sizing_mode="stretch_both")
        self.layout = pn.Column(
            top_bar,
            self.panel_plot_pane,
            sizing_mode="stretch_both",
        )

    def _panel_on_mode_changed(self, event):
        self.mode = 'rasters' if event.new == 'Rasters' else 'psth'
        self._panel_refresh()

    def _panel_on_event_changed(self, event):
        self.selected_event_key = event.new
        self._panel_refresh()

    def _panel_refresh(self):
        import numpy as np
        import bokeh.plotting as bpl

        visible_units = self.controller.get_visible_unit_ids()
        aligned_spikes_by_unit = self.get_aligned_spikes(visible_units)
        if self.mode == 'rasters':
            self.hist_source.data = {"center": [], "height": [], "color": []}  # Clear histogram data
            self.panel_fig.title.text = f'Rasters aligned to {self.selected_event_key}'
            self.panel_fig.yaxis.axis_label = 'Event #'
            all_x = []
            all_y = []
            all_colors = []
            for selected_unit in visible_units:
                aligned_spikes = aligned_spikes_by_unit[selected_unit]
                color = self.get_unit_color(selected_unit)
                for i, trial in enumerate(aligned_spikes):
                    if len(trial) > 0:
                        all_x.extend(trial)
                        y = [i] * len(trial)
                        all_y.extend(y)
                        all_colors.extend([color] * len(trial))
            self.scatter_source.data = {
                "x": np.array(all_x), 
                "y": np.array(all_y), 
                "color": all_colors
            }
        else:
            self.scatter_source.data = {"x": [], "y": [], "color": []}  # Clear scatter data

            all_centers = []
            all_heights = []
            all_colors = []
            for selected_unit in visible_units:
                aligned_spikes = aligned_spikes_by_unit[selected_unit]
                all_spikes = np.concatenate(aligned_spikes) if aligned_spikes else np.array([])
                hist, _ = np.histogram(all_spikes, bins=self.bins)
                all_centers.extend(list(self.bin_centers))
                all_heights.extend(list(hist))
                all_colors.extend([self.get_unit_color(selected_unit)] * len(hist))
            self.hist_source.data = {
                "center": all_centers,
                "height": all_heights,
                "color": all_colors
            }
            self.panel_fig.yaxis.axis_label = 'Spike count'
            self.panel_fig.title.text = f'PSTH aligned to {self.selected_event_key}'

        # adjust x_range if needed
        if self.settings["window_start"] != self.x_range.start:
            self.x_range.start = self.settings["window_start"]
        if self.settings["window_end"] != self.x_range.end:
            self.x_range.end = self.settings["window_end"]
            
    def _panel_on_settings_changed(self):
        self.bins = np.linspace(
            self.settings["window_start"],
            self.settings["window_end"],
            self.settings["num_bins"]
        )
        self.bin_centers = (self.bins[:-1] + self.bins[1:]) / 2
        self.x_range.start = self.settings['window_start']
        self.x_range.end = self.settings['window_end']
        self.bar.glyph.width = self.bins[1] - self.bins[0]
        self._panel_refresh()
