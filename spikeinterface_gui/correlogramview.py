import numpy as np

from .view_base import ViewBase



class CorrelogramView(ViewBase):
    id = "correlogram"
    _supported_backend = ['qt', 'panel']
    _depend_on = ["correlograms"]
    _settings = [
        {'name': 'window_ms', 'type': 'float', 'value' : 50. },
        {'name': 'bin_ms', 'type': 'float', 'value' : 1.0 },
        {'name': 'display_axis', 'type': 'bool', 'value' : True },
        {'name': 'show_cross_correlograms', 'type': 'bool', 'value' : True },
    ]
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

        self.figure_cache = {}
        self.max_cache_size = 20

        # the settings are changed before self.ccg is set, so that _on_settings_changed
        # does not discard the loaded correlograms
        self.ccg, self.bins = None, None
        ccg, bins = self.controller.get_correlograms()
        if bins is not None:
            # match the loaded correlograms, otherwise any setting change would discard them
            self.settings['window_ms'] = float(bins[-1] - bins[0])
            self.settings['bin_ms'] = float(bins[1] - bins[0])
        if self.controller.has_extension('comparison'):
            # in comparison mode only the ACGs are available, the off-diagonal is zeros
            self.settings['show_cross_correlograms'] = False
        self.ccg, self.bins = ccg, bins

    def _on_settings_changed(self):
        # only a new window/bin needs a re-compute, the display settings just need new figures
        if self.bins is not None:
            window_ms = self.bins[-1] - self.bins[0]
            bin_ms = self.bins[1] - self.bins[0]
            if not (np.isclose(window_ms, self.settings['window_ms']) and np.isclose(bin_ms, self.settings['bin_ms'])):
                self.ccg = None
        self.figure_cache = {}
        self.refresh()

    def _get_columns(self, r, n):
        """The columns of row r: the upper triangle, or only the diagonal (the ACG)"""
        if self.settings['show_cross_correlograms']:
            return range(r, n)
        return range(r, r + 1)

    def get_acg_ymax(self, visible_unit_ids):
        """The y max shared by the auto-correlograms of the visible units, so that they compare"""
        unit_ids = list(self.controller.unit_ids)
        inds = [unit_ids.index(unit_id) for unit_id in visible_unit_ids]
        ymax = max((self.ccg[i, i, :].max() for i in inds), default=0)
        return float(ymax) * 1.05 if ymax > 0 else 1.

    def _compute(self):
        self.ccg, self.bins = self.controller.compute_correlograms(
            self.settings['window_ms'],  self.settings['bin_ms']
        )
        # clear cache
        self.figure_cache = {}

    def on_unit_color_changed(self):
        # clear cache
        self.figure_cache = {}
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

    def _reinitialize(self):
        self.ccg, self.bins = self.controller.get_correlograms()
        self.figure_cache = {}
        self._refresh()

    def _qt_refresh(self):
        import pyqtgraph as pg

        self.grid.clear()
        
        if self.ccg is None:
            return
        
        visible_unit_ids = self.controller.get_visible_unit_ids()

        n = len(visible_unit_ids)
        unit_ids = list(self.controller.unit_ids)
        colors = {
            unit_id: self.get_unit_color(unit_id) for unit_id in visible_unit_ids
        }
        ccg = self.ccg
        bins = self.bins
        acg_plots = []
        
        for r in range(n):
            for c in self._get_columns(r, n):
                unit_id1 = visible_unit_ids[r]
                unit_id2 = visible_unit_ids[c]
                if (unit_id1, unit_id2) in self.figure_cache:
                    plot = self.figure_cache[(unit_id1, unit_id2)]
                    if self.controller.main_settings["color_mode"] == 'color_by_visibility':
                        # Update color in cached figure
                        if r == c:
                            unit_id = visible_unit_ids[r]
                            color = colors[unit_id]
                            for item in plot.items:
                                if hasattr(item, 'setBrush') and hasattr(item, 'setPen'):
                                    item.setBrush(color)
                                    item.setPen(color)
                else:
                    # create new plot
                    i = unit_ids.index(visible_unit_ids[r])
                    j = unit_ids.index(visible_unit_ids[c])
                    count = ccg[i, j, :]

                    plot = pg.PlotItem()
                    if not self.settings['display_axis']:
                        plot.hideAxis('bottom')
                        plot.hideAxis('left')

                    if r == c:
                        unit_id = visible_unit_ids[r]
                        color = colors[unit_id]
                    else:
                        color = (120, 120, 120, 120)

                    curve = pg.PlotCurveItem(bins, count, stepMode='center', fillLevel=0, brush=color, pen=color)
                    plot.addItem(curve)
                    # cache plot
                    if len(self.figure_cache) >= self.max_cache_size:
                        self.figure_cache.pop(next(iter(self.figure_cache)))
                    self.figure_cache[(unit_id1, unit_id2)] = plot
                if r == c:
                    acg_plots.append(plot)
                if self.settings['show_cross_correlograms']:
                    self.grid.addItem(plot, row=r, col=c)
                else:
                    # only ACGs: side by side on one row
                    self.grid.addItem(plot, row=0, col=r)

        if not self.settings['show_cross_correlograms']:
            # the ACGs share the y axis (also when zooming), the plots can come from the cache
            # with a link to a plot that is not shown anymore
            ymax = self.get_acg_ymax(visible_unit_ids) if len(acg_plots) > 0 else None
            for i, plot in enumerate(acg_plots):
                plot.setYLink(None if i == 0 else acg_plots[0])
                plot.setYRange(0, ymax, padding=0)
    
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
        # ids of the figures in the grid currently shown
        self._panel_shown_figure_ids = set()

        self.layout = pn.Column(
            self.empty_plot_pane,
            sizing_mode="stretch_both",
        )

    def _panel_refresh(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.layouts import gridplot
        from bokeh.models import Range1d
        from .utils_panel import _bg_color

        if self.ccg is None:
            return

        visible_unit_ids = self.controller.get_visible_unit_ids()

        n = len(visible_unit_ids)
        unit_ids = list(self.controller.unit_ids)
        colors = {
            unit_id: self.get_unit_color(unit_id) for unit_id in visible_unit_ids
        }
        ccg = self.ccg
        bins = self.bins
        figures = []
        acg_figs = []
        first_fig = None
        for r in range(n):
            row_plots = []
            for c in self._get_columns(r, n):
                unit1 = visible_unit_ids[r]
                unit2 = visible_unit_ids[c]

                # a cached figure still in the shown grid cannot be moved to the new grid
                # (bokeh renders it blank), so it is re-created
                cached_fig = self.figure_cache.get((unit1, unit2))
                if cached_fig is not None and id(cached_fig) not in self._panel_shown_figure_ids:
                    fig = cached_fig
                    # for the color_by_visibility
                    if self.controller.main_settings["color_mode"] == 'color_by_visibility':
                        # Update color in cached figure
                        if r == c:
                            unit_id = visible_unit_ids[r]
                            color = colors[unit_id]
                            for renderer in fig.renderers:
                                if hasattr(renderer, 'glyph') and hasattr(renderer.glyph, 'fill_color'):
                                    renderer.glyph.fill_color = color
                                    renderer.glyph.line_color = color
                else:
                    # create new figure
                    i = unit_ids.index(unit1)
                    j = unit_ids.index(unit2)
                    count = ccg[i, j, :]

                    # Create Bokeh figure
                    if first_fig is not None:
                        extra_kwargs = dict(x_range=first_fig.x_range)
                    else:
                        extra_kwargs = dict()
                    fig = bpl.figure(
                        width=250,
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

                    # Get color from controller
                    if r == c:
                        unit_id = visible_unit_ids[r]
                        color = colors[unit_id]
                        fill_alpha = 0.7
                    else:
                        color = "lightgray"
                        fill_alpha = 0.4

                    fig.quad(
                        top=count,
                        bottom=0,
                        left=bins[:-1],
                        right=bins[1:],
                        fill_color=color,
                        line_color=color,
                        alpha=fill_alpha,
                    )
                    if first_fig is None:
                        first_fig = fig
                    # Cache figure
                    if len(self.figure_cache) >= self.max_cache_size:
                        self.figure_cache.pop(next(iter(self.figure_cache)))
                    self.figure_cache[(unit1, unit2)] = fig
                if r == c:
                    acg_figs.append(fig)
                row_plots.append(fig)
            if self.settings['show_cross_correlograms']:
                # Fill row with None for proper spacing
                full_row = [None] * r + row_plots + [None] * (n - r - len(row_plots))
                figures.append(full_row)
            else:
                # only ACGs: side by side on one row
                if len(figures) == 0:
                    figures.append([])
                figures[0].extend(row_plots)

        if not self.settings['show_cross_correlograms']:
            # the ACGs share the y axis (also when zooming), the figures can come from the cache
            acg_y_range = Range1d(0, self.get_acg_ymax(visible_unit_ids))
            for fig in acg_figs:
                fig.y_range = acg_y_range

        grid = gridplot(figures, toolbar_location="right", sizing_mode="stretch_both")
        grid.toolbar.logo = None
        self._panel_shown_figure_ids = {id(fig) for row in figures for fig in row if fig is not None}
        self.layout[0] = pn.Column(
            grid,
            styles={'background-color': f'{_bg_color}'}
        )



CorrelogramView._gui_help_txt = """
## Correlograms View

This view shows the auto-correlograms and cross-correlograms of the selected units.

### Settings
- **window_ms** / **bin_ms** : the correlogram window and bin size (needs a re-compute).
- **display_axis** : show the axes of each plot.

The auto-correlograms share the y axis, so that the firing of the units can be compared.
- **show_cross_correlograms** : show the cross-correlograms (upper triangle), or only the
  auto-correlograms side by side. In comparison mode only the auto-correlograms of both
  sorters are available, so this is off by default.
"""
