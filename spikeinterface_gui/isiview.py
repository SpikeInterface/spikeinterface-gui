# from .myqt import QT
# import pyqtgraph as pg

# import numpy as np
# import pandas as pd

# from .base import WidgetBase

from .view_base import ViewBase




# class MyViewBox(pg.ViewBox):
#     doubleclicked = QT.pyqtSignal()
#     def mouseDoubleClickEvent(self, ev):
#         self.doubleclicked.emit()
#         ev.accept()
#     def raiseContextMenu(self, ev):
#         #for some reasons enableMenu=False is not taken (bug ????)
#         pass



class ISIView(ViewBase):
    _supported_backend = ['qt']
    _settings = [
                {'name': 'window_ms', 'type': 'float', 'value' : 50. },
                {'name': 'bin_ms', 'type': 'float', 'value' : 1.0 },
        ]
    _need_compute = True


    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    # def __init__(self, controller=None, parent=None):
    #     WidgetBase.__init__(self, parent=parent, controller=controller)


    def _make_layout_qt(self):
        import pyqtgraph as pg
        from .myqt import QT
        from .utils_qt import ViewBoxHandlingDoubleClick
        


        self.layout = QT.QVBoxLayout()
        # self.setLayout(self.layout)
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.isi_histograms, self.isi_bins = self.controller.get_isi_histograms()

        self.viewBox = ViewBoxHandlingDoubleClick()
        # self.viewBox.doubleclicked.connect(self.open_settings)
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()


    def compute(self):
        self.isi_histograms, self.isi_bins = self.controller.compute_isi_histograms(
                self.settings['window_ms'],  self.settings['bin_ms'])
        self.refresh()

    def on_params_changed(self):
        self.isi_histograms, self.isi_bins = None, None
        self.refresh()

    def _refresh_qt(self):
        import pyqtgraph as pg
        
        self.plot.clear()
        if self.isi_histograms is None:
            return
        
        n = 0
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                continue

            isi = self.isi_histograms[unit_index, :]
            
            qcolor = self.get_unit_color(unit_id)
            curve = pg.PlotCurveItem(self.isi_bins[:-1], isi, pen=pg.mkPen(qcolor, width=3))
            self.plot.addItem(curve)

ISIView._gui_help_txt = """Inter spike intervals
Show only selected units.
Settings control the bin size in ms.
Right mouse : zoom"""

