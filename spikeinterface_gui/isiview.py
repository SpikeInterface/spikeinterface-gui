from .view_base import ViewBase


class ISIView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _settings = [
                {'name': 'window_ms', 'type': 'float', 'value' : 50. },
                {'name': 'bin_ms', 'type': 'float', 'value' : 1.0 },
        ]
    _depend_on = ["isi_histograms"]
    _need_compute = True


    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        self.isi_histograms, self.isi_bins = self.controller.get_isi_histograms()        

    def compute(self):
        self.isi_histograms, self.isi_bins = self.controller.compute_isi_histograms(
                self.settings['window_ms'],  self.settings['bin_ms'])
        self.refresh()

    def _on_settings_changed(self):
        self.isi_histograms, self.isi_bins = None, None
        self.refresh()

    ## QT ##

    def _qt_make_layout(self):
        import pyqtgraph as pg
        from .myqt import QT
        from .utils_qt import ViewBoxHandlingDoubleClick

        self.layout = QT.QVBoxLayout()
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.viewBox = ViewBoxHandlingDoubleClick()
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()

    def _qt_refresh(self):
        import pyqtgraph as pg
        
        self.plot.clear()
        if self.isi_histograms is None:
            return
        
        n = 0
        for unit_index, unit_id in self.controller.iter_visible_units():

            isi = self.isi_histograms[unit_index, :]
            
            qcolor = self.get_unit_color(unit_id)
            curve = pg.PlotCurveItem(self.isi_bins[:-1], isi, pen=pg.mkPen(qcolor, width=3))
            self.plot.addItem(curve)

    ## Panel ##

    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import Range1d
        from .utils_panel import _bg_color

        # Create Bokeh figure
        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="pan,box_zoom,wheel_zoom,reset",
            x_axis_label="Time (ms)",
            y_axis_label="Count",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.figure.toolbar.logo = None
        # Update plot ranges
        self.figure.x_range = Range1d(0, self.settings['window_ms'])
        self.figure.y_range = Range1d(0, 100)

        self.layout = pn.Column(
                self.figure,
                styles={"flex": "1"},
                sizing_mode="stretch_both"
            )

    def _panel_refresh(self):
        from bokeh.models import ColumnDataSource

        # this clear the figure
        self.figure.renderers = []
        self.lines = {}

        y_max = 0
        for unit_index, unit_id in self.controller.iter_visible_units():
            isi = self.isi_histograms[unit_index, :]
            source = ColumnDataSource({"x": self.isi_bins[:-1].tolist(), "y": isi.tolist()})
            color = self.get_unit_color(unit_id)
            self.lines[unit_id] = self.figure.line(
                "x",
                "y",
                source=source,
                line_color=color,
                line_width=2,
                visible=True,
            )
            y_max = max(y_max, isi.max())
        self.figure.y_range.end = y_max * 1.1

ISIView._gui_help_txt = """
## ISI View

This view shows the inter spike interval histograms for each unit.
"""