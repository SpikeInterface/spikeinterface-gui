import param
import panel as pn


from .viewlist import possible_class_views
from .layout_presets import get_layout_description

# Used by views to emit/trigger signals
class SignalNotifier(param.Parameterized):
    spike_selection_changed = param.Event()
    unit_visibility_changed = param.Event()
    channel_visibility_changed = param.Event()
    manual_curation_updated = param.Event()

    def __init__(self, view=None):
        param.Parameterized.__init__(self)
        self.view = view

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
        view.notifier.param.watch(self.on_spike_selection_changed, "spike_selection_changed")
        view.notifier.param.watch(self.on_unit_visibility_changed, "unit_visibility_changed")
        view.notifier.param.watch(self.on_channel_visibility_changed, "channel_visibility_changed")
        view.notifier.param.watch(self.on_manual_curation_updated, "manual_curation_updated")

    def on_spike_selection_changed(self, param):
        if not self._active:
            return

        for view in self.controller.views:
            if param.obj.view == view:
                continue
            view.on_spike_selection_changed()

    def on_unit_visibility_changed(self, param):
        if not self._active:
            return
        for view in self.controller.views:
            if param.obj.view == view:
                continue
            view.on_unit_visibility_changed()

    def on_channel_visibility_changed(self, param):
        if not self._active:
            return
        for view in self.controller.views:
            if param.obj.view == view:
                continue
            view.on_channel_visibility_changed()


    def on_manual_curation_updated(self, param):
        if not self._active:
            return
        for view in self.controller.views:
            if param.obj.view == view:
                continue
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
    
    def __getitem__(self, key):
        return getattr(self._parametrized, key)
    
    def __setitem__(self, key, value):
        self._parametrized.param.update(**{key:value})

    def keys(self):
        return list(p for p in self._parametrized.param if p != "name")

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
                settings = pn.Param(view.settings._parametrized, sizing_mode="stretch_height", name="")
                view_layout = pn.Tabs(
                    ("View", view.layout), 
                    ("⚙️", settings),
                    sizing_mode="stretch_both",
                    dynamic=True,
                    tabs_location="above",
                )
            else:
                view_layout = pn.Column(
                    view.layout,
                    styles={"display": "flex", "flex-direction": "column"},
                )
            self.view_layouts[view_name] = view_layout


    def create_main_layout(self):

        pn.extension("gridstack")

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
                    tabs_location="below",
                )

        # Create GridStack layout with resizable regions
        grid_per_zone = 4
        gs = pn.GridStack(
            sizing_mode='stretch_both',
            allow_resize=True,
            allow_drag=False,
            ncols=4 * grid_per_zone,
            nrows=4 * grid_per_zone,
        )

        # Add the zones to the gridstack layout
        # Left side
        for zone in ['zone1', 'zone2', 'zone5', 'zone6']:
            view = layout_zone[zone]
            if zone in ['zone1', 'zone2']:
                col_slice = slice(0, 2 * grid_per_zone)
            else:
                col_slice = slice(2 * grid_per_zone, 4 * grid_per_zone)
            if zone == 'zone1':
                if layout_zone.get('zone2') is None or len(layout_zone['zone2']) == 0:
                    # zone1 and zone2 are merged
                    row_slice = slice(0, 2*grid_per_zone)
                else:
                    # zone1 and zone2 are not merged
                    row_slice = slice(0, grid_per_zone)
            elif zone == 'zone2':
                if layout_zone.get('zone1') is None or len(layout_zone['zone1']) == 0:
                    # zone1 and zone2 are merged
                    row_slice = slice(0, 2*grid_per_zone)
                else:
                    # zone1 and zone2 are not merged
                    row_slice = slice(grid_per_zone, 2*grid_per_zone)
            elif zone == 'zone5':
                if layout_zone.get('zone6') is None or len(layout_zone['zone6']) == 0:
                    # zone5 and zone6 are merged
                    row_slice = slice(0, 2*grid_per_zone)
                else:
                    # zone5 and zone6 are not merged
                    row_slice = slice(0, grid_per_zone)
            elif zone == 'zone6':
                if layout_zone.get('zone5') is None or len(layout_zone['zone5']) == 0:
                    # zone5 and zone6 are merged
                    row_slice = slice(0, 2*grid_per_zone)
                else:
                    # zone5 and zone6 are not merged
                    row_slice = slice(grid_per_zone, 2*grid_per_zone)
            if view is not None  and len(view) > 0:
                gs[col_slice, row_slice] = view
                print(row_slice, col_slice, zone)
            else:
                print('no view', zone)
            gs[col_slice, row_slice] = view

        # Right side
        for zone in ['zone3', 'zone4', 'zone7', 'zone8']:
            view = layout_zone[zone]
            if zone in ['zone3', 'zone4']:
                col_slice = slice(0, 2 * grid_per_zone)
            else:
                col_slice = slice(2 * grid_per_zone, 4 * grid_per_zone)
            if zone == 'zone3':
                if layout_zone.get('zone4') is None or len(layout_zone['zone4']) == 0:
                    # zone3 and zone4 are merged
                    row_slice = slice(2*grid_per_zone, 4*grid_per_zone)
                else:
                    # zone3 and zone4 are not merged
                    row_slice = slice(2*grid_per_zone, 3*grid_per_zone)
            elif zone == 'zone4':
                if layout_zone.get('zone3') is None or len(layout_zone['zone3']) == 0:
                    # zone3 and zone4 are merged
                    row_slice = slice(2*grid_per_zone, 4*grid_per_zone)
                else:
                    # zone3 and zone4 are not merged
                    row_slice = slice(3*grid_per_zone, 4*grid_per_zone)
            elif zone == 'zone7':
                if layout_zone.get('zone8') is None or len(layout_zone['zone8']) == 0:
                    # zone7 and zone8 are merged
                    row_slice = slice(2*grid_per_zone, 4*grid_per_zone)
                else:
                    # zone7 and zone8 are not merged
                    row_slice = slice(2*grid_per_zone, 3*grid_per_zone)
            elif zone == 'zone8':
                if layout_zone.get('zone7') is None or len(layout_zone['zone7']) == 0:
                    # zone7 and zone8 are merged
                    row_slice = slice(2*grid_per_zone, 4*grid_per_zone)
                else:
                    # zone7 and zone8 are not merged
                    row_slice = slice(3*grid_per_zone, 4*grid_per_zone)
            if view is not None  and len(view) > 0:
                gs[col_slice, row_slice] = view
                print(row_slice, col_slice, zone)
            else:
                print('no view', zone)
        self.main_layout = gs


def start_server(mainwindow, address="localhost", port=0):

    pn.config.sizing_mode = "stretch_width"
    
    # Enable bokeh and other required extensions
    pn.extension("bokeh", "design", sizing_mode="stretch_width")

    mainwindow.main_layout.servable()

    server = pn.serve({"/": mainwindow.main_layout}, address=address, port=port,
                      show=False, start=True, dev=True,  autoreload=True)

    return server
