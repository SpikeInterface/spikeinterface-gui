import numpy as np
import matplotlib.colors
import matplotlib.pyplot as plt

from .view_base import ViewBase


def get_categorical_properties(controller, max_categories):
    """The non numeric columns of the units table that are set for both analyzers"""
    table = controller.units_table
    properties = []
    for name in controller.get_shared_unit_properties():
        if name == "sorter":
            continue
        column = table[name]
        if column.dtype.kind in 'if':
            continue
        # too many values (e.g. main_channel_id) do not make a readable chart
        if column.nunique() > max_categories:
            continue
        properties.append(name)
    return properties


def get_category_colors(categories, cmap="tab10"):
    """One hex color per category, in the order given"""
    cmap = plt.get_cmap(cmap)
    return [matplotlib.colors.rgb2hex(cmap(i % cmap.N)) for i in range(len(categories))]


class CompareLabelsView(ViewBase):
    """
    Donut charts of a categorical unit property (e.g. a quality label), one per compared
    analyzer, so that the label proportions of the two sorters can be compared.
    """
    id = "comparelabels"
    _supported_backend = ['qt', 'panel']
    _depend_on = ['comparison']
    _settings = [
        {'name': 'max_categories', 'type': 'int', 'value': 20},
    ]
    # donut geometry, in data units
    _outer_radius = 1.
    _inner_radius = 0.7
    _spacing = 2.7
    # one donut per analyzer, stacked vertically
    _centers = ((0., 0.), (0., -_spacing))

    def get_categorical_properties(self):
        return get_categorical_properties(self.controller, self.settings['max_categories'])

    def get_donut_data(self, property_name):
        """
        Returns (categories, colors, counts) where counts has one row per analyzer.
        Units with no value are counted as "n/a".
        """
        column = self.controller.units_table[property_name].astype(object).where(
            self.controller.units_table[property_name].notna(), "n/a"
        ).astype(str)
        categories = sorted(column.unique())
        colors = get_category_colors(categories, cmap=self.controller.main_settings['label_colormap'])
        counts = np.array([
            [np.sum(column.loc[unit_ids] == category) for category in categories]
            for unit_ids in (self.controller.unit_ids1, self.controller.unit_ids2)
        ])
        return categories, colors, counts

    def get_wedge_polygons(self, counts, center, num_points=100):
        """One annular sector per category as (xs, ys), clockwise from 12 o'clock"""
        polygons = []
        fractions = np.cumsum(np.concatenate([[0.], counts / max(counts.sum(), 1)]))
        for start, stop in zip(fractions[:-1], fractions[1:]):
            if stop == start:
                polygons.append(None)
                continue
            theta = np.pi / 2 - 2 * np.pi * np.linspace(start, stop, num_points)
            xs = np.concatenate([self._outer_radius * np.cos(theta), self._inner_radius * np.cos(theta[::-1])])
            ys = np.concatenate([self._outer_radius * np.sin(theta), self._inner_radius * np.sin(theta[::-1])])
            polygons.append((center[0] + xs, center[1] + ys))
        return polygons

    def get_donut_patches(self, colors, counts):
        """All the wedges as (xs, ys, color), the 2 donuts stacked vertically"""
        patches = []
        for analyzer_row, center in zip(counts, self._centers):
            for polygon, color in zip(self.get_wedge_polygons(analyzer_row, center), colors):
                if polygon is not None:
                    patches.append((polygon[0], polygon[1], color))
        return patches

    def get_donut_labels(self, categories, colors, counts):
        """The texts to draw, as a list of (x, y, text, color, size)"""
        labels = []
        mid_radius = (self._outer_radius + self._inner_radius) / 2
        for analyzer_index, (analyzer_row, (center_x, center_y)) in enumerate(zip(counts, self._centers)):
            total = analyzer_row.sum()
            name = self.controller.get_analyzer_name(analyzer_index + 1)
            labels.append((center_x, center_y + self._outer_radius * 1.15, name, '#FFFFFF', 12))
            labels.append((center_x, center_y, f'{total:,}\nunits', '#FFFFFF', 14))
            fractions = np.cumsum(np.concatenate([[0.], analyzer_row / max(total, 1)]))
            for start, stop in zip(fractions[:-1], fractions[1:]):
                if stop == start:
                    continue
                theta = np.pi / 2 - np.pi * (start + stop)
                labels.append((
                    center_x + mid_radius * np.cos(theta), center_y + mid_radius * np.sin(theta),
                    f'{100 * (stop - start):.1f}%', '#FFFFFF', 9,
                ))
        # legend, one line per category on the left of the top donut
        for i, (category, color) in enumerate(zip(categories, colors)):
            labels.append((-1.7, self._outer_radius - 0.2 * i, f'■ {category}', color, 10))
        return labels

    def get_view_ranges(self):
        return (-2.3, 1.2), (-self._spacing - 1.2, 1.4)

    def get_draw_data(self, property_name):
        if property_name is None:
            return [], []
        categories, colors, counts = self.get_donut_data(property_name)
        return self.get_donut_patches(colors, counts), self.get_donut_labels(categories, colors, counts)

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        header = QT.QHBoxLayout()
        header.addWidget(QT.QLabel('property'))
        self.property_combo = QT.QComboBox()
        self.property_combo.addItems(self.get_categorical_properties())
        self.property_combo.currentTextChanged.connect(self.refresh)
        header.addWidget(self.property_combo)
        header.addStretch()
        self.layout.addLayout(header)

        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        self.viewBox = pg.ViewBox()
        self.viewBox.disableAutoRange()
        self.viewBox.setAspectLocked(True)
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        self._items = []

    def _qt_on_settings_changed(self):
        current = self.property_combo.currentText()
        self.property_combo.blockSignals(True)
        self.property_combo.clear()
        self.property_combo.addItems(self.get_categorical_properties())
        self.property_combo.setCurrentText(current)
        self.property_combo.blockSignals(False)
        self.refresh()

    def _qt_refresh(self):
        from .myqt import QT
        import pyqtgraph as pg

        for item in self._items:
            self.plot.removeItem(item)
        self._items = []

        patches, labels = self.get_draw_data(self.property_combo.currentText() or None)
        for xs, ys, color in patches:
            polygon = QT.QPolygonF([QT.QPointF(x, y) for x, y in zip(xs, ys)])
            item = QT.QGraphicsPolygonItem(polygon)
            item.setPen(pg.mkPen(None))
            item.setBrush(pg.mkBrush(color))
            self.plot.addItem(item)
            self._items.append(item)
        for x, y, text, color, size in labels:
            item = pg.TextItem(text=text, color=color, anchor=(0.5, 0.5))
            item.setFont(QT.QFont('', size))
            item.setPos(x, y)
            self.plot.addItem(item)
            self._items.append(item)

        x_range, y_range = self.get_view_ranges()
        # one call: with the aspect locked, separate x/y calls override each other and crop
        self.viewBox.setRange(xRange=x_range, yRange=y_range, padding=0)

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource
        from .utils_panel import _bg_color

        properties = self.get_categorical_properties()
        self.property_select = pn.widgets.Select(
            name='property', options=properties, value=properties[0] if properties else None,
            sizing_mode="stretch_width",
        )
        self.property_select.param.watch(lambda event: self.refresh(), 'value')

        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset,wheel_zoom",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            match_aspect=True,
            outline_line_color="white",
            styles={"flex": "1"},
        )
        self.figure.toolbar.logo = None
        self.figure.axis.visible = False
        self.figure.grid.visible = False
        # match_aspect only works with auto ranges: an invisible glyph on the view corners
        # makes the auto range include the labels, setting range start/end would distort
        self.bounds_source = ColumnDataSource({"x": [], "y": []})
        self.figure.scatter(x="x", y="y", source=self.bounds_source, alpha=0)

        self.patch_source = ColumnDataSource({"xs": [], "ys": [], "color": []})
        self.figure.patches(xs="xs", ys="ys", source=self.patch_source, fill_color="color", line_color=None)
        self.text_source = ColumnDataSource({"x": [], "y": [], "text": [], "color": [], "size": []})
        self.figure.text(
            x="x", y="y", text="text", text_color="color", text_font_size="size", source=self.text_source,
            text_align="center", text_baseline="middle",
        )

        self.layout = pn.Column(
            self.property_select,
            self.figure,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

    def _panel_on_settings_changed(self):
        properties = self.get_categorical_properties()
        self.property_select.options = properties
        if self.property_select.value not in properties:
            self.property_select.value = properties[0] if properties else None
        self.refresh()

    def _panel_refresh(self):
        patches, labels = self.get_draw_data(self.property_select.value)
        self.patch_source.data.update({
            "xs": [p[0].tolist() for p in patches],
            "ys": [p[1].tolist() for p in patches],
            "color": [p[2] for p in patches],
        })
        self.text_source.data.update({
            "x": [label[0] for label in labels],
            "y": [label[1] for label in labels],
            "text": [label[2] for label in labels],
            "color": [label[3] for label in labels],
            "size": [f'{label[4]}pt' for label in labels],
        })
        x_range, y_range = self.get_view_ranges()
        self.bounds_source.data.update({"x": list(x_range), "y": list(y_range)})


CompareLabelsView._gui_help_txt = """
## Compare Labels View

Proportions of a categorical unit property (e.g. a quality label: SUA / MUA / noise) for the
two compared sorting outputs, as one donut chart per sorter. The total number of units is in
the middle of each donut.

Only the non numeric properties that are set for both analyzers are listed. Units with no
value are counted as "n/a".

### Controls
- **property** : the categorical property to display.

### Settings
- **max_categories** : properties with more distinct values than this are not listed.
"""
