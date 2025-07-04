from .view_base import ViewBase



class CrossCorrelogramView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _depend_on = ["correlograms"]
    _settings = [
        {'name': 'window_ms', 'type': 'float', 'value' : 50. },
        {'name': 'bin_ms', 'type': 'float', 'value' : 1.0 },
        {'name': 'display_axis', 'type': 'bool', 'value' : True },
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

    def _compute_split_ccg(self):
        """
        This method is used to compute the cross-correlogram for a split unit.
        It is called when the user selects a split unit in the controller.
        """
        from spikeinterface import NumpySorting
        from spikeinterface.postprocessing import compute_correlograms

        if self.controller.active_split is None:
            raise ValueError("No active split unit selected.")

        split_unit_id = self.controller.active_split["unit_id"]
        spike_inds = self.controller.get_spike_indices(split_unit_id, seg_index=None)
        split_indices = self.controller.active_split['indices']
        spikes_split_unit = self.controller.spikes[spike_inds]
        unit_index = spikes_split_unit[0]["unit_index"]
        # change unit_index for split indices
        spikes_split_unit["unit_index"][split_indices] = unit_index + 1
        split_sorting = NumpySorting(
            spikes=spikes_split_unit,
            sampling_frequency=self.controller.sampling_frequency,
            unit_ids=[f"{split_unit_id}-0", f"{split_unit_id}-1"]
        )
        ccg, bins = compute_correlograms(
            split_sorting,
            window_ms=self.settings['window_ms'],
            bin_ms=self.settings['bin_ms']
        )
        return ccg, bins
    
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
        if self.controller.active_split is None:
            n = len(visible_unit_ids)
            unit_ids = list(self.controller.unit_ids)
            colors = {
                unit_id: self.get_unit_color(unit_id) for unit_id in visible_unit_ids
            }
            ccg = self.ccg
            bins = self.bins
        else:
            split_unit_id = visible_unit_ids[0]
            n = 2
            unit_ids = [f"{split_unit_id}-0", f"{split_unit_id}-1"]
            visible_unit_ids = unit_ids
            ccg, bins = self._compute_split_ccg()
            split_unit_color = self.get_unit_color(split_unit_id)
            colors = {
                f"{split_unit_id}-0": split_unit_color,
                f"{split_unit_id}-1": split_unit_color,
            }
        
        for r in range(n):
            for c in range(r, n):
                
                i = unit_ids.index(visible_unit_ids[r])
                j = unit_ids.index(visible_unit_ids[c])
                count = ccg[i, j, :]
                
                plot = pg.PlotItem()
                if not self.settings['display_axis']:
                    plot.hideAxis('bottom')
                    plot.hideAxis('left')
                
                if r==c:
                    unit_id = visible_unit_ids[r]
                    color = colors[unit_id]
                else:
                    color = (120,120,120,120)
                
                curve = pg.PlotCurveItem(bins, count, stepMode='center', fillLevel=0, brush=color, pen=color)
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
        if self.controller.active_split is None:
            n = len(visible_unit_ids)
            unit_ids = list(self.controller.unit_ids)
            colors = {
                unit_id: self.get_unit_color(unit_id) for unit_id in visible_unit_ids
            }
            ccg = self.ccg
            bins = self.bins
        else:
            split_unit_id = visible_unit_ids[0]
            n = 2
            unit_ids = [f"{split_unit_id}-0", f"{split_unit_id}-1"]
            visible_unit_ids = unit_ids
            ccg, bins = self._compute_split_ccg()
            split_unit_color = self.get_unit_color(split_unit_id)
            colors = {
                f"{split_unit_id}-0": split_unit_color,
                f"{split_unit_id}-1": split_unit_color,
            }

        first_fig = None
        for r in range(n):
            row_plots = []
            for c in range(r, n):
                i = unit_ids.index(visible_unit_ids[r])
                j = unit_ids.index(visible_unit_ids[c])
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

                row_plots.append(fig)
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
