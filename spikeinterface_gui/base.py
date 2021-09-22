from .myqt import QT
import pyqtgraph as pg

import time


class ControllerBase(QT.QObject):
    # spike_selection_changed = QT.pyqtSignal()
    # spike_label_changed = QT.pyqtSignal()
    # unit_visibility_changed = QT.pyqtSignal()

    
    def __init__(self, parent=None):
        QT.QObject.__init__(self, parent=parent)
        self.views = []
    
    def declare_a_view(self, new_view):
        assert new_view not in self.views, 'view already declared {}'.format(self)
        self.views.append(new_view)
        
        new_view.spike_selection_changed.connect(self.on_spike_selection_changed)
        new_view.spike_label_changed.connect(self.on_spike_label_changed)
        new_view.unit_visibility_changed.connect(self.on_unit_visibility_changed)
        new_view.channel_visibility_changed.connect(self.on_channel_visibility_changed)
        
        
    def on_spike_selection_changed(self):
        for view in self.views:
            if view==self.sender(): continue
            #~ t1 = time.perf_counter()
            view.on_spike_selection_changed()
            #~ t2 = time.perf_counter()
            #~ print('on_spike_selection_changed',view,  t2-t1)

    def on_spike_label_changed(self):
        for view in self.views:
            if view==self.sender(): continue
            #~ t1 = time.perf_counter()
            view.on_spike_label_changed()
            #~ t2 = time.perf_counter()
            #~ print('on_spike_label_changed',view,  t2-t1)
    
    def on_unit_visibility_changed(self):
        #~ print('on_unit_visibility_changed')
        for view in self.views:
            if view==self.sender(): continue
            #~ print(view.isVisible())
            #~ t1 = time.perf_counter()
            view.on_unit_visibility_changed()
            #~ t2 = time.perf_counter()
            #~ print('on_unit_visibility_changed',view,  t2-t1)

    def on_channel_visibility_changed(self):
        for view in self.views:
            if view==self.sender(): continue
            #~ t1 = time.perf_counter()
            view.on_channel_visibility_changed()
            #~ t2 = time.perf_counter()
            #~ print('on_channel_visibility_changed',view,  t2-t1)



    


class WidgetBase(QT.QWidget):
    spike_selection_changed = QT.pyqtSignal()
    spike_label_changed = QT.pyqtSignal()
    unit_visibility_changed = QT.pyqtSignal()
    channel_visibility_changed = QT.pyqtSignal()
    
    _params = None
    _gui_help_txt = "The help for this view it not done yet"
    def __init__(self, parent = None, controller=None):
        QT.QWidget.__init__(self, parent)
        self.controller = controller
        if self.controller is not None:
            self.controller.declare_a_view(self)
        
        if self._params is not None:
            self.create_settings()
    
    def refresh(self):
        raise(NotImplementedError)

    def create_settings(self):
        self.params = pg.parametertree.Parameter.create( name='settings', type='group', children=self._params)
        
        self.tree_params = pg.parametertree.ParameterTree(parent=self)
        self.tree_params.header().hide()
        self.tree_params.setParameters(self.params, showTop=True)
        self.tree_params.setWindowTitle(u'Options for waveforms hist viewer')
        self.tree_params.setWindowFlags(QT.Qt.Window)
        
        self.params.sigTreeStateChanged.connect(self.on_params_changed)

    def open_settings(self):
        if not self.tree_params.isVisible():
            self.tree_params.show()
        else:
            self.tree_params.hide()
    
    def open_help(self):
        but = self.sender()
        QT.QToolTip.showText(but.mapToGlobal(QT.QPoint()),self._gui_help_txt, but)
    
    def on_params_changed(self):
        self.refresh()
    
    def on_spike_selection_changed(self):
        self.refresh()

    def on_spike_label_changed(self):
        self.refresh()
        
    def on_unit_visibility_changed(self):
        self.refresh()
    
    def on_channel_visibility_changed(self):
        pass

