from .view_base import ViewBase
from .utils_global import get_config_folder
import json
import spikeinterface_gui

# this control controller.main_settings
main_settings = [
    {'name': 'max_visible_units', 'type': 'int', 'value' : 10 },
    {'name': 'color_mode', 'type': 'list', 'value' : 'color_by_unit',
             'limits': ['color_by_unit', 'color_only_visible', 'color_by_visibility']},
]


class MainSettingsView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _settings = None
    _depend_on = []
    _need_compute = False

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)


    def on_max_visible_units_changed(self):
        max_visible = self.main_settings['max_visible_units']
        self.controller.main_settings['max_visible_units'] = max_visible

        visible_ids = self.controller.get_visible_unit_ids()
        if len(visible_ids) > max_visible:
            visible_ids = visible_ids[:max_visible]
            self.controller.set_visible_unit_ids(visible_ids)
            self.notify_unit_visibility_changed()
    
    def on_change_color_mode(self):
        
        self.controller.main_settings['color_mode'] = self.main_settings['color_mode']
        self.controller.refresh_colors()
        self.notify_unit_color_changed()

        # for view in self.controller.views:
        #     view.refresh()

    def save_current_settings(self, event=None):
        
        backend = self.controller.backend

        settings_dict = {}
        for view in self.controller.views:

            # If view does not have any settings (e.g. MergeView) then skip
            if view._settings is None:
                continue

            view_class_name = view.__class__.__name__
            view_name = view_class_name.replace("View", "").lower()

            settings_dict[view_name] = {}

            if backend == "panel":
                settings_dict[view_name] = self.panel_make_settings_dict(view)
            elif backend == "qt":
                settings_dict[view_name] = self.qt_make_settings_dict(view)
            
        config_folder = get_config_folder()
        if not config_folder.is_dir():
            config_folder.mkdir(exist_ok=True)

        settings_dict['_metadata'] = {}
        settings_dict["_metadata"]["sigui_version"] = spikeinterface_gui.__version__

        with open(config_folder / 'settings.json', 'w') as f:
            json.dump(settings_dict, f)

    ## QT zone
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        txt = self.controller.get_information_txt()
        self.info_label = QT.QLabel(txt)
        self.layout.addWidget(self.info_label)

        if not self.controller.disable_save_settings_button:
            but = QT.QPushButton('Save as default settings')
            but.clicked.connect(self.save_current_settings)
            self.layout.addWidget(but)

        self.main_settings = pg.parametertree.Parameter.create(name="main settings", type='group', children=main_settings)
        
        # not that the parent is not the view (not Qt anymore) itself but the widget
        self.tree_main_settings = pg.parametertree.ParameterTree(parent=self.qt_widget)
        self.tree_main_settings.header().hide()
        self.tree_main_settings.setParameters(self.main_settings, showTop=True)
        # self.tree_main_settings.setWindowTitle(u'Main settings')
        self.layout.addWidget(self.tree_main_settings)

        self.main_settings.param('max_visible_units').sigValueChanged.connect(self.on_max_visible_units_changed)
        self.main_settings.param('color_mode').sigValueChanged.connect(self.on_change_color_mode)

    def qt_make_settings_dict(self, view):
        """For a given view, return the current settings in a dict"""

        current_settings_dict_from_view = view.settings.getValues()
        
        current_settings_dict = {}    
        for setting_name, (setting_value, _) in current_settings_dict_from_view.items():           
            current_settings_dict[setting_name] = setting_value
        
        return current_settings_dict
        

    def _qt_refresh(self):
        pass
    

    ## panel zone
    def _panel_make_layout(self):
        import panel as pn
        from .backend_panel import create_dynamic_parameterized, SettingsProxy

        if self.controller.disable_save_settings_button:
            self.save_setting_button = None
        else:
            self.save_setting_button = pn.widgets.Button(name="Save as default settings", button_type="primary", sizing_mode="stretch_width")
            self.save_setting_button.on_click(self.save_current_settings)

        # Create method and arguments layout
        self.main_settings = SettingsProxy(create_dynamic_parameterized(main_settings))
        self.main_settings_layout = pn.Param(self.main_settings._parameterized, sizing_mode="stretch_both", 
                                             name=f"Main settings")
        self.main_settings._parameterized.param.watch(self._panel_on_max_visible_units_changed, 'max_visible_units')
        self.main_settings._parameterized.param.watch(self._panel_on_change_color_mode, 'color_mode')
        self.layout = pn.Column(self.save_setting_button, self.main_settings_layout, sizing_mode="stretch_both")

    def panel_make_settings_dict(self, view):
        """For a given view, return the current settings in a dict"""

        current_settings_dict_from_param = view.settings._parameterized.param.values()
        current_settings_dict = {}
        for setting_name, setting_value in current_settings_dict_from_param.items():
            # The param also saves the name of the view - we don't want to propagate this
            if setting_name != "name":           
                current_settings_dict[setting_name] = setting_value
        return current_settings_dict

    def _panel_on_max_visible_units_changed(self, event):
        self.on_max_visible_units_changed()

    def _panel_on_change_color_mode(self, event):
        self.on_change_color_mode()

    def _panel_refresh(self):
        pass


MainSettingsView._gui_help_txt = """
## Main settings

Overview and main controls.
Can save current settings for entire GUI as the default user settings using the "Save as default settings" button.
"""