import numpy as np
import matplotlib.cm
import matplotlib.colors

from .view_base import ViewBase


class AgreementMatrixView(ViewBase):
    """
    Agreement matrix between the units of the two compared analyzers.

    Rows (x axis) are the units of analyzer1, columns (y axis) the units of analyzer2.
    Clicking a cell makes the corresponding pair of units visible.
    """
    id = "agreementmatrix"
    _supported_backend = ['qt', 'panel']
    _depend_on = ['comparison']
    _settings = [
        {'name': 'colormap', 'type': 'list', 'limits': ['viridis', 'jet', 'gray', 'hot']},
        {'name': 'ordered', 'type': 'bool', 'value': True},
        {'name': 'show_all', 'type': 'bool', 'value': True},
        {'name': 'max_labels', 'type': 'int', 'value': 30},
    ]

    def get_agreement_data(self):
        """
        Sub-matrix to display.

        Returns (values, row_unit_ids, col_unit_ids) where the unit ids are the *combined*
        ids in the row/column order of the displayed matrix, or (None, None, None) when
        there is nothing to show.
        """
        controller = self.controller
        scores = controller.get_agreement_scores(ordered=self.settings['ordered'])

        row_unit_ids = np.array([controller.get_combined_unit_id(1, u) for u in scores.index])
        col_unit_ids = np.array([controller.get_combined_unit_id(2, u) for u in scores.columns])
        # pandas hands out a read-only view, but both pyqtgraph and bokeh may write into
        # the array they are given, so pass them a writable copy
        values = np.array(scores.values, dtype='float64')

        if not self.settings['show_all']:
            visible_unit_ids = set(controller.get_visible_unit_ids())
            row_mask = np.array([u in visible_unit_ids for u in row_unit_ids], dtype='bool')
            col_mask = np.array([u in visible_unit_ids for u in col_unit_ids], dtype='bool')
            if not np.any(row_mask) or not np.any(col_mask):
                return None, None, None
            values = values[row_mask, :][:, col_mask]
            row_unit_ids = row_unit_ids[row_mask]
            col_unit_ids = col_unit_ids[col_mask]

        if values.size == 0:
            return None, None, None

        return values, row_unit_ids, col_unit_ids

    def select_unit_pair_on_click(self, x, y, reset=True):
        values, row_unit_ids, col_unit_ids = self.get_agreement_data()
        if values is None:
            return

        num_rows, num_cols = values.shape
        if not ((0 <= x <= num_rows) and (0 <= y <= num_cols)):
            return
        # clip so that a click exactly on the far edge still selects the last unit
        row = min(int(np.floor(x)), num_rows - 1)
        col = min(int(np.floor(y)), num_cols - 1)

        if reset:
            self.controller.set_all_unit_visibility_off()
        self.controller.set_unit_visibility(row_unit_ids[row], True)
        self.controller.set_unit_visibility(col_unit_ids[col], True)
        self.notify_unit_and_channel_visibility_changed()
        self.refresh()

    def get_colormap(self, num_colors=512):
        return matplotlib.colormaps[self.settings['colormap']].resampled(num_colors)

    def get_axis_ticks(self, row_unit_ids, col_unit_ids):
        """
        Tick positions and labels for both axes, or (None, None) when the matrix is too
        big for the labels to be readable.

        The ticks are the unit ids in each analyzer's own namespace: the combined ids
        would be far too long here, the axis label says which analyzer it is.
        """
        max_labels = self.settings['max_labels']
        if max_labels <= 0 or max(len(row_unit_ids), len(col_unit_ids)) > max_labels:
            return None, None

        bottom_ticks = [
            (i + 0.5, f'{self.controller.get_original_unit_id(unit_id)}')
            for i, unit_id in enumerate(row_unit_ids)
        ]
        left_ticks = [
            (i + 0.5, f'{self.controller.get_original_unit_id(unit_id)}')
            for i, unit_id in enumerate(col_unit_ids)
        ]
        return bottom_ticks, left_ticks

    def _qt_on_settings_changed(self):
        N = 512
        cmap = self.get_colormap(N)
        lut = []
        for i in range(N):
            r, g, b, _ = matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r * 255, g * 255, b * 255])
        self.lut = np.array(lut, dtype='uint8')

        self.refresh()

    def _panel_on_settings_changed(self):
        N = 512
        cmap = self.get_colormap(N)
        self.color_mapper.palette = [matplotlib.colors.rgb2hex(cmap(i)[:3]) for i in range(N)]

        self.refresh()

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingClickToPositionWithCtrl

        self.layout = QT.QVBoxLayout()
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)

        self.viewBox = ViewBoxHandlingClickToPositionWithCtrl()
        self.viewBox.clicked.connect(self._qt_select_pair)
        self.viewBox.disableAutoRange()

        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()

        self.image = pg.ImageItem()
        self.plot.addItem(self.image)

        # real axes: the tick labels are the unit ids of that analyzer, and the axis
        # label says which analyzer it is. The combined ids would be far too long here.
        self.plot.showAxis('bottom')
        self.plot.showAxis('left')
        self.plot.setLabel('bottom', f'{self.controller.analyzer1_name} units')
        self.plot.setLabel('left', f'{self.controller.analyzer2_name} units')

        # this builds the lut and refreshes
        self.on_settings_changed()

    def _qt_refresh(self):
        values, row_unit_ids, col_unit_ids = self.get_agreement_data()
        if values is None:
            self.image.hide()
            return

        # agreement scores are already normalized in [0, 1], no rescaling
        self.image.setImage(values, lut=self.lut, levels=[0., 1.])
        self.image.show()
        num_rows, num_cols = values.shape
        self.plot.setXRange(0, num_rows)
        self.plot.setYRange(0, num_cols)

        # one tick per unit, at the middle of its row/column. pyqtgraph drops the ones
        # that would overlap, so no manual placement is needed. None gives back the
        # automatic numeric ticks.
        bottom_ticks, left_ticks = self.get_axis_ticks(row_unit_ids, col_unit_ids)
        self.plot.getAxis('bottom').setTicks(None if bottom_ticks is None else [bottom_ticks])
        self.plot.getAxis('left').setTicks(None if left_ticks is None else [left_ticks])

    def _qt_select_pair(self, x, y, reset):
        self.select_unit_pair_on_click(x, y, reset=reset)

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, LinearColorMapper, FixedTicker
        from bokeh.events import Tap
        from .utils_panel import _bg_color

        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset,wheel_zoom,tap",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"},
        )
        self.figure.toolbar.logo = None
        self.figure.grid.visible = False
        self.figure.xaxis.axis_label = f'{self.controller.analyzer1_name} units'
        self.figure.yaxis.axis_label = f'{self.controller.analyzer2_name} units'

        N = 512
        cmap = self.get_colormap(N)
        # agreement scores are already normalized, the range is fixed
        self.color_mapper = LinearColorMapper(
            palette=[matplotlib.colors.rgb2hex(cmap(i)[:3]) for i in range(N)], low=0., high=1.
        )

        self.image_source = ColumnDataSource({"image": [np.zeros((1, 1))], "dw": [1], "dh": [1]})
        self.figure.image(
            image="image", x=0, y=0, dw="dw", dh="dh",
            color_mapper=self.color_mapper, source=self.image_source,
        )

        self.figure.on_event(Tap, self._panel_on_tap)

        self.layout = pn.Column(
            self.figure,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

    def _panel_refresh(self):
        from bokeh.models import FixedTicker

        values, row_unit_ids, col_unit_ids = self.get_agreement_data()
        if values is None:
            self.image_source.data.update({"image": [np.zeros((1, 1))], "dw": [0], "dh": [0]})
            return

        num_rows, num_cols = values.shape
        # bokeh reads image[y][x] while pyqtgraph reads image[x][y], so transpose to keep
        # analyzer1 on the x axis in both backends
        self.image_source.data.update({"image": [values.T], "dw": [num_rows], "dh": [num_cols]})

        bottom_ticks, left_ticks = self.get_axis_ticks(row_unit_ids, col_unit_ids)
        if bottom_ticks is None:
            self.figure.xaxis.ticker = FixedTicker(ticks=[])
            self.figure.yaxis.ticker = FixedTicker(ticks=[])
            self.figure.xaxis.major_label_overrides = {}
            self.figure.yaxis.major_label_overrides = {}
        else:
            self.figure.xaxis.ticker = FixedTicker(ticks=[pos for pos, _ in bottom_ticks])
            self.figure.xaxis.major_label_overrides = {pos: label for pos, label in bottom_ticks}
            self.figure.yaxis.ticker = FixedTicker(ticks=[pos for pos, _ in left_ticks])
            self.figure.yaxis.major_label_overrides = {pos: label for pos, label in left_ticks}

        self.figure.x_range.start = 0
        self.figure.x_range.end = num_rows
        self.figure.y_range.start = 0
        self.figure.y_range.end = num_cols

    def _panel_on_tap(self, event):
        if event.x is None or event.y is None:
            return
        self.select_unit_pair_on_click(event.x, event.y, reset=True)


AgreementMatrixView._gui_help_txt = """
## Agreement Matrix View

Agreement scores between the units of the two compared sorting outputs.

Rows (horizontal axis) are the units of the first analyzer, columns (vertical axis) the
units of the second one. The score is the number of matched spikes divided by the total
number of spikes of both units, so it is 1 for two identical spike trains and 0 when no
spike matches.

### Settings
- **ordered** : reorder rows and columns so that the best matches are on the diagonal.
- **show_all** : when off, only the currently visible units are displayed.
- **max_labels** : hide the unit id labels when the matrix is bigger than this.

### Controls
- **left click** : select the pair of units of this cell, and make only those visible.
- **ctrl + left click** : add the pair of units to the visible ones.
"""
