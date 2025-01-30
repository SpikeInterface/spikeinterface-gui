import sys
import argparse
from pathlib import Path
import numpy as np

from spikeinterface import load_sorting_analyzer, load
from spikeinterface.core.core_tools import is_path_remote

# this force the loding of spikeinterface sub module
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics

from spikeinterface_gui import MainWindow, mkQApp



def run_mainwindow(
    analyzer,
    with_traces=True,
    curation=False,
    curation_dict=None,
    label_definitions=None,
    displayed_unit_properties=None,
    extra_unit_properties=None,
    recording=None,
    start_qt_app=True,
    verbose=False,
):
    """
    Create the main window and start the QT app loop.

    Parameters
    ----------
    analyzer: SortingAnalyzer
        The sorting analyzer object
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
    recording: RecordingExtractor | None, default: None
        The recording object to display traces. This can be used when the 
        SortingAnalyzer is recordingless.
    start_qt_app: bool, default: True
        If True, the QT app loop is started
    verbose: bool, default: False
        If True, print some information in the console
    """
    from .myqt import QtGui
    app = mkQApp()

    if recording is not None:
        analyzer.set_temporary_recording(recording)
    
    win = MainWindow(
        analyzer,
        verbose=verbose,
        with_traces=with_traces,
        curation=curation,
        curation_dict=curation_dict,
        label_definitions=label_definitions,
        displayed_unit_properties=displayed_unit_properties,
        extra_unit_properties=extra_unit_properties,
    )
    win.setWindowTitle('SpikeInterface GUI')
    this_file = Path(__file__).absolute()
    win.setWindowIcon(QtGui.QIcon(str(this_file.parent / 'img' / 'si.png')))
    win.show()
    if start_qt_app:
        app.exec()


def run_mainwindow_cli():
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='spikeinterface-gui')
    parser.add_argument('analyzer_folder', help='SortingAnalyzer folder path', default=None, nargs='?')
    parser.add_argument('--no-traces', help='Do not show traces', action='store_true', default=False)
    parser.add_argument('--curation', help='Enable curation panel', action='store_true', default=False)
    parser.add_argument('--recording', help='Path to a recording file (.json/.pkl) or folder that can be loaded with spikeinterface.load', default=None)
    parser.add_argument('--recording-base-folder', help='Base folder path for the recording (if .json/.pkl)', default=None)
    parser.add_argument('--verbose', help='Make the output verbose', action='store_true', default=False)
    
    args = parser.parse_args(argv)

    analyzer_folder = args.analyzer_folder
    if analyzer_folder is None:
        print('You must specify the analyzer folder like this: sigui /path/to/my/analyzer/folder')
        exit()
    if args.verbose:
        print('Loading analyzer...')
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
    
    run_mainwindow(analyzer, with_traces=not(args.no_traces), curation=args.curation, recording=recording, verbose=args.verbose)
    
