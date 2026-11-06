import numpy as np

from .view_base import ViewBase
from .comparelabelsview import get_categorical_properties, get_category_colors


_default_visible_metrics = ("firing_rate", "isi_violations_ratio", "amplitude_median", "presence_ratio")
_default_color = '#BBBBBB'


class CompareMetricsView(ViewBase):
    """
    Scatter plots of unit metrics, sorter 1 against sorter 2, for the matched pairs at the
    agreement threshold shared with the unit Venn view. Clicking a point makes its pair visible.
    """
    id = "comparemetrics"
    _supported_backend = ['qt', 'panel']
    _depend_on = ['comparison']
    _settings = [
        {'name': 'log_scale', 'type': 'bool', 'value': False},
        {'name': 'num_columns', 'type': 'int', 'value': 2},
        {'name': 'max_categories', 'type': 'int', 'value': 20},
    ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        table = controller.units_table
        metrics = [col for col in controller.get_shared_unit_properties() if table[col].dtype.kind in 'if']
        default_metrics = [m for m in metrics if m in _default_visible_metrics] or metrics[:4]
        self.visible_metrics_dict = {m: m in default_metrics for m in metrics}
        ViewBase.__init__(self, controller=controller, parent=parent, backend=backend)

    def get_visible_metrics(self):
        return [m for m, visible in self.visible_metrics_dict.items() if visible]

    def get_color_options(self):
        """'none' then each categorical property seen from either sorter, as {label: (property, analyzer_index)}"""
        options = {'none': None}
        for name in get_categorical_properties(self.controller, self.settings['max_categories']):
            for analyzer_index in (1, 2):
                options[f'{name} ({self.controller.get_analyzer_name(analyzer_index)})'] = (name, analyzer_index)
        return options

    def get_pairs(self):
        return self.controller.get_venn_unit_ids()['matched']

    def get_pair_colors(self, pairs, color_option):
        """One color per pair, and the legend as a list of (category, color)"""
        if color_option is None or len(pairs) == 0:
            return [_default_color] * len(pairs), []
        name, analyzer_index = color_option
        column = self.controller.units_table[name]
        unit_ids = [pair[analyzer_index - 1] for pair in pairs]
        values = column.loc[unit_ids].astype(object).where(column.loc[unit_ids].notna(), "n/a").astype(str)
        categories = sorted(column.astype(object).where(column.notna(), "n/a").astype(str).unique())
        color_by_category = dict(
            zip(
                categories,
                get_category_colors(
                    categories,
                    cmap=self.controller.main_settings['label_colormap']
                )
            )
        )
        return [color_by_category[v] for v in values], list(color_by_category.items())

    def get_metric_values(self, metric, pairs):
        """(x, y) for sorter 1 and sorter 2, log10(value + .001) when log_scale is on"""
        table = self.controller.units_table
        x = table.loc[[pair[0] for pair in pairs], metric].to_numpy(dtype='float64')
        y = table.loc[[pair[1] for pair in pairs], metric].to_numpy(dtype='float64')
        if self.settings['log_scale']:
            with np.errstate(invalid='ignore', divide='ignore'):
                x, y = np.log10(x + 1e-3), np.log10(y + 1e-3)
        return x, y

    def get_axis_label(self, analyzer_index):
        name = self.controller.get_analyzer_name(analyzer_index)
        return f'{name} log10(value + .001)' if self.settings['log_scale'] else name

    @staticmethod
    def get_equality_line(x, y):
        """The diagonal over the range of the finite values, or None"""
        values = np.concatenate([x, y])
        values = values[np.isfinite(values)]
        if values.size == 0:
            return None
        return [values.min(), values.max()]

    def get_visible_mask(self, pairs):
        visible_unit_ids = set(self.controller.get_visible_unit_ids())
        return np.array([pair[0] in visible_unit_ids and pair[1] in visible_unit_ids for pair in pairs], dtype=bool)

    def select_pair(self, pair_index):
        pair = self.get_pairs()[pair_index]
        self.controller.set_visible_unit_ids(list(pair))
        self.notify_unit_and_channel_visibility_changed()
        self.refresh()

    def get_legend_html(self, legend):
        return "  ".join(f'<span style="color:{color}">■ {category}</span>' for category, color in legend)

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        tree = [{'name': str(m), 'type': 'bool', 'value': v} for m, v in self.visible_metrics_dict.items()]
        self.qt_visible_metrics = pg.parametertree.Parameter.create(name='visible metrics', type='group', children=tree)
        self.tree_visible_metrics = pg.parametertree.ParameterTree(parent=self.qt_widget)
        self.tree_visible_metrics.header().hide()
        self.tree_visible_metrics.setParameters(self.qt_visible_metrics, showTop=True)
        self.qt_visible_metrics.sigTreeStateChanged.connect(self._qt_on_visible_metrics_changed)
        self.layout.addWidget(self.tree_visible_metrics)
        self.tree_visible_metrics.hide()

        but = QT.QPushButton('metrics')
        but.clicked.connect(lambda: self.tree_visible_metrics.setVisible(not self.tree_visible_metrics.isVisible()))
        self.qt_widget.view_toolbar.addWidget(but)

        header = QT.QHBoxLayout()
        header.addWidget(QT.QLabel('color by'))
        self.color_combo = QT.QComboBox()
        self._color_options = self.get_color_options()
        self.color_combo.addItems(list(self._color_options.keys()))
        self.color_combo.currentTextChanged.connect(self.refresh)
        header.addWidget(self.color_combo)
        self.legend_label = QT.QLabel('')
        header.addWidget(self.legend_label)
        header.addStretch()
        self.layout.addLayout(header)

        self.grid = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.grid)

    def _qt_on_visible_metrics_changed(self):
        for m in self.visible_metrics_dict.keys():
            self.visible_metrics_dict[m] = self.qt_visible_metrics[m]
        self.refresh()

    def _qt_on_settings_changed(self):
        self.refresh()

    def _qt_on_unit_visibility_changed(self):
        self.refresh()

    def _qt_refresh(self):
        import pyqtgraph as pg

        self.grid.clear()
        pairs = self.get_pairs()
        colors, legend = self.get_pair_colors(pairs, self._color_options.get(self.color_combo.currentText()))
        self.legend_label.setText(self.get_legend_html(legend))
        visible_mask = self.get_visible_mask(pairs)
        brushes = [pg.mkBrush(color) for color in colors]
        pens = [pg.mkPen('#FFFFFF', width=2) if v else pg.mkPen(None) for v in visible_mask]
        sizes = np.where(visible_mask, 12, 7)

        num_columns = max(self.settings['num_columns'], 1)
        for i, metric in enumerate(self.get_visible_metrics()):
            plot = self.grid.addPlot(row=i // num_columns, col=i % num_columns, title=metric)
            plot.setLabel('bottom', self.get_axis_label(1))
            plot.setLabel('left', self.get_axis_label(2))
            x, y = self.get_metric_values(metric, pairs)
            line = self.get_equality_line(x, y)
            if line is not None:
                plot.plot(line, line, pen=pg.mkPen('#888888', style=pg.QtCore.Qt.DashLine))
            finite = np.flatnonzero(np.isfinite(x) & np.isfinite(y))
            scatter = pg.ScatterPlotItem(
                x=x[finite], y=y[finite], data=finite, pxMode=True,
                brush=[brushes[k] for k in finite], pen=[pens[k] for k in finite], size=sizes[finite],
            )
            scatter.sigClicked.connect(self._qt_on_points_clicked)
            plot.addItem(scatter)

    def _qt_on_points_clicked(self, scatter, points, *args):
        if len(points) > 0:
            self.select_pair(int(points[0].data()))

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn

        from .utils_panel import make_toggled_checkboxes

        self.metrics_toggle, self.metrics_select, metrics_box = make_toggled_checkboxes(
            "metrics",
            options=list(self.visible_metrics_dict.keys()),
            value=self.get_visible_metrics(),
            on_change=self._panel_on_metrics_changed,
        )

        self._color_options = self.get_color_options()
        self.color_select = pn.widgets.Select(name="color by", options=list(self._color_options.keys()), value='none')
        self.color_select.param.watch(lambda event: self.refresh(), 'value')
        self.legend_pane = pn.pane.HTML("")

        self.layout = pn.Column(
            pn.Row(self.metrics_toggle, self.color_select, self.legend_pane, sizing_mode="stretch_width"),
            metrics_box,
            pn.Column(sizing_mode="stretch_both"),
            sizing_mode="stretch_both",
        )

    def _panel_on_metrics_changed(self, event):
        for m in self.visible_metrics_dict.keys():
            self.visible_metrics_dict[m] = m in event.new
        self.refresh()

    def _panel_on_settings_changed(self):
        self.refresh()

    def _panel_on_unit_visibility_changed(self):
        self.refresh()

    def _panel_refresh(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.layouts import gridplot
        from bokeh.models import ColumnDataSource
        from .utils_panel import _bg_color

        pairs = self.get_pairs()
        colors, legend = self.get_pair_colors(pairs, self._color_options.get(self.color_select.value))
        self.legend_pane.object = self.get_legend_html(legend)
        visible_mask = self.get_visible_mask(pairs)

        figures = []
        for metric in self.get_visible_metrics():
            fig = bpl.figure(
                title=metric,
                tools="pan,wheel_zoom,reset,tap",
                background_fill_color=_bg_color,
                border_fill_color=_bg_color,
                outline_line_color="white",
                x_axis_label=self.get_axis_label(1),
                y_axis_label=self.get_axis_label(2),
            )
            fig.toolbar.logo = None
            fig.grid.visible = False
            x, y = self.get_metric_values(metric, pairs)
            line = self.get_equality_line(x, y)
            if line is not None:
                fig.line(line, line, line_dash="dashed", color="#888888")
            finite = np.flatnonzero(np.isfinite(x) & np.isfinite(y))
            source = ColumnDataSource({
                "x": x[finite], "y": y[finite], "pair_index": finite,
                "color": [colors[k] for k in finite],
                "line_color": ["#FFFFFF" if visible_mask[k] else None for k in finite],
                "size": np.where(visible_mask[finite], 12, 7),
            })
            fig.scatter("x", "y", source=source, color="color", line_color="line_color", line_width=2, size="size")
            source.selected.on_change('indices', self._panel_make_tap_callback(source))
            figures.append(fig)

        if len(figures) == 0:
            self.layout[2] = pn.Column(sizing_mode="stretch_both")
            return
        grid = gridplot(figures, ncols=max(self.settings['num_columns'], 1), sizing_mode="stretch_both", toolbar_location="right")
        self.layout[2] = pn.Column(grid, sizing_mode="stretch_both", styles={'background-color': f'{_bg_color}'})

    def _panel_make_tap_callback(self, source):
        def callback(attr, old, new):
            if len(new) > 0:
                self.select_pair(int(source.data["pair_index"][new[0]]))
        return callback


CompareMetricsView._gui_help_txt = """
## Compare Metrics View

Scatter plots of unit metrics for the matched pairs: the value of the unit of sorter 1 on the
horizontal axis, the value of the unit of sorter 2 on the vertical axis. The dashed line marks
equality.

The pairs are the ones matched at the agreement threshold shared with the unit Venn view (set it
with the slider of the unit Venn view). The visible pair is drawn bigger, with a white outline.

### Controls
- **metrics** : the metrics to plot, one scatter plot per metric.
- **color by** : color the points by a categorical property (e.g. a quality label) of the
  unit of sorter 1 or of sorter 2.
- **left click on a point** : make that pair of units visible.

### Settings
- **log_scale** : plot log10(value + .001), useful for firing rates and ISI violations.
- **num_columns** : the number of plots per row.
- **max_categories** : properties with more distinct values than this are not listed in "color by".
"""
