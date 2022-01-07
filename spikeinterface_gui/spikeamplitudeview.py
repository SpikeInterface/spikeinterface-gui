from .myqt import QT
import pyqtgraph as pg

import numpy as np

from .base import WidgetBase



class MyViewBox(pg.ViewBox):
    pass
    #~ clicked = QT.pyqtSignal(float, float)
    doubleclicked = QT.pyqtSignal()
    
    #~ def mouseClickEvent(self, ev):
        #~ pos = self.mapToView(ev.pos())
        #~ x, y = pos.x(), pos.y()
        #~ self.clicked.emit(x, y)
        #~ ev.accept()
        
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass



class SpikeAmplitudeView(WidgetBase):
    _params = [
            {'name': 'alpha', 'type': 'float', 'value' : 0.7, 'limits':(0, 1.), 'step':0.05 },
            {'name': 'scatter_size', 'type': 'float', 'value' : 4., 'step':0.5 },
        ]
    _need_compute = False
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)

        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        self.combo_seg = QT.QComboBox()
        h.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {seg_index}' for seg_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self.refresh)
        
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.initialize_plot()
        

    def on_params_changed(self):
        self.refresh()
    
    def initialize_plot(self):
        self.viewBox = MyViewBox()
        
        self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.disableAutoRange()
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        self.scatter = pg.ScatterPlotItem(size=self.params['scatter_size'], pxMode = True)
        self.plot.addItem(self.scatter)
        
        self._text_items = []
        
        
        self._amp_min = min(np.min(self.controller.spike_amplitudes[seg_index][unit_id])
                            for seg_index in range(self.controller.num_segments)
                            for unit_id in self.controller.unit_ids)

        self._amp_max = max(np.max(self.controller.spike_amplitudes[seg_index][unit_id])
                            for seg_index in range(self.controller.num_segments)
                            for unit_id in self.controller.unit_ids)
        
        self.plot.setYRange(self._amp_min,self._amp_max, padding = 0.0)


    
    def _refresh(self):
        
        self.scatter.clear()
        
        if self.controller.spike_amplitudes is None:
            return
            
        seg_index =  self.combo_seg.currentIndex()
        
        unit_ids = self.controller.unit_ids

        all_spikes = self.controller.spikes
        
        fs = self.controller.sampling_frequency
        
        self.scatter.setSize(self.params['scatter_size'])
        
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                continue

            color = QT.QColor(self.controller.qcolors[unit_id])
            color.setAlpha(int(self.params['alpha']*255))

            amps = self.controller.spike_amplitudes[seg_index][unit_id]

            keep = (all_spikes['segment_index'] == seg_index) & (all_spikes['unit_index'] == unit_index)
            spikes = all_spikes[keep]
            spike_times = spikes['sample_index'] / fs
            
            self.scatter.addPoints(x=spike_times, y=amps,  pen=pg.mkPen(None), brush=color)
        
        
        
        
        t1 = 0.
        t2 = self.controller.get_num_samples(seg_index) / fs
        self.plot.setXRange( t1, t2, padding = 0.0)
        #~ self.plot.setYRange(-.5, nb_visible-.5, padding = 0.0)


        

    

SpikeAmplitudeView._gui_help_txt = """Similarity view
Check similarity between units with several metric
Mouse lick : make visible one pair of unit."""