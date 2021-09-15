from .myqt import QT, QT_MODE


from .controller import SpikeinterfaceController

# 
from .unitlist import UnitListView
from .spikelist import SpikeListView
from .pairlist import PairListView
from .traceview import TraceView
from .waveformview import WaveformView
from .waveformheatmapview import WaveformHeatMapView


class MainWindow(QT.QMainWindow):
    def __init__(self,waveform_extractor,  parent=None, ):
        QT.QMainWindow.__init__(self, parent)
        
        self.waveform_extractor = waveform_extractor
        
        self.controller = SpikeinterfaceController(waveform_extractor)
    
        self.spikelist = SpikeListView(controller=self.controller)
        self.unitlist = UnitListView(controller=self.controller)
        self.pairlist = PairListView(controller=self.controller)
        self.traceview = TraceView(controller=self.controller)
        self.waveformview = WaveformView(controller=self.controller)
        self.waveformheatmapview = WaveformHeatMapView(controller=self.controller)
        
        
        
        
        docks = {}

        docks['spikelist'] = QT.QDockWidget('spikelist',self)
        docks['spikelist'].setWidget(self.spikelist)
        self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['spikelist'])
        
        docks['pairlist'] = QT.QDockWidget('pairlist',self)
        docks['pairlist'].setWidget(self.pairlist)
        #~ self.tabifyDockWidget(docks['pairlist'], docks['unitlist'])
        self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['pairlist'])

        docks['unitlist'] = QT.QDockWidget('unitlist',self)
        docks['unitlist'].setWidget(self.unitlist)
        self.tabifyDockWidget(docks['pairlist'], docks['unitlist'])
        #~ self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['unitlist'])
        
        


        docks['traceview'] = QT.QDockWidget('traceview',self)
        docks['traceview'].setWidget(self.traceview)
        self.addDockWidget(QT.Qt.RightDockWidgetArea, docks['traceview'])
        #~ self.tabifyDockWidget(docks['waveformhistviewer'], docks['traceview'])

        docks['waveformview'] = QT.QDockWidget('waveformview',self)
        docks['waveformview'].setWidget(self.waveformview)
        #~ self.addDockWidget(QT.Qt.RightDockWidgetArea, docks['waveformview'])
        self.tabifyDockWidget(docks['traceview'], docks['waveformview'])

        docks['waveformheatmapview'] = QT.QDockWidget('waveformheatmapview',self)
        docks['waveformheatmapview'].setWidget(self.waveformheatmapview)
        #~ self.addDockWidget(QT.Qt.RightDockWidgetArea, docks['waveformheatmapview'])
        self.tabifyDockWidget(docks['traceview'], docks['waveformheatmapview'])


        
        
