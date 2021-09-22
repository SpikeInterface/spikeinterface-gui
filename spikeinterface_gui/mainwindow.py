from .myqt import QT, QT_MODE


from .controller import SpikeinterfaceController

from .viewlist import possible_class_views


class MainWindow(QT.QMainWindow):
    def __init__(self,waveform_extractor,  parent=None, ):
        QT.QMainWindow.__init__(self, parent)
        
        self.waveform_extractor = waveform_extractor
        
        self.controller = SpikeinterfaceController(waveform_extractor)
        
        self.views = {}
        self.docks = {}
        
        ## main layout
        
        # list
        self.add_one_view('spikelist', area='left')
        self.add_one_view('pairlist', split='spikelist', orientation='horizontal')
        self.add_one_view('unitlist', tabify='pairlist')

        # on bottom left
        self.add_one_view('probeview', area='left')
        self.add_one_view('similarityview', split='probeview', orientation='horizontal')
        if self.controller.handle_principal_components():
            self.add_one_view('ndscatterview', tabify='similarityview')
            self.docks['ndscatterview'].raise_()
        
        # on right
        self.add_one_view('traceview', area='right')
        self.add_one_view('waveformview', tabify='traceview')
        self.add_one_view('waveformheatmapview', tabify='waveformview')
        self.add_one_view('isiview', tabify='waveformheatmapview')
        self.add_one_view('crosscorrelogramview', tabify='isiview')
        
        self.docks['traceview'].raise_()
        
        self.docks['traceview'].setGeometry(300, 600, 200, 120)
        


    def add_one_view(self, view_name, dock_title=None,
            area=None, orientation=None, tabify=None, split=None):
        assert view_name not in self.views, 'View is already in window'
        
        if dock_title is None:
            dock_title = view_name
    
        dock = MyDock(dock_title,self)
        view_class = possible_class_views[view_name]
        view = view_class(controller=self.controller)
        dock.setWidget(view)
        
        if area is not None:
            _area = areas.get(area)
            if orientation is None:
                self.addDockWidget(_area, dock)
            else:
                _orientation = orientations[orientation]
                self.addDockWidget(dock, _area, _orientation)

        elif tabify is not None:
            assert tabify in self.docks
            self.tabifyDockWidget(self.docks[tabify], dock)
        elif split is not None:
            assert split in self.docks
            _orientation = orientations[orientation]
            self.splitDockWidget(self.docks[split], dock, _orientation)
        
        dock.make_custum_title_bar(title=dock_title, view=view)
        
        self.views[view_name] = view
        self.docks[view_name] = dock

# custum dock with settings button
class MyDock(QT.QDockWidget):
    def __init__(self, *arg, **kargs):
        QT.QDockWidget.__init__(self, *arg, **kargs)
        
        
    
    def make_custum_title_bar(self, title='', view=None):
        # TODO set style with small icons and font
        # TODO link open settings and help
        
        titlebar = QT.QWidget(self)

        # style = 'QPushButton {padding: 5px;}'
        # titlebar.setStyleSheet(style)

        
        titlebar.setMaximumHeight(12)
        self.setTitleBarWidget(titlebar)
        
        h = QT.QHBoxLayout()
        titlebar.setLayout(h)
        h.setContentsMargins(0, 0, 0, 0)
        
        label = QT.QLabel(title)
        h.addWidget(label)
        
        h.addStretch()
        
        if view._params is not None:
            but = QT.QPushButton('settings')
            h.addWidget(but)
            but.clicked.connect(view.open_settings)
        
        but = QT.QPushButton('?')
        h.addWidget(but)
        but.clicked.connect(view.open_help)
        but.setFixedSize(12,12)
        but.setToolTip(view._gui_help_txt)

        but = QT.QPushButton('✕')
        h.addWidget(but)
        but.clicked.connect(self.close)
        but.setFixedSize(12,12)
        
        
        

areas = {
    'right' : QT.Qt.RightDockWidgetArea,
    'left' : QT.Qt.LeftDockWidgetArea,
}

orientations = {
    'horizontal' : QT.Qt.Horizontal,
    'vertical' : QT.Qt.Vertical,
}