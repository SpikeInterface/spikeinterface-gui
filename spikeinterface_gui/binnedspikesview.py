from .view_base import ViewBase
import numpy as np


class BinnedSpikesView(ViewBase):
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
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)

        self.grid = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.grid)


    def _qt_refresh(self):
        import pyqtgraph as pg

        self.grid.clear()
        
        visible_unit_ids = self.controller.get_visible_unit_ids()
        
        sampling_frequency = self.controller.sampling_frequency

        total_frames = self.controller.final_spike_sample
        num_bins = total_frames // int(sampling_frequency) // self.settings['bin_s']
        
        for r, unit_id in enumerate(visible_unit_ids):

            spikes = self.controller.spikes[self.controller._spike_index_by_units[unit_id]]['sample_index']
            count, bins = np.histogram(spikes/sampling_frequency, bins=num_bins)
            
            plot = pg.PlotItem()
            
            color = self.get_unit_color(unit_id)

            curve = pg.PlotCurveItem(bins, count, stepMode='center', fillLevel=0, brush=color, pen=color)
            plot.addItem(curve)
            self.grid.addItem(plot, row=r)
    
    ## panel ##

    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from .utils_panel import _bg_color

        empty_fig = bpl.figure(
            sizing_mode="stretch_both",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
        )
        self.empty_plot_pane = pn.pane.Bokeh(empty_fig, sizing_mode="stretch_both")

        self.layout = pn.Column(
            self.empty_plot_pane,
            sizing_mode="stretch_both",
        )
        self.is_warning_active = False

        self.plots = []

    def _panel_refresh(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.layouts import gridplot
        from .utils_panel import _bg_color

        # clear previous plot
        self.plots = []

        visible_unit_ids = self.controller.get_visible_unit_ids()

        n = len(visible_unit_ids)

        sampling_frequency = self.controller.sampling_frequency

        total_frames = self.controller.final_spike_sample
        num_bins = total_frames // int(sampling_frequency) // self.settings['bin_s']

        row_plots = []
        for r, unit_id in enumerate(visible_unit_ids):

            spikes = self.controller.spikes[self.controller._spike_index_by_units[unit_id]]['sample_index']
            count, bins = np.histogram(spikes, bins=num_bins)
            
            # Create Bokeh figure
            p = bpl.figure(
                width=250,
                height=250,
                tools="pan,wheel_zoom,reset",
                active_drag="pan",
                active_scroll="wheel_zoom",
                background_fill_color=_bg_color,
                border_fill_color=_bg_color,
                outline_line_color="white",
            )
            p.toolbar.logo = None

            # Get color from controller
            color = self.get_unit_color(unit_id)
            fill_alpha = 0.7

            p.quad(
                top=count,
                bottom=0,
                left=bins[:-1]/sampling_frequency,
                right=bins[1:]/sampling_frequency,
                fill_color=color,
                line_color=color,
                alpha=fill_alpha,
            )

            row_plots.append(p)

        self.plots = [[row_plot] for row_plot in row_plots]

        if len(self.plots) > 0:
            grid = gridplot(self.plots, toolbar_location="right", sizing_mode="stretch_both")
            self.layout[0] = pn.Row(
                grid,
                styles={'background-color': f'{_bg_color}'}
            )
        else:
            self.layout[0] = self.empty_plot_pane


BinnedSpikesView._gui_help_txt = """
# BinnedSpikesView View

This view shows the number of spikes per some time unit.
"""
