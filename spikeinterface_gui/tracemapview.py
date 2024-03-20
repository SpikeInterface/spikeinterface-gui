from .myqt import QT
import pyqtgraph as pg

import numpy as np
import time

from .base import WidgetBase
from .tools import TimeSeeker
from .traceview import MixinViewTrace

# _trace_sources = ['preprocessed', 'raw']
_trace_sources = ['preprocessed']

class MyViewBox(pg.ViewBox):
    pass
    # doubleclicked = QT.pyqtSignal(float, float)
    # gain_zoom = QT.pyqtSignal(float)
    # xsize_zoom = QT.pyqtSignal(float)
    # def __init__(self, *args, **kwds):
    #     pg.ViewBox.__init__(self, *args, **kwds)
    # def mouseClickEvent(self, ev):
    #     ev.accept()
    # def mouseDoubleClickEvent(self, ev):
    #     pos = self.mapToView(ev.pos())
    #     x, y = pos.x(), pos.y()
    #     self.doubleclicked.emit(x, y)
    #     ev.accept()
    # def mouseDragEvent(self, ev):
    #     ev.ignore()
    # def wheelEvent(self, ev, axis=None):
    #     if ev.modifiers() == QT.Qt.ControlModifier:
    #         z = 10 if ev.delta()>0 else 1/10.
    #     else:
    #         z = 1.3 if ev.delta()>0 else 1/1.3
    #     self.gain_zoom.emit(z)
    #     ev.accept()
    # def mouseDragEvent(self, ev):
    #     ev.accept()
    #     self.xsize_zoom.emit((ev.pos()-ev.lastPos()).x())


class TraceMapView(WidgetBase, MixinViewTrace):
    
    _params = [
        # {'name': 'auto_zoom_on_select', 'type': 'bool', 'value': True },
        # {'name': 'zoom_size', 'type': 'float', 'value':  0.08, 'step' : 0.001 },
        # {'name': 'plot_threshold', 'type': 'bool', 'value':  True },
        # {'name': 'alpha', 'type': 'float', 'value' : 0.8, 'limits':(0, 1.), 'step':0.05 },
        {'name': 'xsize_max', 'type': 'float', 'value': 4.0, 'step': 1.0, 'limits':(1.0, np.inf)},
        {'name': 'max_visible_channel', 'type': 'int', 'value':  16},
    ]
    
    def __init__(self,controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)

        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.create_toolbar()
        
        
        # create graphic view and 2 scroll bar
        g = QT.QGridLayout()
        self.layout.addLayout(g)
        self.graphicsview = pg.GraphicsView()
        g.addWidget(self.graphicsview, 0,1)
        self.initialize_plot()
        self.scroll_time = QT.QScrollBar(orientation=QT.Qt.Horizontal)
        g.addWidget(self.scroll_time, 1,1)
        self.scroll_time.valueChanged.connect(self.on_scroll_time)
        
        #handle time by segments
        self.time_by_seg = np.array([0.]*self.controller.num_segments, dtype='float64')

        self.change_segment(0)
        self.refresh()

    def on_params_changed(self):
        print('TODO on_params_changed')

    def scatter_item_clicked(self, x, y):
        print('TODO scatter_item_clicked')
    
    def on_spike_selection_changed(self):
        print('TODO on_spike_selection_changed')

    def _initialize_plot(self):
        pass
        # self.curve_predictions = pg.PlotCurveItem(pen='#FF00FF', connect='finite')
        # self.plot.addItem(self.curve_predictions)
        # self.curve_residuals = pg.PlotCurveItem(pen='#FFFF00', connect='finite')
        # self.plot.addItem(self.curve_residuals)


    def _refresh(self):
        self.seek(self.time_by_seg[self.seg_num])

    def seek(self, t):
        if self.sender() is not self.timeseeker:
            self.timeseeker.seek(t, emit = False)
