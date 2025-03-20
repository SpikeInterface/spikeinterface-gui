from .myqt import QT
import pyqtgraph as pg

from .viewlist import possible_class_views
from .layout_presets import get_layout_description

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




# TODO sam : remove the MyDock and make a toolbar inside the widget (bug on some qt version)
# open settings
# open help


class QtMainWindow(QT.QMainWindow):
    def __init__(self, controller, parent=None, layout_preset=None):
        QT.QMainWindow.__init__(self, parent)
        
        self.controller = controller
        self.verbose = controller.verbose
        self.layout_preset = layout_preset

        self.make_views()
        self.create_main_layout()

        # refresh all views
        for view in self.views.values():
            view.refresh()

    def make_views(self):
        self.views = {}
        self.docks = {}
        for view_name, view_class in possible_class_views.items():
            if 'qt' not in view_class._supported_backend:
                continue
            if not self.controller.check_is_view_possible(view_name):
                continue
            
            if view_name == 'curation' and not self.controller.curation:
                continue

            # widget = QT.QWidget(parent=self)
            widget = QT.QWidget()
            view = view_class(controller=self.controller, parent=widget, backend='qt')
            widget.setLayout(view.layout)

            # dock = MyDock(view_name, parent=self)
            dock = MyDock(view_name)
            dock.setWidget(widget)
            dock.make_custum_title_bar(title=view_name, view=view, widget=widget)
            dock.visibilityChanged.connect(view.refresh)
            
            self.views[view_name] = view
            self.docks[view_name] = dock

    def create_main_layout(self):
        preset = get_layout_description(self.layout_preset)

        widgets_zone = {}
        for zone, view_names in preset.items():
            # keep only instanciated views
            view_names = [view_name for view_name in view_names if view_name in self.views.keys()]
            widgets_zone[zone] = view_names


        # upper_sidebar
        last_upper = None
        for i, view_name in enumerate(widgets_zone['upper_sidebar']):
            dock = self.docks[view_name]
            if i == 0:
                self.addDockWidget(areas['left'], dock)
            else:
                self.tabifyDockWidget(self.docks[last_upper], dock)
            last_upper = view_name

        # upper_left
        for i, view_name in enumerate(widgets_zone['upper_left']):
            dock = self.docks[view_name]
            if i == 0 and last_upper is None:
                self.addDockWidget(areas['left'], dock)
            elif i == 0 and last_upper is not None:
                _orientation = orientations['horizontal']
                self.splitDockWidget(self.docks[last_upper], dock, _orientation)
            else:
                self.tabifyDockWidget(self.docks[last_upper], dock)
            last_upper = view_name

        # bottom_sidebar
        last_bottom = None
        for i, view_name in enumerate(widgets_zone['bottom_sidebar']):
            dock = self.docks[view_name]
            if i == 0:
                _area = areas.get('left')
                self.addDockWidget(_area, dock)
            else:
                self.tabifyDockWidget(self.docks[last_bottom], dock)
            last_bottom = view_name

        # bottom_left
        for i, view_name in enumerate(widgets_zone['bottom_left']):
            dock = self.docks[view_name]
            if i == 0 and last_bottom is None:
                _area = areas.get('left')
                self.addDockWidget(_area, dock)
            elif i == 0 and last_bottom is not None:
                _orientation = orientations['horizontal']
                self.splitDockWidget(self.docks[last_bottom], dock, _orientation)
            else:
                self.tabifyDockWidget(self.docks[last_bottom], dock)
            last_bottom = view_name

        # upper_right
        last_right = None
        for i, view_name in enumerate(widgets_zone['upper_right']):
            dock = self.docks[view_name]
            if i == 0:
                _area = areas.get('right')
                self.addDockWidget(_area, dock)
            else:
                self.tabifyDockWidget(self.docks[last_right], dock)
            last_right = view_name

        # bottom_right
        last_right = None
        for i, view_name in enumerate(widgets_zone['bottom_right']):
            dock = self.docks[view_name]
            if i == 0:
                _area = areas.get('right')
                self.addDockWidget(_area, dock)
            else:
                self.tabifyDockWidget(self.docks[last_right], dock)
            last_right = view_name

        # make visible the first of each zone
        for zone, view_names in widgets_zone.items():
            if len(view_names) > 1:
                self.docks[view_names[0]].raise_()



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
