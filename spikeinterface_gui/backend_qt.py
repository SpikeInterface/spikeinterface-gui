from .myqt import QT
import pyqtgraph as pg
import markdown


import weakref

from .viewlist import possible_class_views
from .layout_presets import get_layout_description, get_size_bottom_row, get_size_top_row

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


class QtMainWindow(QT.QMainWindow):
    main_window_closed = QT.pyqtSignal(object)

    def __init__(self, controller, parent=None, layout_preset=None, layout=None, screenshot_name=""):
        QT.QMainWindow.__init__(self, parent)
        
        self.controller = controller
        self.verbose = controller.verbose
        self.layout_preset = layout_preset
        self.layout = layout
        self.make_views()
        self.create_main_layout()

        # refresh all views wihtout notiying
        self.controller.signal_handler.deactivate()
        for view in self.views.values():
            # refresh do not work because view are not yet visible at init
            view._refresh()
        self.controller.signal_handler.activate()

        self.screenshot_name = screenshot_name
        #QT.QTimer.singleShot(200, self.saveScreenshot)

    def saveScreenshot(self):

        screen = QT.QApplication.primaryScreen()
        screenshot = screen.grabWindow( self.winId() )
        screenshot.save(self.screenshot_name, 'jpg')

        # TODO sam : all veiws are always refreshed at the moment so this is useless.
        # uncommen this when ViewBase.is_view_visible() work correctly
        # for view_name, dock in self.docks.items():
        #     dock.visibilityChanged.connect(self.views[view_name].refresh)

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

            if view_name in ("trace", "tracemap") and not self.controller.with_traces:
                continue

            widget = ViewWidget(view_class)
            view = view_class(controller=self.controller, parent=widget, backend='qt')
            widget.set_view(view)
            dock = QT.QDockWidget(view_name)
            dock.setWidget(widget)
            # dock.visibilityChanged.connect(view.refresh)

            self.views[view_name] = view
            self.docks[view_name] = dock


    def create_main_layout(self):
        """
        We rely on PyQt docks so that the user can adjust the size of each widget. These
        are made iteratively by splitting an existing dock. The algorithm to create the 
        splits based on our layout dict is in three steps. It is complicated, so we provide
        an example. Let's "*" represent a zone with something in it and "o" a zone without.
        Consider the example

        1 2 3 4
        * * o *
        * o * *

        First, we determine which columns should be two rows long. Then split the docks
        around these. In this case, only column 2 should be long. So the split is

        1   2   3 4
        * | * | o *
        * | o | * *

        Next, for each sub-region, we split vertically. The second column cannot be split.

        1   2   3 4
        * | * | o *
        -       - -
        * | o | * *

        Finally, in each sub-sub-region, we check how many times we need to split horizontally.
        Here the lower 3/4 row can be split

        1   2   3   4
        * | * | o   *
        -       -   -
        * | o | * | *

        Each final region contains exactly one zone. All of our possible layouts can be split up
        in this way.
        """
        import warnings

        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyqtgraph")

        self.setDockNestingEnabled(True)

        preset = get_layout_description(self.layout_preset, self.layout)

        widgets_zone = {}
        for zone, view_names in preset.items():
            # keep only instantiated views
            view_names = [view_name for view_name in view_names if view_name in self.views.keys()]
            widgets_zone[zone] = view_names

        import numpy as np
        from copy import copy

        all_zones = [f'zone{a}' for a in range(1,9)]
        all_zones_array = np.transpose(np.reshape(all_zones, (2,4)))
        is_zone = np.array([(widgets_zone.get(zone) is not None) and (len(widgets_zone.get(zone)) > 0) for zone in all_zones])
        is_zone_array = np.reshape(is_zone, (2,4))
        original_zone_array = copy(is_zone_array)

        first_nonzero_column = np.arange(4)[np.any(original_zone_array, axis=0)][0]
        first_is_top = original_zone_array[:,first_nonzero_column][0]
        if not first_is_top:
            top_zone = f"zone{first_nonzero_column+1}"
            bottom_zone = f"zone{first_nonzero_column+5}"
            widgets_zone[top_zone] = widgets_zone[bottom_zone]
            widgets_zone[bottom_zone] = []

        is_zone = np.array([(widgets_zone.get(zone) is not None) and (len(widgets_zone.get(zone)) > 0) for zone in all_zones])
        is_zone_array = np.reshape(is_zone, (2,4))
        original_zone_array = copy(is_zone_array)

        num_rows_1, num_cols_1 = get_size_top_row(0,0, is_zone_array, original_zone_array)
        num_rows_2, num_cols_2 = get_size_top_row(0,1, is_zone_array, original_zone_array)
        num_rows_3, num_cols_3 = get_size_top_row(0,2, is_zone_array, original_zone_array)
        num_rows_4, num_cols_4 = get_size_top_row(0,3, is_zone_array, original_zone_array)

        num_rows_5, num_cols_5 = get_size_bottom_row(1,0, is_zone_array, original_zone_array)
        num_rows_6, num_cols_6 = get_size_bottom_row(1,1, is_zone_array, original_zone_array)
        num_rows_7, num_cols_7 = get_size_bottom_row(1,2, is_zone_array, original_zone_array)
        num_rows_8, num_cols_8 = get_size_bottom_row(1,3, is_zone_array, original_zone_array)

        num_rows = np.array([num_rows_1, num_rows_2, num_rows_3, num_rows_4, num_rows_5, num_rows_6, num_rows_7, num_rows_8])
        num_cols = np.array([num_cols_1, num_cols_2, num_cols_3, num_cols_4, num_cols_5, num_cols_6, num_cols_7, num_cols_8])

        num_rows_array = np.reshape(num_rows, (2,4))
        num_cols_array = np.reshape(num_cols, (2,4))

        group = []
        all_groups = []
        for num_row, num_col, is_a_zone, zones in zip(np.transpose(num_rows_array), np.transpose(num_cols_array), np.transpose(original_zone_array), all_zones_array):
            if num_row[0] == 2:
                if len(group) > 0:
                    all_groups.append(group)
                group = []
                allowed_zones = zones[is_a_zone]
                all_groups.append(allowed_zones)
            else:
                for zone in zones[is_a_zone]:
                    group.append(zone)

        if len(group) > 0:
            all_groups.append(group)

        first_dock = None
        print(f"{all_groups}")
        first_zone = all_groups[0][0]
        print(f"{first_zone=}")
        if first_zone in ['zone5', 'zone6', 'zone7', 'zone8']:
            above_zone = f'zone{int(first_zone[-1])-4}'
            widgets_zone[above_zone] = widgets_zone[first_zone]
            first_zone = above_zone
        first_dock = widgets_zone[first_zone][0]
        dock = self.docks[first_dock]
        self.addDockWidget(areas['left'], dock)

        for group in reversed(all_groups[1:]):             
            digits = np.array([int(s[-1]) for s in group])
            sorted_indices = np.argsort(digits)
            sorted_arr = np.array(group)[sorted_indices]
            view_name = widgets_zone[sorted_arr[0]][0]
            dock = self.docks[view_name]
            print(f"Splitting {first_dock}, {view_name}")
            self.splitDockWidget(self.docks[first_dock], dock, orientations['horizontal'])

        new_all_groups = []
        for group in all_groups:
            if len(group) == 1:
                continue
            else:
                top_zones = [zone for zone in group if zone in ['zone1', 'zone2', 'zone3', 'zone4']]
                bottom_zones = [zone for zone in group if zone in ['zone5', 'zone6', 'zone7', 'zone8']]
                new_all_groups.append([top_zones, bottom_zones])

        for top_and_bottom_groups in new_all_groups:

            top_groups, bottom_groups = top_and_bottom_groups

            if len(top_groups) > 0 and len(bottom_groups) > 0:

                top_view_name = widgets_zone[top_groups[0]][0]
                top_dock = self.docks[top_view_name]

                bottom_view_name = widgets_zone[bottom_groups[0]][0]
                bottom_dock = self.docks[bottom_view_name]

                print(f"Splitting {top_view_name}, {bottom_view_name}")
                self.splitDockWidget(top_dock, bottom_dock, orientations['vertical'])

        for top_bottom_groups in new_all_groups:
            for group in top_bottom_groups:
                if len(group) <= 1:
                    continue
                else:
                    first_zone_name = widgets_zone[group[0]][0]
                    
                    for zone in reversed(group[1:]):
                        zone_name = widgets_zone[zone][0]
                        print(f"Splitting {first_zone_name}, {zone_name}")
                        self.splitDockWidget(self.docks[first_zone_name], self.docks[zone_name], orientations['horizontal'])

        # ## Handle left
        # first_left = None
        # for zone in ['zone1', 'zone5', 'zone2',  'zone6']:
        #     if len(widgets_zone[zone]) == 0:
        #         continue
        #     view_name = widgets_zone[zone][0]
        #     dock = self.docks[view_name]
        #     if len(widgets_zone[zone]) > 0 and first_left is None:
        #         self.addDockWidget(areas['left'], dock)
        #         first_left = view_name
        #     elif zone == 'zone5':
        #         self.splitDockWidget(self.docks[first_left], dock, orientations['vertical'])
        #     elif zone == 'zone2':
        #         self.splitDockWidget(self.docks[first_left], dock, orientations['horizontal'])
        #     elif zone == 'zone6':
        #         if len(widgets_zone['zone5']) > 0:
        #             z = widgets_zone['zone5'][0]
        #             self.splitDockWidget(self.docks[z], dock, orientations['horizontal'])
        #         else:
        #             self.splitDockWidget(self.docks[first_left], dock, orientations['vertical'])

        # ## Handle right
        # first_top = None
        # for zone in ['zone3', 'zone4', 'zone7',  'zone8']:
        #     if len(widgets_zone[zone]) == 0:
        #         continue
        #     view_name = widgets_zone[zone][0]
        #     dock = self.docks[view_name]
        #     if len(widgets_zone[zone]) > 0 and first_top is None:
        #         self.addDockWidget(areas['right'], dock)
        #         first_top = view_name
        #     elif zone == 'zone4':
        #         self.splitDockWidget(self.docks[first_top], dock, orientations['horizontal'])
        #     elif zone == 'zone7':
        #         self.splitDockWidget(self.docks[first_top], dock, orientations['vertical'])
        #     elif zone == 'zone8':
        #         if len(widgets_zone['zone4']) > 0:
        #             z = widgets_zone['zone4'][0]
        #             self.splitDockWidget(self.docks[z], dock, orientations['vertical'])
        #         else:
        #             self.splitDockWidget(self.docks[first_top], dock, orientations['horizontal'])
        
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
