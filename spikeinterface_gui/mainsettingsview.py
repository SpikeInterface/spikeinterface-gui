from .view_base import ViewBase


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

    ## QT zone
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        txt = self.controller.get_information_txt()
        self.info_label = QT.QLabel(txt)
        self.layout.addWidget(self.info_label)

        self.main_settings = pg.parametertree.Parameter.create(name="main settings", type='group', children=main_settings)
        
        # not that the parent is not the view (not Qt anymore) itself but the widget
        self.tree_main_settings = pg.parametertree.ParameterTree(parent=self.qt_widget)
        self.tree_main_settings.header().hide()
        self.tree_main_settings.setParameters(self.main_settings, showTop=True)
        # self.tree_main_settings.setWindowTitle(u'Main settings')
        self.layout.addWidget(self.tree_main_settings)

        self.main_settings.param('max_visible_units').sigValueChanged.connect(self.on_max_visible_units_changed)
        self.main_settings.param('color_mode').sigValueChanged.connect(self.on_change_color_mode)


    def _qt_refresh(self):
        pass
    

    ## panel zone
    def _panel_make_layout(self):
        import panel as pn
        from .backend_panel import create_dynamic_parameterized, SettingsProxy

        # Create method and arguments layout
        self.main_settings = SettingsProxy(create_dynamic_parameterized(main_settings))
        self.main_settings_layout = pn.Param(self.main_settings._parameterized, sizing_mode="stretch_both", 
                                             name=f"Main settings")
        self.main_settings._parameterized.param.watch(self._panel_on_max_visible_units_changed, 'max_visible_units')
        self.main_settings._parameterized.param.watch(self._panel_on_change_color_mode, 'color_mode')
        self.layout = pn.Column(self.main_settings_layout, sizing_mode="stretch_both")

    def _panel_on_max_visible_units_changed(self, event):
        self.on_max_visible_units_changed()

    def _panel_on_change_color_mode(self, event):
        self.on_change_color_mode()

    def _panel_refresh(self):
        pass


MainSettingsView._gui_help_txt = """
## Main settings

Overview and main controls 
"""