import numpy as np

from .view_base import ViewBase



class MainTemplateView(ViewBase):
    id = "maintemplate"
    _supported_backend = ['qt', 'panel']
    _depend_on = ["templates"]
    _settings = [
        {'name': 'ncols', 'type': 'int', 'value': 3 },
        {'name': 'width_mode', 'type': 'list', 'limits' : ['half_width', 'peak_width'] },
    ]
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

        nbefore, nafter = self.controller.get_waveform_sweep()
        fs = self.controller.sampling_frequency
        self.time_vect = np.arange(-nbefore, nafter) / fs * 1000.
        factor = self.controller.get_template_upsampling_factor()
        self.time_vect_high = np.arange(-nbefore*factor, nafter*factor) / (fs * factor) * 1000.

    
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
        from pyqtgraph.Qt import QtCore

        self.grid.clear()
        
        visible_unit_ids = self.controller.get_visible_unit_ids()

        n = len(visible_unit_ids)
        ncols = self.settings['ncols']

        for i in range(n):
            col = i % ncols
            row = i // ncols

            unit_id = visible_unit_ids[i]

            plot = pg.PlotItem()
            self.grid.addItem(plot, row=row, col=col)

            template, template_high, peak_data = self.controller.get_upsampled_templates(unit_id)
            
            color = self.get_unit_color(unit_id)

            if template_high is None:
                template_high = template
                plot_template = False
            else:
                plot_template = True

            plot.addItem(pg.PlotCurveItem(
                [self.time_vect_high[0], self.time_vect_high[-1]],
                [0, 0],
                color="grey")
            )

            if plot_template:
                curve = pg.PlotCurveItem(self.time_vect, template,
                                        pen=pg.mkPen("white", width=1., style=QtCore.Qt.DashLine))
                plot.addItem(curve)

            curve = pg.PlotCurveItem(self.time_vect_high, template_high,
                                     pen=pg.mkPen(color, width=2))
            plot.addItem(curve)

            times = self.time_vect_high

            if peak_data is not None:
                # trough
                peak_inds =  peak_data[['trough_index']].values
                scatter = pg.ScatterPlotItem(x = times[peak_inds], y = template_high[peak_inds],
                                            size=10, pxMode = True, color="white", symbol="t")
                plot.addItem(scatter)
                
                names = ('peak_before', 'peak_after')
                peak_inds =  peak_data[[f'{k}_index' for k in names]].values
                scatter = pg.ScatterPlotItem(x = times[peak_inds], y = template_high[peak_inds],
                                            size=10, pxMode = True, color="white", symbol="t1")
                plot.addItem(scatter)

                all_names = ('trough', 'peak_before', 'peak_after')
                peak_inds =  peak_data[[f'{k}_index' for k in all_names]].values
                # Vertical dotted lines from peak to zero
                for ind in peak_inds:
                    x = [times[ind], times[ind]]
                    y = [0, template_high[ind]]
                    plot.addItem(pg.PlotCurveItem(x, y, pen=pg.mkPen("white", width=1., style=QtCore.Qt.DotLine)))

                for k in all_names:
                    if self.settings['width_mode'] == 'half_width':
                        left = peak_data[f'{k}_half_width_left']
                        right = peak_data[f'{k}_half_width_right']
                    if self.settings['width_mode'] == 'peak_width':
                        left = peak_data[f'{k}_width_left']
                        right = peak_data[f'{k}_width_right']
                    
                    if left != -1:
                        inds = [left, right]
                        x = times[inds]
                        # y = template_high[inds] <<<< this make a strange line
                        m = np.mean(template_high[inds])
                        y = [m, m ]
                        plot.addItem(pg.PlotCurveItem(x, y, pen=pg.mkPen("white", width=1., style=QtCore.Qt.DotLine)))

    ## Panel ##
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
        empty_fig.toolbar.logo = None
        self.empty_plot_pane = pn.pane.Bokeh(empty_fig, sizing_mode="stretch_both")

        self.layout = pn.Column(
            self.empty_plot_pane,
            sizing_mode="stretch_both",
        )

    def _panel_refresh(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.layouts import gridplot
        from bokeh.models import Span
        from .utils_panel import _bg_color

        visible_unit_ids = self.controller.get_visible_unit_ids()
        n = len(visible_unit_ids)
        ncols = self.settings['ncols']

        if n == 0:
            empty_fig = bpl.figure(
                sizing_mode="stretch_both",
                background_fill_color=_bg_color,
                border_fill_color=_bg_color,
                outline_line_color="white",
            )
            empty_fig.toolbar.logo = None
            self.layout[0] = pn.pane.Bokeh(empty_fig, sizing_mode="stretch_both")
            return

        figures = []
        row_plots = []
        first_fig = None

        for i in range(n):
            unit_id = visible_unit_ids[i]
            template, template_high, peak_data = self.controller.get_upsampled_templates(unit_id)

            color = self.get_unit_color(unit_id)

            if template_high is None:
                template_high = template
                plot_template = False
            else:
                plot_template = True

            # Share x_range across all figures
            extra_kwargs = {}
            if first_fig is not None:
                extra_kwargs = dict(x_range=first_fig.x_range)

            fig = bpl.figure(
                width=300,
                height=250,
                tools="pan,wheel_zoom,reset",
                active_drag="pan",
                active_scroll="wheel_zoom",
                background_fill_color=_bg_color,
                border_fill_color=_bg_color,
                outline_line_color="white",
                **extra_kwargs,
            )
            fig.toolbar.logo = None
            fig.grid.visible = False

            if first_fig is None:
                first_fig = fig

            # Zero line (grey)
            fig.line(
                [self.time_vect_high[0], self.time_vect_high[-1]],
                [0, 0],
                line_color="grey",
                line_width=1,
            )

            # Original template as white dashed line (if upsampled exists)
            if plot_template:
                fig.line(
                    self.time_vect.tolist(),
                    template.tolist(),
                    line_color="white",
                    line_width=1,
                    line_dash="dashed",
                )

            # Upsampled template in unit color
            fig.line(
                self.time_vect_high.tolist(),
                template_high.tolist(),
                line_color=color,
                line_width=2,
            )

            times = self.time_vect_high

            if peak_data is not None:
                # Trough (downward triangle)
                trough_inds = peak_data[['trough_index']].values
                fig.scatter(
                    x=times[trough_inds].tolist(),
                    y=template_high[trough_inds].tolist(),
                    size=10,
                    color="white",
                    marker="inverted_triangle",
                )

                # Peaks before/after (upward triangle)
                names = ('peak_before', 'peak_after')
                peak_inds = peak_data[[f'{k}_index' for k in names]].values
                fig.scatter(
                    x=times[peak_inds].tolist(),
                    y=template_high[peak_inds].tolist(),
                    size=10,
                    color="white",
                    marker="triangle",
                )

                # Peaks before/after (upward triangle)
                all_names = ('trough', 'peak_before', 'peak_after')
                peak_inds = peak_data[[f'{k}_index' for k in all_names]].values
                # Vertical dotted lines from peak to zero
                for ind in peak_inds:
                    fig.line(
                        [times[ind], times[ind]],
                        [0, template_high[ind]],
                        line_color="white",
                        line_width=1,
                        line_dash="dotted",
                    )

                # Width lines
                for k in all_names:
                    if self.settings['width_mode'] == 'half_width':
                        left = peak_data[f'{k}_half_width_left']
                        right = peak_data[f'{k}_half_width_right']
                    if self.settings['width_mode'] == 'peak_width':
                        left = peak_data[f'{k}_width_left']
                        right = peak_data[f'{k}_width_right']

                    if left != -1:
                        inds = [left, right]
                        x = times[inds]
                        m = float(np.mean(template_high[inds]))
                        fig.line(
                            x.tolist(),
                            [m, m],
                            line_color="white",
                            line_width=1,
                            line_dash="dotted",
                        )

            row_plots.append(fig)

            # When row is full or last unit, add to figures
            if len(row_plots) == ncols or i == n - 1:
                # Pad with None if row is not full
                while len(row_plots) < ncols:
                    row_plots.append(None)
                figures.append(row_plots)
                row_plots = []

        grid = gridplot(figures, toolbar_location="right", sizing_mode="stretch_both")
        grid.toolbar.logo = None
        self.layout[0] = pn.Column(
            grid,
            styles={'background-color': f'{_bg_color}'},
        )


MainTemplateView._gui_help_txt = """
## Main Template View

Display average template on main channel.
If the `template_metrics` are computed, it also displayed the template signal
used to compute metrics (usually upsampled) and the trough/peak_before/peak_after 
positions and widths.

- troughs are negative extrema and are displayed with a downward triangle symbol
- peaks are positive extrema and are displayed with an upward triangle symbol

x-axis represents time and is in units of milliseconds.
y-axis represents the electrical signal. The units depend on your preprocessing 
steps, but is usually in uV.
"""