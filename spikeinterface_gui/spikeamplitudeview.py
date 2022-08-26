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
            {'name': 'num_bins', 'type': 'int', 'value' : 80, 'step': 1 },
            
            
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
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        self.graphicsview = pg.GraphicsView()
        #~ self.graphicsview.setHorizontalStretch(3)
        #~ self.layout.addWidget(self.graphicsview)
        h.addWidget(self.graphicsview, 3)

        self.graphicsview2 = pg.GraphicsView()
        #~ self.layout.addWidget(self.graphicsview2)
        h.addWidget(self.graphicsview2, 1)
        #~ self.graphicsview2.setHorizontalStretch(1)


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
    
        self.viewBox2 = MyViewBox()
        self.viewBox2.doubleclicked.connect(self.open_settings)
        self.viewBox2.disableAutoRange()
        self.plot2 = pg.PlotItem(viewBox=self.viewBox2)
        self.graphicsview2.setCentralItem(self.plot2)
        self.plot2.hideButtons()
        self.plot2.setYLink(self.plot)

        #~ l = pg.GraphicsLayout()
        
        #~ # hack to force 4 row
        #~ rem = [l.addPlot() for i in range(4)]
        #~ l.nextRow()
        
        #~ self.graphicsview.setCentralItem(l)
        #~ self.plot = l.addPlot(row=1, col=0, colspan=3)
        #~ self.plot.hideButtons()
        
        #~ self.plot2 = l.addPlot(row=1, col=3, colspan=1)
        #~ self.plot2.hideButtons()
        
        #~ self.plot2.setYLink(self.plot)
        
        #~ #end of the hack hack to force 4 row
        #~ for p in rem:
            #~ l.removeItem(p)
        
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
        self.plot2.clear()
        
        if self.controller.spike_amplitudes is None:
            return
            
        seg_index =  self.combo_seg.currentIndex()
        
        unit_ids = self.controller.unit_ids

        all_spikes = self.controller.spikes
        
        fs = self.controller.sampling_frequency
        
        self.scatter.setSize(self.params['scatter_size'])
        
        max_count = 0
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
            
            count, bins = np.histogram(amps, bins = np.linspace(self._amp_min, self._amp_max, self.params['num_bins']))
            # trick to avoid bad borders
            count[0] = 0
            count[-1] = 0
            
            max_count = max(max_count, np.max(count))
            
            #~ color = QT.QColor(self.controller.qcolors[unit_id])
            # curve = pg.PlotCurveItem(count, bins, stepMode='center', fillLevel=0, brush=color, pen=color)
            curve = pg.PlotCurveItem(count, bins[:-1], fillLevel=0, fillOutline=True, brush=color, pen=color)
            self.plot2.addItem(curve)

            
        
        t1 = 0.
        t2 = self.controller.get_num_samples(seg_index) / fs
        self.plot.setXRange( t1, t2, padding = 0.0)
        #~ self.plot.setYRange(-.5, nb_visible-.5, padding = 0.0)
        
        self.plot2.setXRange(0, max_count, padding = 0.0)

        

    

SpikeAmplitudeView._gui_help_txt = """Similarity view
Check similarity between units with several metric
Mouse lick : make visible one pair of unit."""