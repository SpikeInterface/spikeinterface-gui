import numpy as np

from .view_base import ViewBase


def solve_venn_geometry(num_only1, num_matched, num_only2):
    """
    Two circle Venn geometry with areas proportional to the unit counts.

    Returns (radius1, radius2, center_x1, center_x2). The disc areas are `num1` and `num2`
    and the area of the lens is `num_matched`, so the picture is quantitatively honest.
    The two circles are centered on y=0 and symmetric around x=0.
    """
    num1 = num_only1 + num_matched
    num2 = num_matched + num_only2

    if num1 == 0 and num2 == 0:
        return 0., 0., 0., 0.

    # disc area == unit count
    radius1 = np.sqrt(num1 / np.pi)
    radius2 = np.sqrt(num2 / np.pi)

    if num1 == 0 or num2 == 0:
        # one of the two is empty, put the other one in the middle
        distance = radius1 + radius2
    elif num_matched == 0:
        # disjoint, just touching
        distance = radius1 + radius2
    elif num_matched >= min(num1, num2):
        # fully nested
        distance = abs(radius1 - radius2)
    else:
        distance = _solve_center_distance(radius1, radius2, num_matched)

    return radius1, radius2, -distance / 2., distance / 2.


def _lens_area(distance, radius1, radius2):
    """Area of the intersection of two discs whose centers are `distance` apart"""
    if distance >= radius1 + radius2:
        return 0.
    if distance <= abs(radius1 - radius2):
        return np.pi * min(radius1, radius2) ** 2
    d, r1, r2 = distance, radius1, radius2
    part1 = r1 ** 2 * np.arccos((d ** 2 + r1 ** 2 - r2 ** 2) / (2 * d * r1))
    part2 = r2 ** 2 * np.arccos((d ** 2 + r2 ** 2 - r1 ** 2) / (2 * d * r2))
    part3 = 0.5 * np.sqrt(max((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2), 0.))
    return part1 + part2 - part3


def _solve_center_distance(radius1, radius2, target_area):
    """Center distance giving an intersection of `target_area`. The lens area decreases with d."""
    from scipy.optimize import brentq

    low = abs(radius1 - radius2)
    high = radius1 + radius2
    return brentq(lambda d: _lens_area(d, radius1, radius2) - target_area, low, high)


class VennView(ViewBase):
    """
    Venn diagram of the two compared sortings: units matched by both, and units found
    by only one of the two. The agreement threshold is set with a slider and is shared
    with the other comparison views.
    """
    id = "venn"
    _supported_backend = ['qt', 'panel']
    _depend_on = ['comparison']
    _settings = [
        {'name': 'num_units_to_select', 'type': 'int', 'value': 1, 'step': 1},
    ]

    _color1 = "#1f77b4"
    _color2 = "#ff7f0e"

    def get_venn_data(self):
        """Returns (venn_dict, geometry) where geometry is (r1, r2, cx1, cx2)"""
        venn = self.controller.get_venn_unit_ids()
        geometry = solve_venn_geometry(len(venn['only1']), len(venn['matched']), len(venn['only2']))
        return venn, geometry

    def select_units_on_click(self, x, y, reset=True):
        """
        Make visible a random sample of the clicked region.

        A region can hold hundreds of units, and what one wants is to inspect a few of
        them, so `num_units_to_select` of them are drawn at random. Clicking the same
        region again draws another sample.
        """
        venn, (radius1, radius2, center_x1, center_x2) = self.get_venn_data()

        inside1 = (x - center_x1) ** 2 + y ** 2 <= radius1 ** 2
        inside2 = (x - center_x2) ** 2 + y ** 2 <= radius2 ** 2

        if inside1 and inside2:
            # in the intersection an entry is a pair, and both of its units are selected
            candidates = venn['matched']
        elif inside1:
            candidates = venn['only1']
        elif inside2:
            candidates = venn['only2']
        else:
            return

        if len(candidates) == 0:
            return

        num_to_select = max(int(self.settings['num_units_to_select']), 1)
        num_to_select = min(num_to_select, len(candidates))
        rng = np.random.default_rng()
        selected = rng.choice(len(candidates), size=num_to_select, replace=False)

        unit_ids = []
        for index in selected:
            candidate = candidates[index]
            if isinstance(candidate, tuple):
                # a matched pair, keep both units so that they can be compared
                unit_ids.extend(candidate)
            else:
                unit_ids.append(candidate)

        if not reset:
            unit_ids = list(self.controller.get_visible_unit_ids()) + unit_ids
        # set_visible_unit_ids still truncates to main_settings['max_visible_units']
        self.controller.set_visible_unit_ids(unit_ids)
        self.notify_unit_and_channel_visibility_changed()
        self.refresh()

    def set_agreement_threshold(self, threshold):
        self.controller.set_agreement_threshold(threshold)
        self.notify_agreement_threshold_changed()
        self.refresh()

    def get_venn_labels(self, venn, geometry):
        """
        The texts to draw, as a list of (x, y, text, color).

        Each count sits in the middle of its own region along y=0, and each analyzer name
        on the outer side of its own circle, in its own color so that the two never
        overlap when the circles are close together.
        """
        radius1, radius2, center_x1, center_x2 = geometry
        num_only1 = len(venn['only1'])
        num_matched = len(venn['matched'])
        num_only2 = len(venn['only2'])

        left1, right1 = center_x1 - radius1, center_x1 + radius1
        left2, right2 = center_x2 - radius2, center_x2 + radius2
        labels = []

        if num_only1 > 0:
            # the only1 region runs from the left of circle1 to the left of circle2,
            # or spans the whole of circle1 when the two are disjoint
            only1_right = min(right1, max(left2, left1))
            labels.append(((left1 + only1_right) / 2., 0., f'{num_only1}', '#FFFFFF'))
        if num_only2 > 0:
            only2_left = max(left2, min(right1, right2))
            labels.append(((only2_left + right2) / 2., 0., f'{num_only2}', '#FFFFFF'))
        if num_matched > 0 and radius1 + radius2 > abs(center_x2 - center_x1):
            # middle of the lens along x
            labels.append(((right1 + left2) / 2., 0., f'{num_matched}', '#FFFFFF'))

        top = max(radius1, radius2)
        labels.append((left1 + radius1 * 0.45, top * 1.15, f'{self.controller.analyzer1_name}', self._color1))
        labels.append((right2 - radius2 * 0.45, top * 1.15, f'{self.controller.analyzer2_name}', self._color2))

        return labels

    def get_circle_polygon(self, radius, center_x, num_points=100):
        """A closed circle as (xs, ys), for the backends that draw polygons"""
        theta = np.linspace(0, 2 * np.pi, num_points)
        return center_x + radius * np.cos(theta), radius * np.sin(theta)

    def get_view_ranges(self, geometry):
        radius1, radius2, center_x1, center_x2 = geometry
        top = max(radius1, radius2)
        margin = 0.2 * top
        x_range = (center_x1 - radius1 - margin, center_x2 + radius2 + margin)
        y_range = (-top - margin, top * 1.3 + margin)
        return x_range, y_range

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingClickToPositionWithCtrl

        self.layout = QT.QVBoxLayout()

        # threshold slider, the controller holds the value
        header = QT.QHBoxLayout()
        header.addWidget(QT.QLabel('agreement threshold'))
        self.slider = QT.QSlider(QT.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(int(round(self.controller.agreement_threshold * 100)))
        self.slider.valueChanged.connect(self._qt_on_slider_changed)
        header.addWidget(self.slider)
        self.threshold_label = QT.QLabel(f'{self.controller.agreement_threshold:.2f}')
        header.addWidget(self.threshold_label)
        self.layout.addLayout(header)

        # dragging the slider emits one signal per step: debounce the re-matching so that
        # a drag does not re-run the matching and rebuild the unit table on every step
        self._commit_timer = QT.QTimer(self.qt_widget)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.setInterval(150)
        self._commit_timer.timeout.connect(self._qt_commit_threshold)

        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)

        self.viewBox = ViewBoxHandlingClickToPositionWithCtrl()
        self.viewBox.clicked.connect(self._qt_select_units)
        self.viewBox.disableAutoRange()
        self.viewBox.setAspectLocked(True)

        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')

        self._items = []

    def _qt_on_slider_changed(self, value):
        # the label follows the slider immediately, the rest is debounced
        self.threshold_label.setText(f'{value / 100.:.2f}')
        self._commit_timer.start()

    def _qt_commit_threshold(self):
        self.set_agreement_threshold(self.slider.value() / 100.)

    def _qt_select_units(self, x, y, reset):
        self.select_units_on_click(x, y, reset=reset)

    def _qt_refresh(self):
        from .myqt import QT
        import pyqtgraph as pg

        # keep the slider in sync when the threshold is changed elsewhere, but never
        # while an edit of our own is still pending, otherwise a refresh triggered by
        # another view would snap the handle back under the user's cursor
        slider_value = int(round(self.controller.agreement_threshold * 100))
        if self.slider.value() != slider_value and not self._commit_timer.isActive():
            self.slider.blockSignals(True)
            self.slider.setValue(slider_value)
            self.slider.blockSignals(False)
        # the label always shows what the handle shows
        self.threshold_label.setText(f'{self.slider.value() / 100.:.2f}')

        for item in self._items:
            self.plot.removeItem(item)
        self._items = []

        venn, geometry = self.get_venn_data()
        radius1, radius2, center_x1, center_x2 = geometry

        if radius1 == 0. and radius2 == 0.:
            return

        for radius, center_x, color in (
            (radius1, center_x1, self._color1),
            (radius2, center_x2, self._color2),
        ):
            if radius == 0.:
                continue
            circle = QT.QGraphicsEllipseItem(center_x - radius, -radius, 2 * radius, 2 * radius)
            circle.setPen(pg.mkPen(color, width=2))
            # semi transparent so that the intersection reads as a third region
            brush_color = QT.QColor(color)
            brush_color.setAlpha(110)
            circle.setBrush(pg.mkBrush(brush_color))
            self.plot.addItem(circle)
            self._items.append(circle)

        for x, y, text, color in self.get_venn_labels(venn, geometry):
            item = pg.TextItem(text=text, color=color, anchor=(0.5, 0.5), border=None)
            item.setPos(x, y)
            self.plot.addItem(item)
            self._items.append(item)

        x_range, y_range = self.get_view_ranges(geometry)
        self.plot.setXRange(*x_range)
        self.plot.setYRange(*y_range)

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource
        from bokeh.events import Tap
        from .utils_panel import _bg_color

        # value_throttled only fires at the end of a drag, which is the debounce that
        # the Qt side has to do with a timer
        self.threshold_slider = pn.widgets.FloatSlider(
            name='agreement threshold',
            start=0., end=1., step=0.01,
            value=float(self.controller.agreement_threshold),
            sizing_mode="stretch_width",
        )
        self.threshold_slider.param.watch(self._panel_on_slider_changed, 'value_throttled')

        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset,wheel_zoom,tap",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            match_aspect=True,
            outline_line_color="white",
            styles={"flex": "1"},
        )
        self.figure.toolbar.logo = None
        self.figure.axis.visible = False
        self.figure.grid.visible = False

        # one entry per circle, updated in place on refresh
        self.circle_source = ColumnDataSource({"xs": [], "ys": [], "color": []})
        self.figure.patches(
            xs="xs", ys="ys", source=self.circle_source,
            fill_color="color", line_color="color", fill_alpha=0.43, line_width=2,
        )

        self.text_source = ColumnDataSource({"x": [], "y": [], "text": [], "color": []})
        self.figure.text(
            x="x", y="y", text="text", text_color="color", source=self.text_source,
            text_align="center", text_baseline="middle",
        )

        self.figure.on_event(Tap, self._panel_on_tap)

        self.layout = pn.Column(
            self.threshold_slider,
            self.figure,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

    def _panel_on_slider_changed(self, event):
        self.set_agreement_threshold(event.new)

    def _panel_on_tap(self, event):
        if event.x is None or event.y is None:
            return
        self.select_units_on_click(event.x, event.y, reset=True)

    def _panel_refresh(self):
        # keep the slider in sync when the threshold is changed elsewhere
        threshold = float(self.controller.agreement_threshold)
        if self.threshold_slider.value != threshold:
            self.threshold_slider.value = threshold

        venn, geometry = self.get_venn_data()
        radius1, radius2, center_x1, center_x2 = geometry

        if radius1 == 0. and radius2 == 0.:
            self.circle_source.data.update({"xs": [], "ys": [], "color": []})
            self.text_source.data.update({"x": [], "y": [], "text": [], "color": []})
            return

        all_xs, all_ys, colors = [], [], []
        for radius, center_x, color in (
            (radius1, center_x1, self._color1),
            (radius2, center_x2, self._color2),
        ):
            if radius == 0.:
                continue
            xs, ys = self.get_circle_polygon(radius, center_x)
            all_xs.append(xs.tolist())
            all_ys.append(ys.tolist())
            colors.append(color)
        self.circle_source.data.update({"xs": all_xs, "ys": all_ys, "color": colors})

        labels = self.get_venn_labels(venn, geometry)
        self.text_source.data.update({
            "x": [label[0] for label in labels],
            "y": [label[1] for label in labels],
            "text": [label[2] for label in labels],
            "color": [label[3] for label in labels],
        })

        x_range, y_range = self.get_view_ranges(geometry)
        self.figure.x_range.start, self.figure.x_range.end = x_range
        self.figure.y_range.start, self.figure.y_range.end = y_range


VennView._gui_help_txt = """
## Venn View

Venn diagram of the two compared sorting outputs. The area of each disc is proportional to
the number of units of that sorter, and the area of the intersection is proportional to the
number of units matched between the two, so the picture is quantitatively honest.

The matching is one to one (hungarian) at the agreement threshold set with the slider.
That threshold is shared with the other comparison views: moving it also re-orders the
agreement matrix and re-categorizes the rows of the comparison unit table.

### Settings
- **num_units_to_select** : how many units of a region a click makes visible. In the
  intersection this is a number of pairs, and both units of each pair are selected.

### Controls
- **slider** : the agreement threshold above which two units are considered matched.
- **left click on a region** : make a random sample of that region visible. Clicking again
  draws another sample, which is a quick way to walk through a region.
- **ctrl + left click on a region** : add the sample to the units already visible.

Note that `max_visible_units` (see the main settings) still caps how many units can be
visible at once.
"""
