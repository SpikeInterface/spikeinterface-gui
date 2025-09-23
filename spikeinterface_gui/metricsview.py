import warnings
import numpy as np


from .view_base import ViewBase

from spikeinterface.postprocessing.unit_locations import possible_localization_methods


_default_visible_metrics = ("snr", "firing_rate")

class MetricsView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _settings = [
        {'name': 'num_bins', 'type': 'int', 'value' : 30 },
    ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        units_table = controller.get_units_table()

        self.visible_metrics_dict = dict()
        for col in units_table.columns:
            if units_table[col].dtype.kind == "f":
                self.visible_metrics_dict[col] = col in _default_visible_metrics

        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleClickToPosition
    
        self.layout = QT.QVBoxLayout()

        visible_metrics_tree = []
        for col, visible in self.visible_metrics_dict.items():
            visible_metrics_tree.append(
                {'name': str(col), 'type': 'bool', 'value': visible}
            )
        self.qt_visible_metrics = pg.parametertree.Parameter.create( name='visible columns', type='group', children=visible_metrics_tree)
        self.tree_visible_metrics = pg.parametertree.ParameterTree(parent=self.qt_widget)
        self.tree_visible_metrics.header().hide()
        self.tree_visible_metrics.setParameters(self.qt_visible_metrics, showTop=True)
        # self.tree_visible_metrics.setWindowTitle(u'visible columns')
        # self.tree_visible_metrics.setWindowFlags(QT.Qt.Window)
        self.qt_visible_metrics.sigTreeStateChanged.connect(self._qt_on_visible_metrics_changed)
        self.layout.addWidget(self.tree_visible_metrics)
        self.tree_visible_metrics.hide()
        

        tb = self.qt_widget.view_toolbar
        but = QT.QPushButton('metrics')
        but.clicked.connect(self._qt_select_metrics)
        tb.addWidget(but)

        self.grid = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.grid)

        self._qt_creat_grid()

    def _qt_creat_grid(self):
        import pyqtgraph as pg
        from .myqt import QT

        visible_metrics = [k for k, v in self.visible_metrics_dict.items() if v]
        self.grid.clear()
        n = len(visible_metrics)
        if len(visible_metrics) == 0:
            return
        
        

        self.plots = {}
        for r in range(n):
            for c in range(r, n):
                
                plot = pg.PlotItem()
                self.grid.addItem(plot, row=r, col=c)
                self.plots[(r, c)] = plot

                if r == c:
                    label_style = {'color': "#7BFF00", 'font-size': '14pt'}
                    plot.setLabel('bottom', visible_metrics[c], **label_style)

    def _qt_refresh(self):
        import pyqtgraph as pg
        from .myqt import QT


        visible_metrics = [k for k, v in self.visible_metrics_dict.items() if v]
        n = len(visible_metrics)

        units_table = self.controller.get_units_table()
        white_brush = QT.QColor('white')
        white_brush.setAlpha(200)


        for r in range(n):
            for c in range(r, n):
                col1 = visible_metrics[r]
                col2 = visible_metrics[c]

                plot = self.plots[(r, c)]
                plot.clear()
                if c > r:
                    scatter = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=white_brush, size=11, pxMode = True)
                    plot.addItem(scatter)
                    values1 = units_table[col1].values
                    values2 = units_table[col2].values

                    scatter.setData(x=values2, y=values1)

                    visible_unit_ids = self.controller.get_visible_unit_ids()
                    visible_unit_ids = self.controller.get_visible_unit_indices()

                    for unit_ind, unit_id in self.controller.iter_visible_units():
                        color = self.get_unit_color(unit_id)
                        scatter.addPoints(x=[values2[unit_ind]], y=[values1[unit_ind]],  pen=pg.mkPen(None), brush=color)

                    # self.scatter.addPoints(x=scatter_x[unit_id], y=scatter_y[unit_id],  pen=pg.mkPen(None), brush=color)
                    # self.scatter_select.setData(selected_scatter_x, selected_scatter_y)
                elif c == r:
                    values1 = units_table[visible_metrics[r]].values

                    count, bins = np.histogram(values1, bins=self.settings['num_bins'])
                    curve = pg.PlotCurveItem(bins, count, stepMode='center', fillLevel=0, brush=white_brush, pen=white_brush)
                    plot.addItem(curve)

                    for unit_ind, unit_id in self.controller.iter_visible_units():
                        x = values1[unit_ind]
                        color = self.get_unit_color(unit_id)
                        line = pg.InfiniteLine(pos=x, angle=90, movable=False, pen=color)
                        plot.addItem(line)

    def _qt_select_metrics(self):
        if not self.tree_visible_metrics.isVisible():
            self.tree_visible_metrics.show()
        else:
            self.tree_visible_metrics.hide()
    
        self.layout.addWidget(self.tree_visible_metrics)
    
    def _qt_on_visible_metrics_changed(self):
        
        for col in self.visible_metrics_dict.keys():
            # update the internal dict with the qt tree
            self.visible_metrics_dict[col] = self.qt_visible_metrics[col]
        self._qt_creat_grid()
        self.refresh()

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        import pandas as pd
        from .utils_panel import _bg_color

        # Create metrics selection widget
        self.metrics_select = pn.widgets.MultiChoice(
            name="Visible Metrics",
            value=list([k for k, v in self.visible_metrics_dict.items() if v]),
            options=list(self.visible_metrics_dict.keys()),
        )
        self.metrics_select.param.watch(self._panel_on_metrics_changed, 'value')

        empty_fig = bpl.figure(
            sizing_mode="stretch_both",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
        )
        self.empty_plot_pane = pn.pane.Bokeh(empty_fig, sizing_mode="stretch_both")

        self.layout = pn.Column(
            pn.Row(self.metrics_select, sizing_mode="stretch_width", height=160),
            self.empty_plot_pane,
            sizing_mode="stretch_both"
        )

        self.plots = []

    def _panel_on_metrics_changed(self, event):
        # Update visible metrics dict
        for col in self.visible_metrics_dict.keys():
            self.visible_metrics_dict[col] = col in event.new
        self.refresh()

    def _panel_refresh(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.layouts import gridplot
        from bokeh.models import ColumnDataSource
        from .utils_panel import _bg_color

        visible_metrics = [k for k, v in self.visible_metrics_dict.items() if v]
        n = len(visible_metrics)

        # clear previous plot
        self.plots = []

        if n > 0:
            # Calculate plot size based on number of metrics
            plot_size = max(200, min(400, 800 // n))
            units_table = self.controller.get_units_table()

            # Create plots only for upper triangular matrix
            for r in range(n):
                row_plots = []
                for c in range(r, n):
                    col1 = visible_metrics[r]
                    col2 = visible_metrics[c]
                    values1 = units_table[col1].values
                    values2 = units_table[col2].values

                    plot = bpl.figure(
                        width=plot_size, height=plot_size,
                        background_fill_color=_bg_color,
                        border_fill_color=_bg_color,
                        outline_line_color="white",
                        toolbar_location=None
                    )
                    plot.grid.visible = False

                    if r == c:
                        # Diagonal - histogram
                        plot.xaxis.axis_label = col1
                        plot.yaxis.axis_label = "Count"
                        # Create histogram
                        hist, edges = np.histogram(values1, bins=self.settings['num_bins'])
                        if len(hist) > 0 and max(hist) > 0:
                            plot.quad(
                                top=hist, bottom=0, left=edges[:-1], right=edges[1:],
                                fill_color='lightgray', line_color='white', alpha=0.7
                            )

                            # Add vertical lines for visible units
                            max_hist = max(hist)
                            for unit_ind, unit_id in self.controller.iter_visible_units():
                                x = values1[unit_ind]
                                color = self.get_unit_color(unit_id)
                                plot.line([x, x], [0, max_hist], line_width=2, color=color, alpha=0.8)
                    else:
                        # Off-diagonal - scatter plot
                        plot.xaxis.axis_label = col2
                        plot.yaxis.axis_label = col1

                        colors = ["gray"] * len(values1)
                        for unit_ind, unit_id in self.controller.iter_visible_units():
                            colors[unit_ind] = self.get_unit_color(unit_id)

                        # Plot all points in light color first
                        all_source = ColumnDataSource({
                            'x': values2,
                            'y': values1,
                            'color': colors
                        })
                        plot.scatter('x', 'y', source=all_source, size=8, color='color', alpha=0.5)
                    row_plots.append(plot)
                # Fill row with None for proper spacing
                full_row = [None] * r + row_plots + [None] * (n - len(row_plots))
                self.plots.append(full_row)

                # Create the final layout
                grid = gridplot(self.plots, toolbar_location="right", sizing_mode="stretch_both")
                self.layout[1] = pn.Column(
                    grid,
                    styles={'background-color': f'{_bg_color}'}
                )
        else:
            self.layout[1] = self.empty_plot_pane
