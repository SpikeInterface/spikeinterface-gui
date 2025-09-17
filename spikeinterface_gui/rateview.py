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
    
    def _on_settings_changed(self):
        self.refresh()

    ## Qt ##

    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        tb = self.qt_widget.view_toolbar
        self.combo_seg = QT.QComboBox()
        tb.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {seg_index}' for seg_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self.refresh)

        h = QT.QHBoxLayout()
        self.layout.addLayout(h)

        self.plot = pg.PlotItem(viewBox=None)
        self.graphicsview = pg.GraphicsView()
        self.graphicsview.setCentralItem(self.plot)
        self.layout.addWidget(self.graphicsview)

    def _qt_refresh(self):
        import pyqtgraph as pg

        self.plot.clear()

        seg_index =  self.combo_seg.currentIndex()

        visible_unit_ids = self.controller.get_visible_unit_ids()
        
        sampling_frequency = self.controller.sampling_frequency

        total_frames = self.controller.final_spike_samples
        bins_s = self.settings['bin_s']
        num_bins = total_frames[seg_index] // int(sampling_frequency) // bins_s
        
        for r, unit_id in enumerate(visible_unit_ids):

            spike_inds = self.controller.get_spike_indices(unit_id, seg_index=seg_index)
            spikes = self.controller.spikes[spike_inds]['sample_index']

            count, bins = np.histogram(spikes, bins=num_bins)
            
            color = self.get_unit_color(unit_id)
            curve = pg.PlotCurveItem(
                (bins[1:]+bins[:-1])/(2*sampling_frequency), 
                count/bins_s, 
                pen=pg.mkPen(color, width=2)
            )
            self.plot.addItem(curve)
        
    ## panel ##

    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from .utils_panel import _bg_color

        self.segment_index = 0
        self.segment_selector = pn.widgets.Select(
            name="",
            options=[f"Segment {i}" for i in range(self.controller.num_segments)],
            value=f"Segment {self.segment_index}",
        )
        self.segment_selector.param.watch(self._panel_change_segment, 'value')

        self.rate_fig = bpl.figure(
            width=250,
            height=250,
            tools="pan,wheel_zoom,reset",
            active_drag="pan",
            active_scroll="wheel_zoom",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
        )
        self.rate_fig.toolbar.logo = None
        self.rate_fig.grid.visible = False

        self.layout = pn.Column(
            pn.Row(self.segment_selector, sizing_mode="stretch_width"),
            pn.Row(self.rate_fig,sizing_mode="stretch_both"),
        )
        self.is_warning_active = False

    def _panel_refresh(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.layouts import gridplot
        from .utils_panel import _bg_color

        seg_index =  self.segment_index

        visible_unit_ids = self.controller.get_visible_unit_ids()

        sampling_frequency = self.controller.sampling_frequency

        total_frames = self.controller.final_spike_samples
        bins_s = self.settings['bin_s']
        num_bins = total_frames[seg_index] // int(sampling_frequency) // bins_s

        # clear fig
        self.rate_fig.renderers = []
        
        for unit_id in visible_unit_ids:

            spike_inds = self.controller.get_spike_indices(unit_id, seg_index=seg_index)
            spikes = self.controller.spikes[spike_inds]['sample_index']

            count, bins = np.histogram(spikes, bins=num_bins)
            
            # Get color from controller
            color = self.get_unit_color(unit_id)

            line = self.rate_fig.line(
                x=(bins[1:]+bins[:-1])/(2*sampling_frequency),
                y=count/bins_s,
                color=color,
                line_width=2,
            )

        self.rate_fig.y_range.start = 0

    def _panel_change_segment(self, event):
        self.segment_index = int(self.segment_selector.value.split()[-1])
        self.refresh()



SpikeRateView._gui_help_txt = """
# SpikeRateView View

This view shows firing rate for spikes per `bin_s`.
"""
