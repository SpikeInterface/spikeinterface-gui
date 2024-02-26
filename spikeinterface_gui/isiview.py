from .myqt import QT
import pyqtgraph as pg

import numpy as np
import pandas as pd

from .base import WidgetBase



class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass



class ISIView(WidgetBase):
    _params = [
                {'name': 'window_ms', 'type': 'float', 'value' : 50. },
                {'name': 'bin_ms', 'type': 'float', 'value' : 1.0 },
        ]
    _need_compute = True
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.isi_histograms, self.isi_bins = self.controller.get_isi_histograms()

        self.initialize_plot()
        

    def initialize_plot(self):
        self.viewBox = MyViewBox()
        self.viewBox.doubleclicked.connect(self.open_settings)
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()


    def compute(self):
        self.isi_histograms, self.isi_bins = self.controller.compute_isi_histograms(
                self.params['window_ms'],  self.params['bin_ms'])
        self.refresh()

    def on_params_changed(self):
        self.isi_histograms, self.isi_bins = None, None
        self.refresh()

    def _refresh(self):
        self.plot.clear()
        if self.isi_histograms is None:
            return
        
        n = 0
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                continue

            isi = self.isi_histograms[unit_index, :]
            
            qcolor = self.controller.qcolors[unit_id]
            curve = pg.PlotCurveItem(self.isi_bins[:-1], isi, pen=pg.mkPen(qcolor, width=3))
            self.plot.addItem(curve)

ISIView._gui_help_txt = """Inter spike intervals
Show only selected units.
Settings control the bin size in ms.
Right mouse : zoom"""

