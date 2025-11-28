import sys
import argparse
import json
from pathlib import Path
import numpy as np
import warnings

from spikeinterface import load_sorting_analyzer, load
from spikeinterface.core import BaseRecording, SortingAnalyzer, BaseEvent
from spikeinterface.core.sortinganalyzer import get_available_analyzer_extensions
from .utils_global import get_config_folder
from spikeinterface_gui.layout_presets import get_layout_description

import spikeinterface_gui
from spikeinterface_gui.controller import Controller
from spikeinterface_gui.viewlist import possible_class_views

def run_mainwindow(
    analyzer: SortingAnalyzer,
    mode: str = "desktop",
    with_traces: bool = True,
    curation: bool = False,
    curation_dict: dict | None = None,
    label_definitions: dict | None = None,
    displayed_unit_properties: list | None=None,
    extra_unit_properties: list | None=None,
    skip_extensions: list | None = None,
    recording: BaseRecording | None = None,
    events: BaseEvent | dict | None = None,
    start_app: bool = True,
    layout_preset: str | None = None,
    layout: dict | None = None,
    address: str = "localhost",
    port: int = 0,
    panel_start_server_kwargs: dict | None = None,
    panel_window_servable: bool = True,
    verbose: bool = False,
    user_settings: dict | None = None,
    disable_save_settings_button: bool = False,
):
    """
    Create the main window and start the QT app loop.

    Parameters
    ----------
    analyzer: SortingAnalyzer
        The sorting analyzer object
    mode: 'desktop' | 'web'
        The GUI mode to use.
        'desktop' will run a Qt app.
        'web' will run a Panel app.
    with_traces: bool, default: True
        If True, traces are displayed
    curation: bool, default: False
        If True, the curation panel is displayed
    curation_dict: dict | None, default: None
        The curation dictionary to start from an existing curation
    label_definitions: dict | None, default: None
        The label definitions to provide to the curation panel
    displayed_unit_properties: list | None, default: None
        The displayed unit properties in the unit table
    extra_unit_properties: list | None, default: None
        The extra unit properties in the unit table
    skip_extensions: list | None, default: None
        The list of extensions to skip when loading the sorting analyzer
    recording: RecordingExtractor | None, default: None
        The recording object to display traces. This can be used when the 
        SortingAnalyzer is recordingless.
    events: BaseEvent | dict | None, default: None
        The events to display in the GUI. This can be a BaseEvent object or a dictionary
        with keys as event names and another dictionary as values with "samples" or "times".
    start_qt_app: bool, default: True
        If True, the QT app loop is started
    layout_preset : str | None
        The name of the layout preset. None is default.
    layout : dict | None
        The layout dictionary to use instead of the preset.
    address: str, default : "localhost"
        For "web" mode only. By default it is "localhost".
        Use "auto-ip" to use the real IP address of the machine.
    port: int, default: 0
        For "web" mode only. If 0 then the port is automatic.
    panel_start_server_kwargs: dict, default: None
        For "web" mode only. Additional arguments to pass to the Panel server
        - `{'show': True}` to automatically open the browser (default is True).
        - `{'dev': True}` to enable development mode (default is False).
        - `{'autoreload': True}` to enable autoreload of the server when files change
          (default is False).
    panel_window_servable: bool, default: True
        For "web" mode only. If True, the Panel app is made servable.
        This is useful when embedding the GUI in another Panel app. In that case,
        the `panel_window_servable` should be set to False.
    verbose: bool, default: False
        If True, print some information in the console
    user_settings: dict, default: None
        A dictionary of user settings for each view, which overwrite the default settings.
    disable_save_settings_button: bool, default: False
        If True, disables the "save default settings" button, so that user cannot do this.
    """

    if mode == "desktop":
        backend = "qt"
    elif mode == "web":
        backend = "panel"
    else:
        raise ValueError(f"spikeinterface-gui wrong mode {mode}")

    # Order of preference for settings is set here:
    #   1) User specified settings
    #   2) Settings in the config folder
    #   3) Default settings of each view 
    if user_settings is None:
        sigui_version = spikeinterface_gui.__version__
        config_version_folder = get_config_folder() / sigui_version
        settings_file = config_version_folder / "settings.json"
        if settings_file.is_file():
            try:
                with open(settings_file) as f:
                    user_settings = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Config file at {settings_file} is not decodable. Error: {e}")
                print("Using default settings.")

    if recording is not None:
        analyzer.set_temporary_recording(recording)

    if verbose:
        import time
        t0 = time.perf_counter()

    layout_dict = get_layout_description(layout_preset, layout)
    if skip_extensions is None:
        skip_extensions = find_skippable_extensions(layout_dict)

    controller = Controller(
        analyzer, backend=backend, verbose=verbose,
        curation=curation, curation_data=curation_dict,
        label_definitions=label_definitions,
        with_traces=with_traces,
        displayed_unit_properties=displayed_unit_properties,
        extra_unit_properties=extra_unit_properties,
        skip_extensions=skip_extensions,
        disable_save_settings_button=disable_save_settings_button,
        events=events
    )
    if verbose:
        t1 = time.perf_counter()
        print('controller init time', t1 - t0)

    if backend == "qt":
        from spikeinterface_gui.myqt import QT, mkQApp
        from spikeinterface_gui.backend_qt import QtMainWindow

        # Suppress a known pyqtgraph warning
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyqtgraph")
        warnings.filterwarnings('ignore', category=UserWarning, message=".*QObject::connect.*")


        app = mkQApp()

        win = QtMainWindow(controller, layout_dict=layout_dict, user_settings=user_settings)
        win.setWindowTitle('SpikeInterface GUI')
        # Set window icon
        icon_file = Path(__file__).absolute().parent / 'img' / 'si.png'
        if icon_file.exists():
            app.setWindowIcon(QT.QIcon(str(icon_file)))
        win.show()
        if start_app:
            app.exec()
    
    elif backend == "panel":
        from .backend_panel import PanelMainWindow, start_server
        win = PanelMainWindow(controller, layout_dict=layout_dict, user_settings=user_settings)

        if start_app or panel_window_servable:
            win.main_layout.servable(title='SpikeInterface GUI')

        if start_app:
            panel_start_server_kwargs = panel_start_server_kwargs or {}
            _ = start_server(win, address=address, port=port, **panel_start_server_kwargs)

    return win



def run_launcher(mode="desktop", analyzer_folders=None, root_folder=None, address="localhost", port=0, verbose=False):
    """
    Run the launcher for the SpikeInterface GUI.

    Parameters
    ----------
    mode: 'desktop' | 'app', default: 'desktop'
        The backend to use for the GUI.
    analyzer_folders: list of str | dict | None, default: None
        List of analyzer folders to load.
    root_folder: str|Path| None
        A folder that is explore to construct the list of analyzers.
        When not None analyzer_folders must be None.
    address: str, default: "localhost"
        The address to use for the web mode. Default is "localhost".
        Use "auto-ip" to use the real IP address of the machine.
    port: int, default: 0
        The port to use for the web mode. If 0, a random available port is chosen.
    verbose: bool, default: False
        If True, print some information in the console.
    """
    from spikeinterface_gui.launcher import Launcher

    if mode == "desktop":
        from .myqt import QT, mkQApp
        app = mkQApp()
        launcher = Launcher(analyzer_folders=analyzer_folders, root_folder=root_folder, backend="qt", verbose=verbose)
        app.exec()
    
    elif mode == "web":
        import panel as pn
        import webbrowser

        from spikeinterface_gui.launcher import panel_gui_view
        from spikeinterface_gui.backend_panel import start_server

        launcher = Launcher(analyzer_folders=analyzer_folders, root_folder=root_folder, backend="panel", verbose=verbose)

        server, address, port, _ = start_server(
            {"/launcher": launcher.layout, "/gui": panel_gui_view},
            address=address, port=port,
            show=False, start=False, verbose=False
        )

        url = f"http://{address}:{port}/launcher"
        webbrowser.open(url)
        server.start()
        print(f"SpikeInterface GUI launcher running at {url}")
        # BLOCK main thread so server stays alive:
        server.io_loop.start()
    else:
        raise ValueError(f"spikeinterface-gui wrong mode {mode}")

def check_folder_is_analyzer(folder):
    """
    Check if the given folder is a valid SortingAnalyzer folder.

    Parameters
    ----------
    folder: str or Path
        The path to the folder to check.

    Returns
    -------
    bool
        True if the folder is a valid SortingAnalyzer folder, False otherwise.
    """
    from spikeinterface.core.core_tools import is_path_remote

    if not isinstance(folder, (str, Path)):
        return False

    if is_path_remote(folder):
        return True # We assume remote paths are valid, will throw error later if not

    folder = Path(folder)
    if not folder.is_dir():
        return False

    if not str(folder).endswith(".zarr"):
        spikeinterface_info_file = folder / 'spikeinterface_info.json'
        if not spikeinterface_info_file.exists():
            return False
        # Check if the folder contains the necessary files for a SortingAnalyzer
        with open(spikeinterface_info_file, 'r') as f:
            spikeinterface_info = json.load(f)
        if spikeinterface_info.get("object") != "SortingAnalyzer":
            return False
        else:
            return True
    else:  #zarr folder
        import zarr
        # Check if the folder contains the necessary files for a SortingAnalyzer
        zarr_root = zarr.open(folder, mode='r')
        spikeinterface_info = zarr_root.attrs.get('spikeinterface_info')
        if spikeinterface_info is None:
            return False
        if spikeinterface_info.get("object") != "SortingAnalyzer":
            return False
        else:
            return True
        

def run_mainwindow_cli():
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='spikeinterface-gui')
    parser.add_argument('analyzer_folder', help='SortingAnalyzer folder path', default=None, nargs='?')
    parser.add_argument('--root-folder', help='Base folder for launcher mode with multiple analyzer folders', default=None)
    parser.add_argument('--mode', help='Mode desktop or web', default='desktop')
    parser.add_argument('--no-traces', help='Do not show traces', action='store_true', default=False)
    parser.add_argument('--curation', help='Enable curation panel', action='store_true', default=False)
    parser.add_argument('--recording', help='Path to a recording file (.json/.pkl) or folder that can be loaded with spikeinterface.load', default=None)
    parser.add_argument('--recording-base-folder', help='Base folder path for the recording (if .json/.pkl)', default=None)
    parser.add_argument('--verbose', help='Make the output verbose', action='store_true', default=False)
    parser.add_argument('--skip_extensions', help='Choose which extensions not to load, comma separated (e.g. waveforms,principal_components)', default=None)
    parser.add_argument('--port', help='Port for web mode', default=0, type=int)
    parser.add_argument('--address', help='Address for web mode', default='localhost')
    parser.add_argument('--layout-file', help='Path to json file defining layout', default=None)
    parser.add_argument('--curation-file', help='Path to json file defining a curation', default=None)
    parser.add_argument('--settings-file', help='Path to json file specifying the settings of each view', default=None)
    parser.add_argument('--disable_save_settings_button', help='Disables button allowing for user to save default settings', action='store_true', default=False)

    args = parser.parse_args(argv)

    analyzer_folder = args.analyzer_folder
    if analyzer_folder is None:
        if args.verbose:
            print('Running launcher...')
        run_launcher(root_folder=args.root_folder, mode=args.mode, address=args.address, port=args.port, verbose=args.verbose)
    else:
        if args.verbose:
            print('Loading analyzer...')
        assert check_folder_is_analyzer(analyzer_folder), f'The folder {analyzer_folder} is not a valid SortingAnalyzer folder'
        try:
            analyzer = load_sorting_analyzer(analyzer_folder, load_extensions=False)
        except Exception as e:
            print('Error when loading analyzer. Please check the path or the file format')
            raise e
        if args.verbose:
            print('Analyzer loaded')

        recording = None
        if args.recording is not None:
            try:
                if args.verbose:
                    print('Loading recording...')
                recording_base_path = args.recording_base_path
                recording = load(args.recording, base_folder=recording_base_path)
                if args.verbose:
                    print('Recording loaded')
            except Exception as e:
                print('Error when loading recording. Please check the path or the file format')
            if recording is not None:
                if analyzer.get_num_channels() != recording.get_num_channels():
                    print('Recording and analyzer have different number of channels. Slicing recording')
                    channel_mask = np.isin(recording.channel_ids, analyzer.channel_ids)
                    if np.sum(channel_mask) != analyzer.get_num_channels():
                        raise ValueError('The recording does not have the same channel ids as the analyzer')
                    recording = recording.select_channels(recording.channel_ids[channel_mask])

        if args.curation_file is not None:
            with open(args.curation_file, "r") as f:
                curation_data = json.load(f)
        else:
            curation_data = None

        if args.settings_file is not None:
            with open(args.settings_file, "r") as f:
                user_settings = json.load(f)
        else:
            user_settings = None

        disable_save_settings_button = args.disable_save_settings_button

        skip_extensions_string = args.skip_extensions
        skip_extensions_list = skip_extensions_string.split(',') if skip_extensions_string else None        

        run_mainwindow(
            analyzer,
            mode=args.mode,
            with_traces=not(args.no_traces),
            curation=args.curation,
            recording=recording,
            skip_extensions=skip_extensions_list,
            verbose=args.verbose,
            layout=args.layout_file,
            curation_dict=curation_data,
            user_settings=user_settings,
            disable_save_settings_button=disable_save_settings_button,
        )

def find_skippable_extensions(layout_dict):
    """
    Returns the extensions which don't need to be loaded, depending on which views the user
    wants to load. Does this by taking all possible extensions, then removing any which are
    needed by a view.
    """
    
    all_extensions = set(get_available_analyzer_extensions())

    view_per_zone = list(layout_dict.values())
    list_of_views = [view for zone_views in view_per_zone for view in zone_views]

    needed_extensions = ['unit_locations']

    for view in list_of_views:
        extensions_view_depend_on = possible_class_views[view]._depend_on
        if extensions_view_depend_on is not None:
            needed_extensions += extensions_view_depend_on

    skippable_extensions = list(all_extensions.difference(set(needed_extensions)))

    return skippable_extensions