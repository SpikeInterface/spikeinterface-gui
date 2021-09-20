from .myqt import QT
import pyqtgraph as pg

import numpy as np
import pandas as pd

from .base import WidgetBase
#~ from ..tools import compute_cross_correlograms



class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass



class CrossCorrelogramView(WidgetBase):
    _params = [
                      {'name': 'window_size_ms', 'type': 'float', 'value' : 100. },
                      {'name': 'bin_size_ms', 'type': 'float', 'value' : 1.0 },
                      {'name': 'symmetrize', 'type': 'bool', 'value' : False },
                      {'name': 'display_axis', 'type': 'bool', 'value' : True },
                      {'name': 'max_visible', 'type': 'int', 'value' : 8 },
                      #~ {'name': 'check_sorted', 'type': 'bool', 'value' : False },
        ]
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)

        but = QT.QPushButton('settings')
        but.clicked.connect(self.open_settings)
        h.addWidget(but)

        but = QT.QPushButton('compute')
        but.clicked.connect(self.compute_ccg)
        h.addWidget(but)
        
        self.grid = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.grid)
        
        self.ccg = None


    def on_params_changed(self):
        self.ccg = None
        self.refresh()
    
    def compute_ccg(self):
        self.ccg, self.bins = self.controller.compute_correlograms(
                self.params['window_size_ms'],  self.params['bin_size_ms'], self.params['symmetrize'])
        self.refresh()

    def refresh(self):
        self.grid.clear()
        
        if self.ccg is None:
            return
        
        visible_unit_ids = [ ]
        for unit_id in self.controller.unit_ids:
            if self.controller.unit_visible_dict[unit_id]:
                visible_unit_ids.append(unit_id)

        visible_unit_ids = visible_unit_ids[:self.params['max_visible']]
        
        n = len(visible_unit_ids)
        
        #~ bins = self.bins * 1000. #to ms
        bins = self.bins
        
        #~ labels = self.controller.positive_cluster_labels.tolist()
        unit_ids = list(self.controller.unit_ids)
        
        for r in range(n):
            for c in range(r, n):
                
                i = unit_ids.index(visible_unit_ids[r])
                j = unit_ids.index(visible_unit_ids[c])
                
                count = self.ccg[i, j, :]
                
                plot = pg.PlotItem()
                if not self.params['display_axis']:
                    plot.hideAxis('bottom')
                    plot.hideAxis('left')
                
                if r==c:
                    unit_id = visible_unit_ids[r]
                    color = self.controller.qcolors[unit_id]
                else:
                    color = (120,120,120,120)
                
                curve = pg.PlotCurveItem(bins, count, stepMode=True, fillLevel=0, brush=color, pen=color)
                plot.addItem(curve)
                self.grid.addItem(plot, row=r, col=c)

