from .view_base import ViewBase



class CrossCorrelogramView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _depend_on = ["correlograms"]
    _settings = [
                      {'name': 'window_ms', 'type': 'float', 'value' : 50. },
                      {'name': 'bin_ms', 'type': 'float', 'value' : 1.0 },
                      {'name': 'display_axis', 'type': 'bool', 'value' : True },
                      {'name': 'max_visible', 'type': 'int', 'value' : 8 },
        ]
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

        self.ccg, self.bins = self.controller.get_correlograms()

    
    def _on_settings_changed(self):
        self.ccg = None
        self.refresh()

    def _compute(self):
        self.ccg, self.bins = self.controller.compute_correlograms(
                self.settings['window_ms'],  self.settings['bin_ms'])
    
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
        
        if self.ccg is None:
            return
        
        visible_unit_ids = self.controller.get_visible_unit_ids()
        visible_unit_ids = visible_unit_ids[:self.settings['max_visible']]
        
        n = len(visible_unit_ids)
        
        unit_ids = list(self.controller.unit_ids)
        
        for r in range(n):
            for c in range(r, n):
                
                i = unit_ids.index(visible_unit_ids[r])
                j = unit_ids.index(visible_unit_ids[c])
                count = self.ccg[i, j, :]
                
                plot = pg.PlotItem()
                if not self.settings['display_axis']:
                    plot.hideAxis('bottom')
                    plot.hideAxis('left')
                
                if r==c:
                    unit_id = visible_unit_ids[r]
                    color = self.get_unit_color(unit_id)
                else:
                    color = (120,120,120,120)
                
                curve = pg.PlotCurveItem(self.bins, count, stepMode='center', fillLevel=0, brush=color, pen=color)
                plot.addItem(curve)
                self.grid.addItem(plot, row=r, col=c)
    
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
        from .utils_panel import _bg_color, insert_warning, clear_warning

        # clear previous plot
        self.plots = []

        if self.ccg is None:
            return

        visible_unit_ids = self.controller.get_visible_unit_ids()

        # Show warning above the plot if too many visible units
        if len(visible_unit_ids) > self.settings['max_visible']:
            warning_msg = f"Only showing first {self.settings['max_visible']} units out of {len(visible_unit_ids)} visible units"
            insert_warning(self, warning_msg)
            self.is_warning_active = True
            return
        if self.is_warning_active:
            clear_warning(self)
            self.is_warning_active = False

        visible_unit_ids = visible_unit_ids[:self.settings['max_visible']]

        n = len(visible_unit_ids)
        unit_ids = list(self.controller.unit_ids)
        for r in range(n):
            row_plots = []
            for c in range(r, n):
                
                i = unit_ids.index(visible_unit_ids[r])
                j = unit_ids.index(visible_unit_ids[c])
                count = self.ccg[i, j, :]

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
                if r == c:
                    unit_id = visible_unit_ids[r]
                    color = self.get_unit_color(unit_id)
                    fill_alpha = 0.7
                else:
                    color = "lightgray"
                    fill_alpha = 0.4

                p.quad(
                    top=count,
                    bottom=0,
                    left=self.bins[:-1],
                    right=self.bins[1:],
                    fill_color=color,
                    line_color=color,
                    alpha=fill_alpha,
                )

                row_plots.append(p)
            # Fill row with None for proper spacing
            full_row = [None] * r + row_plots + [None] * (n - len(row_plots))
            self.plots.append(full_row)

        if len(self.plots) > 0:
            grid = gridplot(self.plots, toolbar_location="right", sizing_mode="stretch_both")
            self.layout[0] = pn.Column(
                grid,
                styles={'background-color': f'{_bg_color}'}
            )
        else:
            self.layout[0] = self.empty_plot_pane



CrossCorrelogramView._gui_help_txt = """
## Correlograms View

This view shows the auto-correlograms and cross-correlograms of the selected units.
"""
