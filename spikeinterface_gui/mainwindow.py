import time

from .myqt import QT, QT_MODE


from .controller import SpikeinterfaceController

from .viewlist import possible_class_views


class MainWindow(QT.QMainWindow):
    def __init__(self,analyzer,  parent=None, verbose=False, curation=False, curation_data=None, label_definitions=None,
                 with_traces=True):
        QT.QMainWindow.__init__(self, parent)
        
        self.verbose = verbose
        
        # self.analyzer = analyzer
        
        if verbose:
            
            print('Controller:')
            t0 = time.perf_counter()
        self.controller = SpikeinterfaceController(analyzer, verbose=verbose,
                                                   curation=curation, curation_data=curation_data, label_definitions=label_definitions,
                                                   with_traces=with_traces)
        
        if verbose:
            t1 = time.perf_counter()
            print('Total controller init', t1 - t0)
            print()

        self.views = {}
        self.docks = {}
        
        ## main layout
        
        # list
        self.add_one_view('spikelist', area='left')
        self.add_one_view('pairlist', split='spikelist', orientation='horizontal')
        self.add_one_view('unitlist', tabify='pairlist')
        if self.controller.curation:
            self.add_one_view('curation', tabify='spikelist')
            # self.docks['spikelist'].raise_()

        # on bottom left
        self.add_one_view('probeview', area='left')
        self.add_one_view('similarityview', split='probeview', orientation='horizontal')
        
        self.add_one_view('ndscatterview', tabify='similarityview') # optional
        
        # on right
        if with_traces:
            self.add_one_view('traceview', area='right') # optional
            if self.controller.num_channels >=16:
                self.add_one_view('tracemapview',  tabify='traceview') # optional
        
        if 'tracemapview' in self.docks:
            self.add_one_view('waveformview', tabify='tracemapview')
        elif 'traceview' in self.docks:
            self.add_one_view('waveformview', tabify='traceview')
        else:
            self.add_one_view('waveformview', area='right')
        
        self.add_one_view('waveformheatmapview', tabify='waveformview')

        next_tab = 'waveformheatmapview' if 'waveformheatmapview' in self.docks else 'waveformview'
        self.add_one_view('isiview', tabify=next_tab)
        self.add_one_view('crosscorrelogramview', tabify='isiview')
        self.add_one_view('spikeamplitudeview', tabify='crosscorrelogramview') # optional
        
        if 'traceview' in self.docks:
            self.docks['traceview'].raise_()
            self.docks['traceview'].setGeometry(300, 600, 200, 120)
        
    def add_one_view(self, view_name, dock_title=None,
            area=None, orientation=None, tabify=None, split=None):
        assert view_name not in self.views, 'View is already in window'
        
        if self.verbose:
            t0 = time.perf_counter()
            print('view', view_name)
            
        if dock_title is None:
            dock_title = view_name

        view_class = possible_class_views[view_name]
        if view_class._depend_on is not None:
            depencies_ok = all(self.controller.has_extension(k) for k in view_class._depend_on)
            if not depencies_ok:
                if self.verbose:
                    print(view_name, 'does not have all dependencies', view_class._depend_on)                
                return None

        dock = MyDock(dock_title,self)
        
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
        
        dock.visibilityChanged.connect(view.refresh)
        
        self.views[view_name] = view
        self.docks[view_name] = dock

        if self.verbose:
            t1 = time.perf_counter()
            print('view', view_name, t1-t0)
            
            #~ print('refresh view')
            #~ view.refresh()
            #~ t2 = time.perf_counter()
            #~ print(t2-t1)
            
            



# custum dock with settings button
class MyDock(QT.QDockWidget):
    def __init__(self, *arg, **kargs):
        QT.QDockWidget.__init__(self, *arg, **kargs)

    def make_custum_title_bar(self, title='', view=None):
        # TODO set style with small icons and font
        
        titlebar = QT.QWidget(self)

        # style = 'QPushButton {padding: 5px;}'
        # titlebar.setStyleSheet(style)

        titlebar.setMaximumHeight(14)
        self.setTitleBarWidget(titlebar)
        
        h = QT.QHBoxLayout()
        titlebar.setLayout(h)
        h.setContentsMargins(0, 0, 0, 0)
        
        h.addSpacing(10)
        
        label = QT.QLabel(f'<b>{title}</b>')
        
        h.addWidget(label)
        
        h.addStretch()

        but_style = "QPushButton{border-width: 1px; font: 10px; padding: 10px}"

        if view._params is not None:
            but = QT.QPushButton('settings')
            h.addWidget(but)
            but.clicked.connect(view.open_settings)
            but.setStyleSheet(but_style)

        if view._need_compute:
            but = QT.QPushButton('compute')
            h.addWidget(but)
            but.clicked.connect(view.compute)
            but.setStyleSheet(but_style)

        but = QT.QPushButton('refresh')
        h.addWidget(but)
        but.clicked.connect(view.refresh)
        but.setStyleSheet(but_style)
        
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