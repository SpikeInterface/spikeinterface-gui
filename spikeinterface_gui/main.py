import sys
import argparse
import json
from pathlib import Path
import numpy as np
import warnings

from spikeinterface import load_sorting_analyzer, load
from spikeinterface.core.core_tools import is_path_remote

from spikeinterface_gui.controller import Controller


def run_mainwindow(
    analyzer,
    mode="desktop",
    with_traces=True,
    curation=False,
    curation_dict=None,
    label_definitions=None,
    displayed_unit_properties=None,
    extra_unit_properties=None,
    skip_extensions=None,
    recording=None,
    start_app=True,
    layout_preset=None,
    layout=None,
    address="localhost",
    port=0,
    panel_start_server_kwargs=None,
    verbose=False,
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
    verbose: bool, default: False
        If True, print some information in the console
    """

    if mode == "desktop":
        backend = "qt"
    elif mode == "web":
        backend = "panel"
    else:
        raise ValueError(f"spikeinterface-gui wrong mode {mode}")


    if recording is not None:
        analyzer.set_temporary_recording(recording)

    if verbose:
        import time
        t0 = time.perf_counter()
    controller = Controller(
        analyzer, backend=backend, verbose=verbose,
        curation=curation, curation_data=curation_dict,
        label_definitions=label_definitions,
        with_traces=with_traces,
        displayed_unit_properties=displayed_unit_properties,
        extra_unit_properties=extra_unit_properties,
        skip_extensions=skip_extensions,
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
        
        win = QtMainWindow(controller, layout_preset=layout_preset, layout=layout)
        win.setWindowTitle('SpikeInterface GUI')
        # Set window icon
        icon_file = Path(__file__).absolute().parent / 'img' / 'si.png'
        if icon_file.exists():
            win.setWindowIcon(QT.QIcon(str(icon_file)))
        win.show()
        if start_app:
            app.exec()
    
    elif backend == "panel":
        from .backend_panel import PanelMainWindow, start_server
        win = PanelMainWindow(controller, layout_preset=layout_preset, layout=layout)
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
    if not isinstance(folder, (str, Path)):
        return False

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
    parser.add_argument('--port', help='Port for web mode', default=0, type=int)
    parser.add_argument('--address', help='Address for web mode', default='localhost')
    
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
        analyzer = load_sorting_analyzer(analyzer_folder, load_extensions=not is_path_remote(analyzer_folder))
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

        run_mainwindow(
            analyzer,
            mode=args.mode,
            with_traces=not(args.no_traces),
            curation=args.curation,
            recording=recording,
            verbose=args.verbose
        )
