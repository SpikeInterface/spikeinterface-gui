import sys
import os
import argparse

from spikeinterface import load_sorting_analyzer
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics

from spikeinterface_gui import MainWindow, mkQApp




def run_mainwindow(
        analyzer,
        with_traces=True,
        curation=False,
        curation_dict=None,
        label_definitions=None,
        displayed_units_properties=None,
        extra_units_properties=None,
    ):

    app = mkQApp()
    
    win = MainWindow(
        analyzer,
        with_traces=with_traces,
        curation=curation,
        curation_dict=curation_dict,
        label_definitions=label_definitions,
        displayed_units_properties=displayed_units_properties,
        extra_units_properties=extra_units_properties,
    )
    win.show()
    app.exec()


def run_mainwindow_cli():
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='spikeinterface-gui')
    parser.add_argument('analyzer_folder', help='SortingAnalyzer folder path', default=None, nargs='?')
    parser.add_argument('--no-traces', help='Do not show traces', action='store_true', default=False)
    parser.add_argument('--curation', help='Do not show traces', action='store_true', default=False)
    
    
    args = parser.parse_args(argv)
    # print(args)

    analyzer_folder = args.analyzer_folder
    if analyzer_folder is None:
        print('You must specify the analyzer folder like this: sigui /path/to/my/analyzer/folder')
        exit()
    analyzer = load_sorting_analyzer(analyzer_folder)
    
    run_mainwindow(analyzer, with_traces=not(args.no_traces), curation=args.curation)
    
