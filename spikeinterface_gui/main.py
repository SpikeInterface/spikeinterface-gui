import sys
import argparse
import numpy as np

from spikeinterface import load_sorting_analyzer, load_extractor
from spikeinterface.core.core_tools import is_path_remote
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics

from spikeinterface_gui import MainWindow, mkQApp




def run_mainwindow(analyzer, with_traces=True, curation=False, recording=None):
    app = mkQApp()
    if recording is not None:
        analyzer.set_temporary_recording(recording)
    win = MainWindow(analyzer, with_traces=with_traces, curation=curation)
    win.show()
    app.exec()


def run_mainwindow_cli():
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='spikeinterface-gui')
    parser.add_argument('analyzer_folder', help='SortingAnalyzer folder path', default=None, nargs='?')
    parser.add_argument('--no-traces', help='Do not show traces', action='store_true', default=False)
    parser.add_argument('--curation', help='Enable curation panel', action='store_true', default=False)
    parser.add_argument('--recording', help='Path to a file or path that can be loaded with load_extractor', default=None)
    parser.add_argument('--preprocess-recording', choices=['none', 'highpass', 'bandpass'], help='Preprocess the recording', default='none')
    
    args = parser.parse_args(argv)
    # print(args)

    analyzer_folder = args.analyzer_folder
    if analyzer_folder is None:
        print('You must specify the analyzer folder like this: sigui /path/to/my/analyzer/folder')
        exit()
    analyzer = load_sorting_analyzer(analyzer_folder, load_extensions=not is_path_remote(analyzer_folder))

    recording = None
    if args.recording is not None:
        try:
            recording = load_extractor(args.recording)
        except Exception as e:
            print('Error when loading recording. Please check the path or the file format')
        if recording is not None:
            if args.preprocess_recording == 'highpass':
                from spikeinterface.preprocessing import highpass_filter
                recording = highpass_filter(recording)
            elif args.preprocess_recording == 'bandpass':
                from spikeinterface.preprocessing import bandpass_filter
                recording = bandpass_filter(recording)
            if analyzer.get_num_channels() != recording.get_num_channels():
                print('Recording and analyzer have different number of channels. Slicing recording')
                channel_mask = np.isin(recording.channel_ids, analyzer.channel_ids)
                recording = recording.select_channels(recording.channel_ids[channel_mask])
                recording = None
    
    run_mainwindow(analyzer, with_traces=not(args.no_traces), curation=args.curation, recording=recording)
    
