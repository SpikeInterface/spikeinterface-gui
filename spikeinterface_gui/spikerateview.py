from .view_base import ViewBase
import numpy as np


class SpikeRateView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _settings = [
            {'name': 'bin_s', 'type': 'int', 'value' : 60 },
        ]
    _need_compute = False

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        self._block_auto_refresh_and_notify = False
    
    def _on_settings_changed(self):
        self.refresh()

    def _qt_on_time_info_updated(self):
        if self.combo_seg.currentIndex() != self.controller.get_time()[1]:
            self._block_auto_refresh_and_notify = True
            self.refresh()
            self._block_auto_refresh_and_notify = False

    def on_use_times_updated(self):
        self.refresh()

    ## Qt ##

    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        tb = self.qt_widget.view_toolbar
        self.combo_seg = QT.QComboBox()
        tb.addWidget(self.combo_seg)
        self.combo_seg.addItems([f'Segment {segment_index}' for segment_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self._qt_change_segment)

        h = QT.QHBoxLayout()
        self.layout.addLayout(h)

        self.plot = pg.PlotItem(viewBox=None)
        self.graphicsview = pg.GraphicsView()
        self.graphicsview.setCentralItem(self.plot)
        self.layout.addWidget(self.graphicsview)

    def _qt_change_segment(self):
        segment_index = self.combo_seg.currentIndex()
        self.controller.set_time(segment_index=segment_index)
        if not self._block_auto_refresh_and_notify:
            self.refresh()
            self.notify_time_info_updated()

    def _qt_refresh(self):
        import pyqtgraph as pg

        self.plot.clear()

        segment_index = self.controller.get_time()[1]
        # Update combo_seg if it doesn't match the current segment index
        if self.combo_seg.currentIndex() != segment_index:
            self.combo_seg.setCurrentIndex(segment_index)
        
        visible_unit_ids = self.controller.get_visible_unit_ids()
        
        sampling_frequency = self.controller.sampling_frequency

        total_frames = self.controller.final_spike_samples
        bins_s = self.settings['bin_s']
        t_start, _  = self.controller.get_t_start_t_stop()
        num_bins = max(total_frames[segment_index] // int(sampling_frequency) // bins_s, 1)

        for r, unit_id in enumerate(visible_unit_ids):

            spike_inds = self.controller.get_spike_indices(unit_id, segment_index=segment_index)
            spikes = self.controller.spikes[spike_inds]['sample_index']

            count, bins = np.histogram(spikes, bins=num_bins)
            
            color = self.get_unit_color(unit_id)
            curve = pg.PlotCurveItem(
                (bins[1:]+bins[:-1])/(2*sampling_frequency) + t_start, 
                count/bins_s, 
                pen=pg.mkPen(color, width=2)
            )
            self.plot.addItem(curve)

        # Make lower y-lim 0
        self.plot.getViewBox().autoRange()
        current_max_y_range = self.plot.getViewBox().viewRange()[1][1]
        self.plot.getViewBox().setYRange(0, current_max_y_range)
        
    ## panel ##

    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import Range1d, ColumnDataSource
        from .utils_panel import _bg_color

        segment_index = self.controller.get_time()[1]
        self.segment_selector = pn.widgets.Select(
            name="",
            options=[f"Segment {i}" for i in range(self.controller.num_segments)],
            value=f"Segment {segment_index}",
        )
        self.segment_selector.param.watch(self._panel_change_segment, 'value')

        t_start, t_stop  = self.controller.get_t_start_t_stop()
        self.x_range = Range1d(start=t_start, end=t_stop)
        self.y_range = Range1d(start=0, end=100)
        self.rate_fig = bpl.figure(
            tools="pan,wheel_zoom,reset",
            active_drag="pan",
            active_scroll="wheel_zoom",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            x_range=self.x_range,
            y_range=self.y_range,
            outline_line_color="white",
            sizing_mode="stretch_both",
        )
        self.rate_fig.toolbar.logo = None
        self.rate_fig.grid.visible = False

        self.spike_rate_data_source = ColumnDataSource(data=dict(xs=[], ys=[], colors=[]))
        self.lines_spike_rate = self.rate_fig.multi_line('xs', 'ys', source=self.spike_rate_data_source,
                                                         line_color='colors', line_width=2)

        self.layout = pn.Column(
            pn.Row(self.segment_selector, sizing_mode="stretch_width"),
            pn.Row(self.rate_fig, sizing_mode="stretch_both"),
        )
        self.is_warning_active = False

    def _panel_refresh(self):
        from bokeh.models import Range1d

        segment_index = self.controller.get_time()[1]
        segment_index_from_selector = self.segment_selector.options.index(self.segment_selector.value)
        if segment_index != segment_index_from_selector:
            self.segment_selector.value = f"Segment {segment_index}"

        visible_unit_ids = self.controller.get_visible_unit_ids()

        sampling_frequency = self.controller.sampling_frequency

        total_frames = self.controller.final_spike_samples
        bins_s = self.settings['bin_s']
        num_bins = total_frames[segment_index] // int(sampling_frequency) // bins_s
        t_start, t_stop  = self.controller.get_t_start_t_stop()

        max_count = 0
        xs = []
        ys = []
        colors = []
        for unit_id in visible_unit_ids:

            spike_inds = self.controller.get_spike_indices(unit_id, segment_index=segment_index)
            spikes = self.controller.spikes[spike_inds]['sample_index']

            count, bins = np.histogram(spikes, bins=num_bins)
            
            # Get color from controller
            color = self.get_unit_color(unit_id)
            xs.append((bins[1:]+bins[:-1]) / (2*sampling_frequency) + t_start)
            ys.append(count / bins_s)
            colors.append(color)
            max_count = max(max_count, np.max(count/bins_s))

        self.spike_rate_data_source.data = dict(xs=xs, ys=ys, colors=colors)

        self.x_range.start = t_start
        self.x_range.end = t_stop
        self.y_range.start = 0
        self.y_range.end = max_count*1.2

    def _panel_change_segment(self, event):
        segment_index = int(self.segment_selector.value.split()[-1])
        self.controller.set_time(segment_index=segment_index)
        self.refresh()
        self.notify_time_info_updated()


SpikeRateView._gui_help_txt = """
# SpikeRateView View

This view shows firing rate for spikes per `bin_s`.
"""
