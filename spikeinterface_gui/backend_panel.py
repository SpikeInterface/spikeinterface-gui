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

    def __init__(self, parent=None):
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

    def connect_view(self, view):
        print("connect_view Panel:", view)
        view.notifyer.param.watch(self.on_spike_selection_changed, "spike_selection_changed")
        view.notifyer.param.watch(self.on_unit_visibility_changed, "unit_visibility_changed")
        view.notifyer.param.watch(self.on_channel_visibility_changed, "channel_visibility_changed")
        view.notifyer.param.watch(self.on_manual_curation_updated, "manual_curation_updated")

    def on_spike_selection_changed(self, param):
        # print('on_spike_selection_changed', type(param))
        for view in self.controller.views:
            # Alessio : how do you avoid callback on the own view ? 
            # if view==self.sender(): continue
            view.on_spike_selection_changed()

    def on_unit_visibility_changed(self, param):
        # print('on_unit_visibility_changed', type(param))
        for view in self.controller.views:
            # Alessio : how do you avoid callback on the own view ? 
            # if view==self.sender(): continue
            view.on_unit_visibility_changed()

    def on_channel_visibility_changed(self, param):
        # print('on_channel_visibility_changed', type(param))
        for view in self.controller.views:
            # Alessio : how do you avoid callback on the own view ? 
            # if view==self.sender(): continue
            view.on_channel_visibility_changed()


    def on_manual_curation_updated(self, param):
        # print('on_manual_curation_updated', type(param))
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
    def __init__(self, myparametrized):
        self._parametrized = myparametrized
    
    def __getitem__(self,key):
        return getattr(self._parametrized, key)

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

    # Alessio : how to handle the change on steeing is it like this
    for setting_data in view._settings:
        view.settings._parametrized.param.watch(view.on_settings_changed, setting_data["name"])




class MainWindow:

    def __init__(self, controller, layout_preset=None):
        self.controller = controller
        self.layout_preset = layout_preset
        self.verbose = controller.verbose

        self.make_views()
        self.create_main_layout()
        
        # refresh all views
        for view in self.views.values():
            view.refresh()        

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

            # settings_panel = pn.Param(view.settings._parametrized, name="Settings", show_name=True)

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
                    dynamic=True,  # Render tabs only when activated
                    tabs_location="above",
                )

        left = pn.Column(
            pn.Row(
                *(layout_zone[zone] for zone in ('upper_sidebar', 'upper_left') if layout_zone[zone] is not None),
            ),
            pn.Row(
                *(layout_zone[zone] for zone in ('bottom_sidebar', 'bottom_left') if layout_zone[zone] is not None),
            ),
            sizing_mode="stretch_both",
        )

        right = pn.Column(
            *(layout_zone[zone] for zone in ('upper_right', 'bottom_right') if layout_zone[zone] is not None),
            sizing_mode="stretch_both",
        )

        self.main_layout = pn.Row(
            left,
            right,
            sizing_mode="stretch_both",
        )





        # # Create tabs for views
        # self.main_tabs = pn.Tabs(
        #     # ("Waveform View", self.waveform_view.show()),
        #     # ("Trace View", self.trace_view.show()),
        #     # ("Trace Map View", self.trace_map_view.show()),
        #     ("ISI View", self.view_layouts["isi"]),
        #     ("Correlogram View", self.view_layouts["correlogram"]),
        #     ("Spike Amplitude View", self.view_layouts["spikeamplitude"]),
        #     sizing_mode="stretch_both",
        #     dynamic=True,  # Render tabs only when activated
        #     tabs_location="above",
        # )

        # # make tab with unit list and merge view
        # self.unit_merge_tabs = pn.Tabs(
        #     ("Unit List", self.view_layouts["unitlist"]),
        #     # ("Merge View", self.merge_view.show()),
        #     sizing_mode="stretch_both",
        #     dynamic=True,  # Render tabs only when activated
        #     tabs_location="above",
        #     styles={"min-height": "50%"}

        # )

        # # if self.controller.curation:
        # #     # make top tab with spikelist and curation view
        # #     self.spike_curation_tab = pn.Tabs(
        # #         ("Spike List", self.spike_list_view.show()),
        # #         ("Curation View", self.curation_view.show()),
        # #         sizing_mode="stretch_both",
        # #         dynamic=True,  # Render tabs only when activated
        # #         tabs_location="above",
        # #         styles={"min-height": "50%"}
        # #     )
        # # else:
        # #     self.spike_curation_tab = self.spike_list_view.show()

        # # # make bottom tab with similarity and ndscatter view
        # # if self.ndscatter_view is not None:
        # #     self.similarity_ndscatter_tab = pn.Tabs(
        # #         ("Similarity View", self.similarity_view.show()),
        # #         ("ND Scatter View", self.ndscatter_view.show()),
        # #         sizing_mode="stretch_both",
        # #         dynamic=True,  # Render tabs only when activated
        # #         tabs_location="above",
        # #         styles={"min-height": "50%"}
        # #     )
        # # else:
        # #     self.similarity_ndscatter_tab = pn.Tabs(
        # #         ("Similarity View", self.similarity_view.show()),
        # #         sizing_mode="stretch_both",
        # #         dynamic=True,  # Render tabs only when activated
        # #         tabs_location="above",
        # #         styles={"min-height": "50%"}
        # #     )

        # # # Initialize sidebar with unit list
        # self.sidebar = pn.Row(
        #     pn.Column(
        #         self.unit_merge_tabs,
        #         # self.probe_view.show(),
        #         sizing_mode="stretch_width",
        #     ),
        #     # pn.Column(
        #     #     self.spike_curation_tab,
        #     #     self.similarity_ndscatter_tab,
        #     #     sizing_mode="stretch_width",
        #     # ),
        #     sizing_mode="stretch_width",
        # )

        # # # Create initial layout structure
        # self.main_layout = pn.Column(
        #     pn.Row(
        #         self.sidebar,  # Placeholder for sidebar
        #         self.main_tabs,  # Main content area
        #         sizing_mode="stretch_both"
        #     ),
        #     sizing_mode="stretch_both"
        # )



        # # Update sidebar in layout
        # self.main_layout[0][0] = self.sidebar



# def _find_available_port(address="localhost", start_port: int = 5006, max_attempts: int = 10) -> int:
#     """Find an available port starting from start_port."""
#     for port in range(start_port, start_port + max_attempts):
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
#             try:
#                 sock.bind((address, port))
#                 return port
#             except OSError:
#                 continue
#     raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}")



def start_server(mainwindow, address="localhost", port=0):
    verbose = mainwindow.controller.verbose

    pn.config.sizing_mode = "stretch_width"
    # pn.config.theme = "dark"
    pn.extension("bokeh")

    # logging.basicConfig(level=logging.DEBUG)
    pn.extension("modal", sizing_mode="stretch_width")

    # favicon_path = Path(__file__).parent.parent / "img" / "si.ico"

    # if port is None:
    #     # automatic when localhost
    #     port =_find_available_port(address=address)

    # win.main_layout.servable()
    # server.start()

    mainwindow.main_layout.servable()

    server = pn.serve({"/": mainwindow.main_layout}, address=address, port=port,
                      show=False, start=True, dev=True,  autoreload=True)
    # ioloop = IOLoop.current()
    
    # Handle browser window close using pn.state
    # Alessio : maybe we should have a button for quit instead of the browser closing to be able to recover the session.
    # def on_session_destroyed(session_context):
    #     if not pn.state.curdoc.session_context.sessions:
    #         if verbose:
    #             print("No active sessions. Stopping server...")
    #         server.stop()

    # pn.state.on_session_destroyed(on_session_destroyed)

    # Handle system signals
    # def signal_handler(signum, frame):
    #     if verbose:
    #         print("\nReceived termination signal. Stopping Panel server...")
    #     server.stop()
    #     # sys.exit(0)  # <-- Forcefully exit process

    # signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGTERM, signal_handler)

    # url = f"http://{address}:{port}"

    # server.start()
    # if verbose:
    #     print(f"Spikeinterface-gui server running at {url}")


    # try:
    #     # Start server manually
    #     server.start()
    #     if verbose:
    #         print(f"Spikeinterface-gui server running at {url}")

    #     # Start Tornado event loop
    #     # ioloop.start()

    # except Exception as e:
    #     print("Error starting Panel server:", str(e))
    #     traceback.print_exc()
    #     server.stop()
    #     # sys.exit(1)  # <-- Exit with failure code

    # return url
