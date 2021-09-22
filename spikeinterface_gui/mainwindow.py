from .myqt import QT, QT_MODE


from .controller import SpikeinterfaceController

# 
from .unitlist import UnitListView
from .spikelist import SpikeListView
from .pairlist import PairListView
from .traceview import TraceView
from .waveformview import WaveformView
from .waveformheatmapview import WaveformHeatMapView
from .isiview import ISIView
from .crosscorrelogramview import CrossCorrelogramView
from .probeview import ProbeView
from .ndscatterview import NDScatterView
from .similarityview import SimilarityView


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
        self.isiview = ISIView(controller=self.controller)
        self.crosscorrelogramview = CrossCorrelogramView(controller=self.controller)
        self.probeview  = ProbeView(controller=self.controller)
        self.similarityview = SimilarityView(controller=self.controller)
        
        if self.controller.handle_principal_components():
            self.ndscatterview  = NDScatterView(controller=self.controller)
        

        docks = {}
        
        # top left
        docks['spikelist'] = QT.QDockWidget('spikelist',self)
        docks['spikelist'].setWidget(self.spikelist)
        self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['spikelist'])
        
        docks['pairlist'] = QT.QDockWidget('pairlist',self)
        docks['pairlist'].setWidget(self.pairlist)
        #~ self.tabifyDockWidget(docks['spikelist'], docks['pairlist'])
        #~ self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['pairlist'])
        self.splitDockWidget(docks['spikelist'], docks['pairlist'], QT.Qt.Horizontal)

        docks['unitlist'] = QT.QDockWidget('unitlist',self)
        docks['unitlist'].setWidget(self.unitlist)
        self.tabifyDockWidget(docks['pairlist'], docks['unitlist'])
        

        docks['probeview'] = QT.QDockWidget('probeview',self)
        docks['probeview'].setWidget(self.probeview)
        #~ self.tabifyDockWidget(docks['pairlist'], docks['probeview'])
        self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['probeview'])
        
        
        docks['similarityview'] = QT.QDockWidget('similarityview',self)
        docks['similarityview'].setWidget(self.similarityview)
        self.splitDockWidget(docks['probeview'], docks['similarityview'], QT.Qt.Horizontal)

        if self.controller.handle_principal_components():
            docks['ndscatterview'] = QT.QDockWidget('ndscatterview',self)
            docks['ndscatterview'].setWidget(self.ndscatterview)
            self.tabifyDockWidget(docks['similarityview'], docks['ndscatterview'])
            docks['ndscatterview'].raise_()
        
        
        docks['traceview'] = QT.QDockWidget('traceview',self)
        docks['traceview'].setWidget(self.traceview)
        self.addDockWidget(QT.Qt.RightDockWidgetArea, docks['traceview'])

        docks['waveformview'] = QT.QDockWidget('waveformview',self)
        docks['waveformview'].setWidget(self.waveformview)
        self.tabifyDockWidget(docks['traceview'], docks['waveformview'])

        docks['waveformheatmapview'] = QT.QDockWidget('waveformheatmapview',self)
        docks['waveformheatmapview'].setWidget(self.waveformheatmapview)
        self.tabifyDockWidget(docks['traceview'], docks['waveformheatmapview'])


        docks['isiview'] = QT.QDockWidget('isiview',self)
        docks['isiview'].setWidget(self.isiview)
        self.tabifyDockWidget(docks['traceview'], docks['isiview'])
        
        docks['crosscorrelogramview'] = QT.QDockWidget('crosscorrelogramview',self)
        docks['crosscorrelogramview'].setWidget(self.crosscorrelogramview)
        self.tabifyDockWidget(docks['traceview'], docks['crosscorrelogramview'])
        
        docks['traceview'].raise_()
        
