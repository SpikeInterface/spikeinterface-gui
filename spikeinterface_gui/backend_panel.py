import param
import panel as pn


from .viewlist import possible_class_views
from .layout_presets import get_layout_description

# Used by views to emit/trigger signals
class SignalNotifyer(param.Parameterized):
    spike_selection_changed = param.Event()
    unit_visibility_changed = param.Event()
    channel_visibility_changed = param.Event()
    manual_curation_updated = param.Event()

    def __init__(self):
        param.Parameterized.__init__(self)

    def notify_spike_selection_changed(self):
        self.param.trigger("spike_selection_changed")

    def notify_unit_visibility_changed(self):
        self.param.trigger("unit_visibility_changed")

    def notify_channel_visibility_changed(self):
        self.param.trigger("channel_visibility_changed")

    def notify_manual_curation_updated(self):
        self.param.trigger("manual_curation_updated")



class SignalHandler(param.Parameterized):
    def __init__(self, controller, parent=None):
        param.Parameterized.__init__(self)
        self.controller = controller
        self._active = True
    
    def activate(self):
        self._active = True

    def deactivate(self):
        self._active = False
        

    def connect_view(self, view):
        view.notifyer.param.watch(self.on_spike_selection_changed, "spike_selection_changed")
        view.notifyer.param.watch(self.on_unit_visibility_changed, "unit_visibility_changed")
        view.notifyer.param.watch(self.on_channel_visibility_changed, "channel_visibility_changed")
        view.notifyer.param.watch(self.on_manual_curation_updated, "manual_curation_updated")

    def on_spike_selection_changed(self, param):
        if not self._active:
            return

        for view in self.controller.views:
            # Alessio : how do you avoid callback on the own view ? 
            # if view==self.sender(): continue
            view.on_spike_selection_changed()

    def on_unit_visibility_changed(self, param):
        if not self._active:
            return
        for view in self.controller.views:
            # Alessio : how do you avoid callback on the own view ? 
            # if view==self.sender(): continue
            view.on_unit_visibility_changed()

    def on_channel_visibility_changed(self, param):
        if not self._active:
            return
        for view in self.controller.views:
            # Alessio : how do you avoid callback on the own view ? 
            # if view==self.sender(): continue
            view.on_channel_visibility_changed()


    def on_manual_curation_updated(self, param):
        if not self._active:
            return
        for view in self.controller.views:
            # Alessio : how do you avoid callback on the own view ? 
            # if view == self.sender(): continue
            view.on_manual_curation_updated()



param_type_map = {
    "float": param.Number,
    "int": param.Integer,
    "bool": param.Boolean,
    "list": param.ObjectSelector,
}

class SettingsProxy:
    # this make the setting dict like (to mimic pyqtgraph)
    # for instance self.settings['my_params'] instead of self.settings.my_params
    # self.settings['my_params'] = value instead of self.settings.my_params = value
    def __init__(self, myparametrized):
        self._parametrized = myparametrized
    
    def __getitem__(self,key):
        return getattr(self._parametrized, key)
    
    def __setitem__(self, key, value):
        self._parametrized.param.update(**{key:value})

def create_settings(view):
    # Create the class attributes dynamically
    attributes = {}
    for setting_data in view._settings:
        if setting_data["type"] == "list":
            if "value" in setting_data:
                default = setting_data["value"]
            else:
                default = setting_data["limits"][0]
            attributes[setting_data["name"]] = param_type_map[setting_data["type"]](
                objects=setting_data["limits"], doc=f"{setting_data['name']} parameter", default=default
            )
        elif "value" in setting_data:
            attributes[setting_data["name"]] = param_type_map[setting_data["type"]](
                setting_data["value"], doc=f"{setting_data['name']} parameter"
            )
    MyParameterized = type("MyParameterized", (param.Parameterized,), attributes)

    view.settings = SettingsProxy(MyParameterized())

def listen_setting_changes(view):
    for setting_data in view._settings:
        view.settings._parametrized.param.watch(view.on_settings_changed, setting_data["name"])




class PanelMainWindow:

    def __init__(self, controller, layout_preset=None):
        self.controller = controller
        self.layout_preset = layout_preset
        self.verbose = controller.verbose

        self.make_views()
        self.create_main_layout()
        
        # refresh all views wihtout notiying
        self.controller.signal_handler.deactivate()
        for view in self.views.values():
            view.refresh()
        self.controller.signal_handler.activate()

    def make_views(self):
        self.views = {}
        # this contains view layout + settings
        self.view_layouts = {}
        for view_name, view_class in possible_class_views.items():
            if 'panel' not in view_class._supported_backend:
                continue
            if not self.controller.check_is_view_possible(view_name):
                continue

            view = view_class(controller=self.controller, parent=None, backend='panel')
            self.views[view_name] = view

            if view_class._settings is not None:
                settings_panel = pn.Card(
                    pn.Param(view.settings._parametrized, name="Settings", show_name=True),
                    collapsed=True,
                    styles={"flex": "0.1"}
                )
                items = (
                    settings_panel,
                    view.layout,
                )
            else:
                items = (
                    view.layout,
                )

            view_layout = pn.Column(
                *items,
                styles={"display": "flex", "flex-direction": "column"},
                sizing_mode="stretch_both"
            )
            self.view_layouts[view_name] = view_layout


    def create_main_layout(self):
        
        preset = get_layout_description(self.layout_preset)

        layout_zone = {}
        for zone, view_names in preset.items():
            # keep only instanciated views
            view_names = [view_name for view_name in view_names if view_name in self.view_layouts.keys()]

            if len(view_names) == 0:
                layout_zone[zone] = None
            elif len(view_names) == 1:
                # unique in the zone
                layout_zone[zone] = self.view_layouts[view_names[0]]
            else:
                 layout_zone[zone] = pn.Tabs(
                    *((view_name, self.view_layouts[view_name]) for view_name in view_names if view_name in self.view_layouts),
                    sizing_mode="stretch_both",
                    dynamic=True,
                    tabs_location="above",
                )

        left = pn.Column(
            pn.Row(
                *(layout_zone[zone] for zone in ('zone1', 'zone2') if layout_zone[zone] is not None),
            ),
            pn.Row(
                *(layout_zone[zone] for zone in ('zone5', 'zone6') if layout_zone[zone] is not None),
            ),
            sizing_mode="stretch_both",
        )

        right = pn.Column(
            pn.Row(
                *(layout_zone[zone] for zone in ('zone3', 'zone4') if layout_zone[zone] is not None),
            ),
            pn.Row(
                *(layout_zone[zone] for zone in ('zone7', 'zone8') if layout_zone[zone] is not None),
            ),
            sizing_mode="stretch_both",
        )

        self.main_layout = pn.Row(
            left,
            right,
            sizing_mode="stretch_both",
        )


def start_server(mainwindow, address="localhost", port=0):

    pn.config.sizing_mode = "stretch_width"
    pn.extension("bokeh")

    # logging.basicConfig(level=logging.DEBUG)
    pn.extension("modal", sizing_mode="stretch_width")

    mainwindow.main_layout.servable()

    server = pn.serve({"/": mainwindow.main_layout}, address=address, port=port,
                      show=False, start=True, dev=True,  autoreload=True)

    return server
