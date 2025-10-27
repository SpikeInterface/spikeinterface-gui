from .myqt import QT
import pyqtgraph as pg
import markdown
import numpy as np
from copy import copy

import weakref
import json

from .viewlist import possible_class_views
from .layout_presets import get_layout_description
from .utils_global import fill_unnecessary_space, get_present_zones_in_half_of_layout

from .utils_qt import qt_style, add_stretch_to_qtoolbar

# Used by views to emit/trigger signals
class SignalNotifier(QT.QObject):
    spike_selection_changed = QT.pyqtSignal()
    unit_visibility_changed = QT.pyqtSignal()
    channel_visibility_changed = QT.pyqtSignal()
    manual_curation_updated = QT.pyqtSignal()
    time_info_updated = QT.pyqtSignal()
    unit_color_changed = QT.pyqtSignal()

    def __init__(self, parent=None, view=None):
        QT.QObject.__init__(self, parent=parent)
        self.view = view

    def notify_spike_selection_changed(self):
        self.spike_selection_changed.emit()

    def notify_unit_visibility_changed(self):
        self.unit_visibility_changed.emit()

    def notify_channel_visibility_changed(self):
        self.channel_visibility_changed.emit()

    def notify_manual_curation_updated(self):
        self.manual_curation_updated.emit()

    def notify_time_info_updated(self):
        self.time_info_updated.emit()

    def notify_unit_color_changed(self):
        self.unit_color_changed.emit()


# Used by controler to handle/callback signals
class SignalHandler(QT.QObject):
    def __init__(self, controller, parent=None):
        QT.QObject.__init__(self, parent=parent)
        self.controller = controller
        self._active = True
    
    def activate(self):
        self._active = True

    def deactivate(self):
        self._active = False

    def connect_view(self, view):
        view.notifier.spike_selection_changed.connect(self.on_spike_selection_changed)
        view.notifier.unit_visibility_changed.connect(self.on_unit_visibility_changed)
        view.notifier.channel_visibility_changed.connect(self.on_channel_visibility_changed)
        view.notifier.manual_curation_updated.connect(self.on_manual_curation_updated)
        view.notifier.time_info_updated.connect(self.on_time_info_updated)
        view.notifier.unit_color_changed.connect(self.on_unit_color_changed)

    def on_spike_selection_changed(self):
        if not self._active:
            return
        for view in self.controller.views:
            if view.qt_widget == self.sender().parent():
                # do not refresh it self
                continue
            view.on_spike_selection_changed()
  
    def on_unit_visibility_changed(self):

        if not self._active:
            return
        for view in self.controller.views:
            if view.qt_widget == self.sender().parent():
                # do not refresh it self
                continue
            view.on_unit_visibility_changed()

    def on_channel_visibility_changed(self):
        if not self._active:
            return
        for view in self.controller.views:
            if view.qt_widget == self.sender().parent():
                # do not refresh it self
                continue
            view.on_channel_visibility_changed()

    def on_manual_curation_updated(self):
        if not self._active:
            return
        for view in self.controller.views:
            if view.qt_widget == self.sender().parent():
                # do not refresh it self
                continue
            view.on_manual_curation_updated()

    def on_time_info_updated(self):
        if not self._active:
            return
        for view in self.controller.views:
            if view.qt_widget == self.sender().parent():
                # do not refresh it self
                continue
            view.on_time_info_updated()
    
    def on_unit_color_changed(self):
        if not self._active:
            return
        for view in self.controller.views:
            if view.qt_widget == self.sender().parent():
                # do not refresh it self
                continue
            view.on_unit_color_changed()


def create_settings(view, parent):
    view.settings = pg.parametertree.Parameter.create(name="settings", type='group', children=view._settings)
    
    # not that the parent is not the view (not Qt anymore) itself but the widget
    view.tree_settings = pg.parametertree.ParameterTree(parent=parent)
    view.tree_settings.header().hide()
    view.tree_settings.setParameters(view.settings, showTop=True)
    view.tree_settings.setWindowTitle(u'View options')
    # view.tree_settings.setWindowFlags(QT.Qt.Window)

def listen_setting_changes(view):
    view.settings.sigTreeStateChanged.connect(view.on_settings_changed)

def stop_listen_setting_changes(view):
    view.settings.sigTreeStateChanged.disconnect(view.on_settings_changed)


class QtMainWindow(QT.QMainWindow):
    main_window_closed = QT.pyqtSignal(object)

    def __init__(self, controller, parent=None, layout_preset=None, layout=None, user_settings=None):
        QT.QMainWindow.__init__(self, parent)
        
        self.controller = controller
        self.verbose = controller.verbose
        self.layout_preset = layout_preset
        self.layout = layout
        
        self.make_views(user_settings)
        self.create_main_layout()

        # refresh all views wihtout notiying
        self.controller.signal_handler.deactivate()
        for view in self.views.values():
            # refresh do not work because view are not yet visible at init
            view._refresh()
        self.controller.signal_handler.activate()
        # TODO sam : all veiws are always refreshed at the moment so this is useless.
        # uncommen this when ViewBase.is_view_visible() work correctly
        # for view_name, dock in self.docks.items():
        #     dock.visibilityChanged.connect(self.views[view_name].refresh)

    def make_views(self, user_settings):
        self.views = {}
        self.docks = {}
        for view_name, view_class in possible_class_views.items():
            if 'qt' not in view_class._supported_backend:
                continue
            if not self.controller.check_is_view_possible(view_name):
                continue
            
            if view_name == 'curation' and not self.controller.curation:
                continue

            if view_name in ("trace", "tracemap") and not self.controller.with_traces:
                continue

            widget = ViewWidget(view_class)
            view = view_class(controller=self.controller, parent=widget, backend='qt')

            if user_settings is not None and user_settings.get(view_name) is not None:
                for setting_name, user_setting in user_settings.get(view_name).items():
                    if setting_name not in view.settings.keys().keys():
                        raise KeyError(f"Setting {setting_name} is not a valid setting for View {view_name}. Check your settings file.")
                    stop_listen_setting_changes(view)
                    view.settings[setting_name] = user_setting
                    listen_setting_changes(view)


            widget.set_view(view)
            dock = QT.QDockWidget(view_name)
            dock.setWidget(widget)
            # dock.visibilityChanged.connect(view.refresh)

            self.views[view_name] = view
            self.docks[view_name] = dock


    def create_main_layout(self):
        import warnings

        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyqtgraph")

        self.setDockNestingEnabled(True)

        preset = get_layout_description(self.layout_preset, self.layout)

        widgets_zone = {}
        for zone, view_names in preset.items():
            # keep only instantiated views
            view_names = [view_name for view_name in view_names if view_name in self.views.keys()]
            widgets_zone[zone] = view_names

        self.make_half_layout(widgets_zone, "left")
        self.make_half_layout(widgets_zone, "right")

        # make tabs
        for zone, view_names in widgets_zone.items():
            n = len(widgets_zone[zone])
            if n < 2:
                # no tab here
                continue
            view_name0 = widgets_zone[zone][0]
            for i in range(1, n):
                view_name = widgets_zone[zone][i]
                dock = self.docks[view_name]
                self.tabifyDockWidget(self.docks[view_name0], dock)
            # make visible the first of each zone
            self.docks[view_name0].raise_()

    def make_half_layout(self, widgets_zone, left_or_right):
        """
        Function contains the logic for the greedy layout. Given the 2x2 box of zones

        1 2          3 4   
        5 6    or    7 8

        Then depending on which zones are non-zero, a different layout is generated using splits.

        The zone indices in the second box (34,78) are equal to the zone indices first box (12,56) 
        shifted by 2. We take advantage of this fact.
        """

        shift = 0 if left_or_right == "left" else 2

        widgets_zone = fill_unnecessary_space(widgets_zone, shift)
        present_zones = get_present_zones_in_half_of_layout(widgets_zone, shift)

        if len(present_zones) == 0:
            return

        # The movements from earlier guarantee that the top-left zone is non-zero. Make this the initial zone
        view_name = widgets_zone[f"zone{1+shift}"][0]
        dock = self.docks[view_name]
        self.addDockWidget(areas[left_or_right], dock)

        # The main logic: apply splittings between different zones and in
        # different orders, depending on which zones are present.

        # Layouts with two non-zero zones
        if present_zones == set([f'zone{1+shift}', f'zone{2+shift}']):
            self.make_split(1,2,"horizontal", widgets_zone, shift)
        elif present_zones == set([f'zone{1+shift}', f'zone{5+shift}']):
            self.make_split(1,5,"vertical", widgets_zone, shift)
        elif present_zones == set([f'zone{1+shift}', f'zone{6+shift}']):
            self.make_split(1,6,"horizontal", widgets_zone, shift)

        # Layouts with three non-zero zones
        elif present_zones == set([f'zone{1+shift}', f'zone{2+shift}', f'zone{5+shift}']):
            self.make_split(1,2,"horizontal", widgets_zone, shift)
            self.make_split(1,5,"vertical", widgets_zone, shift)
        elif present_zones == set([f'zone{1+shift}', f'zone{2+shift}', f'zone{6+shift}']):
            self.make_split(1,2,"horizontal", widgets_zone, shift)
            self.make_split(2,6,"vertical", widgets_zone, shift)
        elif present_zones == set([f'zone{1+shift}', f'zone{5+shift}', f'zone{6+shift}']):
            self.make_split(1,5,"vertical", widgets_zone, shift)
            self.make_split(5,6,"horizontal", widgets_zone, shift)

        # Layout with four non-zero zones
        elif present_zones == set([f'zone{1+shift}', f'zone{2+shift}', f'zone{5+shift}', f'zone{6+shift}']):
            self.make_split(1,5,"vertical", widgets_zone, shift)
            self.make_split(1,2,"horizontal", widgets_zone, shift)
            self.make_split(5,6,"horizontal", widgets_zone, shift)

            
    def make_split(self, zone_index_1, zone_index_2, orientation, widgets_zone, shift):
        """
        Splits the zone at `zone_{zone_index_1+shift}` into two zones
        (`zone_{zone_index_1+shift}` and `zone_{zone_index_2+shift}`)
        with an `orientation` split.
        """
        widget_1 = widgets_zone[f"zone{zone_index_1+shift}"][0]
        widget_2 = widgets_zone[f"zone{zone_index_2+shift}"][0]
        self.splitDockWidget(self.docks[widget_1], self.docks[widget_2], orientations[orientation])

    # used by to tell the launcher this is closed
    def closeEvent(self, event):
        self.main_window_closed.emit(self)
        event.accept()


class ViewWidget(QT.QWidget):
    def __init__(self, view_class, parent=None):
        QT.QWidget.__init__(self, parent=parent)

        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(4,4,4,4)
        self.layout.setSpacing(4)

        tb = self.view_toolbar = QT.QToolBar()
        self.layout.addWidget(self.view_toolbar)

        tb.setStyleSheet(qt_style)

        if view_class._settings is not None:
            but = QT.QPushButton('⚙ settings')
            tb.addWidget(but)
            but.clicked.connect(self.open_settings)
            # but.setStyleSheet(qt_style)

        if view_class._need_compute:
            but = QT.QPushButton('compute')
            tb.addWidget(but)
            but.clicked.connect(self.compute)

        but = QT.QPushButton('↻ refresh')
        tb.addWidget(but)
        but.clicked.connect(self.refresh)
        
        but = QT.QPushButton('?')
        tb.addWidget(but)
        but.clicked.connect(self.open_help)
        tooltip_html = markdown.markdown(view_class._gui_help_txt)
        but.setToolTip(tooltip_html)

        add_stretch_to_qtoolbar(tb)

        # TODO: make _qt method for all existing methods that don't start with _qt or _panel
        # skip = ['__init__', 'set_view', 'open_settings', 'compute', 'refresh', 'open_help',
        #         'on_spike_selection_changed', 'on_unit_visibility_changed',
        #         'on_channel_visibility_changed', 'on_manual_curation_updated']
        # for name in dir(view_class):
        #     if name.startswith('_qt_') or name.startswith('_panel_') or name in skip:
        #         continue
        #     if hasattr(view_class, name):
        #         method = getattr(view_class, name)
        #         if callable(method):
        #             if name == "save_in_analyzer":
        #                 print(f'creating _qt_save_in_analyzer for {view_class}')
        #             setattr(view_class, '_qt_' + name, method)


    def set_view(self, view):
        self._view =  weakref.ref(view)
        if view._settings is not None:
            self.layout.addWidget(view.tree_settings)
            view.tree_settings.hide()

        self.layout.addLayout(view.layout)

    def open_settings(self):
        view = self._view()
        if not view.tree_settings.isVisible():
            view.tree_settings.show()
        else:
            view.tree_settings.hide()

    def compute(self):
        view = self._view()
        if view._need_compute:
            view.compute()
    
    def open_help(self):
        view = self._view()
        but = self.sender()
        txt = view._gui_help_txt
        txt = markdown.markdown(txt)
        QT.QToolTip.showText(but.mapToGlobal(QT.QPoint()), txt, but)
    
    def refresh(self):
        view = self._view()
        view.refresh()
        

areas = {
    'right' : QT.Qt.RightDockWidgetArea,
    'left' : QT.Qt.LeftDockWidgetArea,
}

orientations = {
    'horizontal' : QT.Qt.Horizontal,
    'vertical' : QT.Qt.Vertical,
}
