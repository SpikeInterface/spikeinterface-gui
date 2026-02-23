import param
import panel as pn
import numpy as np
from copy import copy

from .viewlist import get_all_possible_views
from .layout_presets import get_layout_description
from .utils_global import fill_unnecessary_space, get_present_zones_in_half_of_layout
# Used by views to emit/trigger signals
class SignalNotifier(param.Parameterized):
    spike_selection_changed = param.Event()
    unit_visibility_changed = param.Event()
    channel_visibility_changed = param.Event()
    manual_curation_updated = param.Event()
    time_info_updated = param.Event()
    use_times_updated = param.Event()
    active_view_updated = param.Event()
    unit_color_changed = param.Event()

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

    def notify_time_info_updated(self):
        self.param.trigger("time_info_updated")

    def notify_use_times_updated(self):
        self.param.trigger("use_times_updated")

    def notify_active_view_updated(self):
        # this is used to keep an "active view" in the main window
        # when a view triggers this event, it self-declares it as active
        # and the other windows will be set as non-active
        # this is used in panel to be able to use the same shortcuts in multiple
        # views
        self.param.trigger("active_view_updated")

    def notify_unit_color_changed(self):
        self.param.trigger("unit_color_changed")


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
        view.notifier.param.watch(self.on_time_info_updated, "time_info_updated")
        view.notifier.param.watch(self.on_use_times_updated, "use_times_updated")
        view.notifier.param.watch(self.on_active_view_updated, "active_view_updated")
        view.notifier.param.watch(self.on_unit_color_changed, "unit_color_changed")

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

    def on_time_info_updated(self, param):
        # time info is updated also when a view is not active
        if not self._active:
            return
        for view in self.controller.views:
            if param.obj.view == view:
                continue
            view.on_time_info_updated()

    def on_use_times_updated(self, param):
        # use times is updated also when a view is not active
        if not self._active:
            return
        for view in self.controller.views:
            if param.obj.view == view:
                continue
            view.on_use_times_updated()

    def on_active_view_updated(self, param):
        if not self._active:
            return
        for view in self.controller.views:
            if param.obj.view == view:
                view._panel_view_is_active = True
            else:
                view._panel_view_is_active = False
    
    def on_unit_color_changed(self, param):
        if not self._active:
            return
        for view in self.controller.views:
            if param.obj.view == view:
                continue
            view.on_unit_color_changed()

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
        self._parameterized = myparametrized
    
    def __getitem__(self, key):
        return getattr(self._parameterized, key)
    
    def __setitem__(self, key, value):
        self._parameterized.param.update(**{key:value})

    def keys(self):
        return list(p for p in self._parameterized.param if p != "name")


def create_dynamic_parameterized(settings):
    """
    Create a dynamic parameterized class based on the settings provided.
    """
    attributes = {}
    for setting_data in settings:
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
    return MyParameterized()


def create_settings(view):
    # Create the class attributes dynamically
    settings = create_dynamic_parameterized(view._settings)

    view.settings = SettingsProxy(settings)

def listen_setting_changes(view):
    for setting_data in view._settings:
        view.settings._parameterized.param.watch(view.on_settings_changed, setting_data["name"])

class PanelMainWindow:

    def __init__(self, controller, layout_dict=None, user_settings=None):
        self.controller = controller
        self.layout_dict = layout_dict
        self.verbose = controller.verbose

        self.make_views(user_settings)
        self.create_main_layout()
        
        # refresh all views wihtout notiying
        self.controller.signal_handler.deactivate()
        self.controller.signal_handler.activate()

        for view in self.views.values():
            if view.is_view_visible():
                view.refresh()

    def make_views(self, user_settings):
        self.views = {}
        # this contains view layout + settings + compute
        self.view_layouts = {}
        requested_views = []
        for _, view_names in self.layout_dict.items():
            requested_views.extend(view_names)
        requested_views = set(requested_views)
        possible_class_views = get_all_possible_views()
        for view_name, view_class in possible_class_views.items():
            if 'panel' not in view_class._supported_backend:
                continue
            if not self.controller.check_is_view_possible(view_name):
                continue
            if view_name not in requested_views:
                continue

            if view_name == 'curation' and not self.controller.curation:
                continue

            if view_name in ("trace", "tracemap") and not self.controller.with_traces:
                continue


            info = pn.Column(
                pn.pane.Markdown(view_class._gui_help_txt),
                scroll=True,
                sizing_mode="stretch_both"
            )

            if user_settings is not None and user_settings.get(view_name) is not None:
                for setting_name, user_setting in user_settings.get(view_name).items():
                    available_settings = [s["name"] for s in view_class._settings]
                    if setting_name not in available_settings:
                        raise KeyError(f"Setting {setting_name} is not a valid setting for View {view_name}. Check your settings file.")
                    settings_index = available_settings.index(setting_name)
                    view_class._settings[settings_index]["value"] = user_setting

            view = view_class(controller=self.controller, parent=None, backend='panel')
            self.views[view_name] = view

            tabs = [("📊", view.layout)]
            if view_class._settings is not None:
                settings = pn.Param(view.settings._parameterized, sizing_mode="stretch_height", 
                                    name=f"{view_name.capitalize()} settings")
                if view_class._need_compute:
                    compute_button = pn.widgets.Button(name="Compute", button_type="primary")
                    compute_button.on_click(view.compute)
                    settings = pn.Row(settings, compute_button)
                tabs.append(("⚙️", settings))

            tabs.append(("ℹ️", info))
            view_layout = pn.Tabs(
                *tabs,
                sizing_mode="stretch_both",
                dynamic=True,
                tabs_location="left",
            )
            self.view_layouts[view_name] = view_layout


    def create_main_layout(self):
        from .utils_panel import KeyboardShortcut, KeyboardShortcuts

        pn.extension("gridstack")

        preset = self.layout_dict

        layout_zone = {}
        self.all_tabs = []
        for zone, view_names in preset.items():
            # keep only instanciated views
            view_names = [view_name for view_name in view_names if view_name in self.view_layouts.keys()]

            if len(view_names) == 0:
                layout_zone[zone] = []
            else:
                layout_zone[zone] = pn.Tabs(
                    *((view_name, self.view_layouts[view_name]) for view_name in view_names if view_name in self.view_layouts),
                    sizing_mode="stretch_both",
                    dynamic=True,
                    tabs_location="below",
                )
                # Function to update visibility
                tabs = layout_zone[zone]
                tabs.param.watch(self.update_visibility, "active")
                self.all_tabs.append(tabs)
                # Simulate an event
                self.update_visibility(
                    param.parameterized.Event(
                        cls=None, what="value", type="changed", old=0, new=0, obj=tabs, name="active",
                    )
                )

        # Create GridStack layout with resizable regions
        gs = pn.GridStack(
            sizing_mode='stretch_both',
            allow_resize=False,
            allow_drag=False,
        )

        gs = self.make_half_layout(gs, layout_zone, "left")
        gs = self.make_half_layout(gs, layout_zone, "right")

        # Initialize keyboard shortcuts
        self.focus_mode = False
        shortcuts = [KeyboardShortcut(name="focus", key="f", ctrlKey=True),]
        shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        shortcuts_component.on_msg(self._handle_shortcut)

        self.main_layout = pn.Column(
            gs,
            shortcuts_component,
            sizing_mode="stretch_both",
        )

    def make_half_layout(self, gs, layout_zone, left_or_right):
        """
        Function contains the logic for the greedy layout. Given the 2x2 box of zones

        1 2          3 4   
        5 6    or    7 8

        Then depending on which zones are non-zero, a different layout is generated using splits.

        The zone indices in the second box (34,78) are equal to the zone indices first box (12,56) 
        shifted by 2. We take advantage of this fact.
        """

        shift = 0 if left_or_right == "left" else 2

        layout_zone = fill_unnecessary_space(layout_zone, shift)
        present_zones = get_present_zones_in_half_of_layout(layout_zone, shift)

        # `fill_unnecessary_space` ensures that zone{1+shift} always exists
        if present_zones == set([f'zone{1+shift}']):
            gs[0,0] = layout_zone.get(f'zone{1+shift}')

        # Layouts with two non-zero zones
        if present_zones == set([f'zone{1+shift}', f'zone{2+shift}']):
            gs[slice(0, 1), slice(0+shift,1+shift)] = layout_zone.get(f'zone{1+shift}')
            gs[slice(0, 1), slice(1+shift,2+shift)] = layout_zone.get(f'zone{2+shift}')
        elif present_zones == set([f'zone{1+shift}', f'zone{5+shift}']):
            gs[slice(0, 1), slice(0+shift,2+shift)] = layout_zone.get(f'zone{1+shift}')
            gs[slice(1, 2), slice(0+shift,2+shift)] = layout_zone.get(f'zone{5+shift}')
        elif present_zones == set([f'zone{1+shift}', f'zone{6+shift}']):
            gs[slice(0, 1), slice(0+shift,1+shift)] = layout_zone.get(f'zone{1+shift}')
            gs[slice(0, 1), slice(1+shift,2+shift)] = layout_zone.get(f'zone{6+shift}')

        # Layouts with three non-zero zones
        elif present_zones == set([f'zone{1+shift}', f'zone{2+shift}', f'zone{5+shift}']):
            gs[slice(0, 1), slice(0+shift,1+shift)] = layout_zone.get(f'zone{1+shift}')
            gs[slice(0, 2), slice(1+shift,2+shift)] = layout_zone.get(f'zone{2+shift}')
            gs[slice(1, 2), slice(0+shift,1+shift)] = layout_zone.get(f'zone{5+shift}')
        elif present_zones == set([f'zone{1+shift}', f'zone{2+shift}', f'zone{6+shift}']):
            gs[slice(0, 2), slice(0+shift,1+shift)] = layout_zone.get(f'zone{1+shift}')
            gs[slice(0, 1), slice(1+shift,2+shift)] = layout_zone.get(f'zone{2+shift}')
            gs[slice(1, 2), slice(1+shift,1+shift)] = layout_zone.get(f'zone{6+shift}')
        elif present_zones == set([f'zone{1+shift}', f'zone{5+shift}', f'zone{6+shift}']):
            gs[slice(0, 1), slice(0+shift,2+shift)] = layout_zone.get(f'zone{1+shift}')
            gs[slice(1, 2), slice(0+shift,1+shift)] = layout_zone.get(f'zone{5+shift}')
            gs[slice(1, 2), slice(1+shift,2+shift)] = layout_zone.get(f'zone{6+shift}')

        # Layouts with four non-zero zones   
        elif present_zones == set([f'zone{1+shift}', f'zone{2+shift}', f'zone{5+shift}', f'zone{6+shift}']):
            gs[slice(0, 1), slice(0+shift,1+shift)] = layout_zone.get(f'zone{1+shift}')
            gs[slice(0, 1), slice(1+shift,2+shift)] = layout_zone.get(f'zone{2+shift}')
            gs[slice(1, 2), slice(0+shift,1+shift)] = layout_zone.get(f'zone{5+shift}')
            gs[slice(1, 2), slice(1+shift,2+shift)] = layout_zone.get(f'zone{6+shift}')

        return gs

    def update_visibility(self, event):
        active = event.new
        tab_names = event.obj._names
        objects = event.obj.objects
        for i, (view_name, content) in enumerate(zip(tab_names, objects)):
            visible = (i == active)
            view = self.views[view_name]
            view._panel_view_is_visible = visible
            if visible:
                # Refresh the view if it is visible
                view.refresh()
                # we also set the current view as the panel active
                view.notify_active_view_updated()

    def _handle_shortcut(self, event):
        if event.data == "focus":
            self.focus_mode = not self.focus_mode

            for tabs in self.all_tabs:
                if self.focus_mode:
                    tabs.stylesheets = [
                        """
                        .bk-header {
                            display: none !important;
                        }
                        """
                    ]
                else:
                    tabs.stylesheets = []


    def set_external_curation(self, curation_data):
        if "curation" not in self.views:
            return

        curation_view = self.views["curation"]
        self.controller.set_curation_data(curation_data)
        curation_view.notify_manual_curation_updated()
        curation_view.refresh()


def get_local_ip():
    """
    Get the local IP address of the machine.
    """
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually need to connect
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def find_free_port():
    """
    Find a free port on the local machine.
    This is useful for starting a server without specifying a port.

    Returns
    -------
    int
        A free port number.
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))  # Bind to a free port assigned by the OS
        return s.getsockname()[1]

def start_server(window_or_dict, address="localhost", port=0, **panel_kwargs):
    """
    Start a Panel server with the main window layout.

    Parameters
    ----------
    window_or_dict : Panel window or dict
        The main window instance containing the layout to serve or a dictionary of
        windows to serve. If a dictionary is provided, it should contain the names
        of the views as keys and their corresponding Panel objects as values.
    address : str, optional
        The address to bind the server to. Defaults to "localhost".
        If "auto-ip" is specified, it will use the local IP address.
    port : int, optional
        The port to bind the server to. If 0, a free port will be found
        automatically. Defaults to 0.
    panel_kwargs : dict, optional
        Additional keyword arguments to pass to the Panel server.
        These can include options like `show`, `start`, `dev`, `autoreload`,
        and `websocket_origin`.
    """
    if port == 0:
        port = find_free_port()
        print(f"Found available port: {port}")

    if address == "auto-ip":
        address = get_local_ip()

    # Set websocket_origin automatically if not explicitly provided
    websocket_origin = panel_kwargs.get("websocket_origin")
    if websocket_origin is None and address != "localhost":
        websocket_origin = f"{address}:{port}"

    dev = panel_kwargs.get("dev", False)
    autoreload = panel_kwargs.get("autoreload", False)
    start = panel_kwargs.get("start", True)
    show = panel_kwargs.get("show", True)
    verbose = panel_kwargs.get("verbose", True)

    if not isinstance(window_or_dict, dict):
        # If a single window is provided, convert it to a dictionary
        mainwindow = window_or_dict
        mainwindow.main_layout = mainwindow.main_layout if hasattr(mainwindow, 'main_layout') else mainwindow.layout
        window_dict = {"/": mainwindow.main_layout}
    else:
        # If a dictionary is provided, use it directly
        window_dict = window_or_dict

    server = pn.serve(
        window_dict, address=address, port=port,
        show=show, start=start, dev=dev, autoreload=autoreload,
        websocket_origin=websocket_origin, verbose=verbose,
        title="SpikeInterface GUI"
    )
    return server, address, port, websocket_origin
