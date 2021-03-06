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
                      {'name': 'bin_min', 'type': 'float', 'value' : 0. },
                      {'name': 'bin_max', 'type': 'float', 'value' : 100. },
                      {'name': 'bin_size', 'type': 'float', 'value' : 1.0 },
        ]
    _need_compute = True
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        #~ h = QT.QHBoxLayout()
        #~ self.layout.addLayout(h)
        #~ h.addWidget(QT.QLabel('<b>Similarity</b>') )

        #~ but = QT.QPushButton('settings')
        #~ but.clicked.connect(self.open_settings)
        #~ h.addWidget(but)
        
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.initialize_plot()
        
        #~ self.on_params_changed()#this do refresh    


    def initialize_plot(self):
        self.viewBox = MyViewBox()
        self.viewBox.doubleclicked.connect(self.open_settings)
        #~ self.viewBox.disableAutoRange()
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        #ISI are computed on demand
        self.all_isi = {}

    def compute(self):
        self.bins = np.arange(self.params['bin_min'], self.params['bin_max'], self.params['bin_size'])
        for unit_id in self.controller.unit_ids:
            spikes = self.controller.spikes
            unit_index = list(self.controller.unit_ids).index(unit_id)
            isi = []
            for segment_index in range(self.controller.num_segments):
                sel = (spikes['segment_index'] == segment_index) & (spikes['unit_index'] == unit_index)
                isi.append(np.diff(spikes[sel]['sample_index']).astype('float64')/self.controller.sampling_frequency)
            isi = np.concatenate(isi)
            isi *= 1000.  # ms
            
            if len(isi) ==0:
                count = np.zeros(bins.size -1)
            else:
                count, bins = np.histogram(isi, bins=self.bins)
            
            self.all_isi[unit_id] = count
        self.refresh()

    def on_params_changed(self):
        self.all_isi = {}
        self.refresh()


    def _refresh(self):
        self.plot.clear()
        if len(self.all_isi) ==0:
            return
        
        n = 0
        for unit_id in self.controller.unit_ids:
            if not self.controller.unit_visible_dict[unit_id]:
                continue
            
            #~ if unit_id not in self.all_isi:
                #~ self._compute_isi(unit_id)
            
            count = self.all_isi[unit_id]
            
            qcolor = self.controller.qcolors[unit_id]
            curve = pg.PlotCurveItem(self.bins[:-1], count, pen=pg.mkPen(qcolor, width=3))
            self.plot.addItem(curve)

ISIView._gui_help_txt = """Inter spike intervals
Show only selected units.
Settings control the bin size in ms.
Right mouse : zoom"""

