from .myqt import QT, QT_MODE


from .controller import SpikeinterfaceController

# 
from .unitlist import UnitListView
from .spikelist import SpikeListView



class MainWindow(QT.QMainWindow):
    def __init__(self,waveform_extractor,  parent=None, ):
        QT.QMainWindow.__init__(self, parent)
        
        self.waveform_extractor = waveform_extractor
        
        self.controller = SpikeinterfaceController(waveform_extractor)
    
        self.spikelist = SpikeListView(controller=self.controller)
        self.unitlist = UnitListView(controller=self.controller)
        
        
        
        docks = {}

        docks['spikelist'] = QT.QDockWidget('spikelist',self)
        docks['spikelist'].setWidget(self.spikelist)
        self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['spikelist'])
        
        docks['unitlist'] = QT.QDockWidget('unitlist',self)
        docks['unitlist'].setWidget(self.unitlist)
        #~ self.tabifyDockWidget(docks['pairlist'], docks['unitlist'])
        self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['unitlist'])
        
        
