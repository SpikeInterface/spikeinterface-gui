from .myqt import QT
import pyqtgraph as pg

from .viewlist import possible_class_views

import time

# Used by views to emit/trigger signals
class SignalNotifyer(QT.QObject):
    spike_selection_changed = QT.pyqtSignal()
    unit_visibility_changed = QT.pyqtSignal()
    channel_visibility_changed = QT.pyqtSignal()
    manual_curation_updated = QT.pyqtSignal()

    def __init__(self, parent=None):
        QT.QObject.__init__(self, parent=parent)

    def notify_spike_selection_changed(self):
        self.spike_selection_changed.emit()

    def notify_unit_visibility_changed(self):
        self.unit_visibility_changed.emit()

    def notify_channel_visibility_changed(self):
        self.channel_visibility_changed.emit()

    def notify_manual_curation_updated(self):
        self.manual_curation_updated.emit()


# Used by controler to handle/callback signals
class SignalHandler(QT.QObject):
    def __init__(self, controller, parent=None):
        QT.QObject.__init__(self, parent=parent)
        self.controller = controller

    def connect_view(self, view):
        view.notifyer.spike_selection_changed.connect(self.on_spike_selection_changed)
        view.notifyer.unit_visibility_changed.connect(self.on_unit_visibility_changed)
        view.notifyer.channel_visibility_changed.connect(self.on_channel_visibility_changed)
        view.notifyer.manual_curation_updated.connect(self.on_manual_curation_updated)

    def on_spike_selection_changed(self):
        for view in self.controller.views:
            if view==self.sender(): continue
            view.on_spike_selection_changed()
  
    def on_unit_visibility_changed(self):
        for view in self.controller.views:
            if view==self.sender(): continue
            view.on_unit_visibility_changed()

    def on_channel_visibility_changed(self):
        for view in self.controller.views:
            if view==self.sender(): continue
            view.on_channel_visibility_changed()

    def on_manual_curation_updated(self):
        for view in self.controller.views:
            if view == self.sender(): continue
            view.on_manual_curation_updated()
    


def create_settings(view, parent):
    view.settings = pg.parametertree.Parameter.create( name='settings', type='group', children=view._settings)
    
    # not that the parent is not the view (not Qt anymore) itself but the widget
    view.tree_settings = pg.parametertree.ParameterTree(parent=parent)
    view.tree_settings.header().hide()
    view.tree_settings.setParameters(view.settings, showTop=True)
    view.tree_settings.setWindowTitle(u'View options')
    view.tree_settings.setWindowFlags(QT.Qt.Window)
    
    view.settings.sigTreeStateChanged.connect(view.on_settings_changed)





# open settings
# open help



class MainWindow(QT.QMainWindow):
    def __init__(self, controller, parent=None):
        QT.QMainWindow.__init__(self, parent)
        
        self.controller = controller
        self.verbose = controller.verbose

        self.views = {}
        self.docks = {}
        
        ## main layout
        
        # list
        self.add_one_view('spikelist', area='left')
        self.add_one_view('mergelist', split='spikelist', orientation='horizontal')
        # self.add_one_view('unitlist', split='spikelist', orientation='horizontal')
        self.add_one_view('unitlist', tabify='mergelist')
        if self.controller.curation:
            self.add_one_view('curation', tabify='spikelist')
            # self.docks['spikelist'].raise_()

        # # on bottom left
        self.add_one_view('probeview', area='left')
        self.add_one_view('similarityview', split='probeview', orientation='horizontal')
        self.add_one_view('ndscatterview', tabify='similarityview') # optional

        
        # on right
        if self.controller.with_traces:
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
        
        # if 'traceview' in self.docks:
        #     self.docks['traceview'].raise_()
        #     self.docks['traceview'].setGeometry(300, 600, 200, 120)
        
    def add_one_view(self, view_name, dock_title=None,
            area=None, orientation=None, tabify=None, split=None):
        assert view_name not in self.views, 'View is already in window'
        
        if self.verbose:
            t0 = time.perf_counter()
            print('view', view_name)
            
        if dock_title is None:
            dock_title = view_name

        view_class = possible_class_views[view_name]
        if 'qt' not in view_class._supported_backend:
            return

        if not self.controller.check_is_view_possible(view_name):
            return 

        dock = MyDock(dock_title, parent=self)
        
        widget = QT.QWidget(parent=self)
        view = view_class(controller=self.controller, parent=widget, backend='qt')

        
        widget.setLayout(view.layout)

        dock.setWidget(widget)
        
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
        
        dock.make_custum_title_bar(title=dock_title, view=view, widget=widget)
        
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

    def make_custum_title_bar(self, title='', view=None, widget=None):
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

        # mainwindow = self.parent()
        self.view = view

        if view._settings is not None:
            but = QT.QPushButton('settings')
            h.addWidget(but)
            # TODO open settings
            but.clicked.connect(self.open_settings)
            # but.setStyleSheet(but_style)

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
        but.clicked.connect(self.open_help)
        but.setFixedSize(12,12)
        but.setToolTip(view._gui_help_txt)

        but = QT.QPushButton('✕')
        h.addWidget(but)
        # but.clicked.connect(self.close)
        but.setFixedSize(12,12)


    def open_settings(self):
        
        if not self.view.tree_settings.isVisible():
            self.view.tree_settings.show()
        else:
            self.view.tree_settings.hide()
    
    def open_help(self):
        but = self.sender()
        txt = self.view._gui_help_txt
        QT.QToolTip.showText(but.mapToGlobal(QT.QPoint()), txt, but)

        
        
        

areas = {
    'right' : QT.Qt.RightDockWidgetArea,
    'left' : QT.Qt.LeftDockWidgetArea,
}

orientations = {
    'horizontal' : QT.Qt.Horizontal,
    'vertical' : QT.Qt.Vertical,
}
