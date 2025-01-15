import sys
import os
import argparse

from spikeinterface import load_sorting_analyzer

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
        start_qt_app=True,
        verbose=False,
    ):
    """
    Create the main window and start the QT app loop.
    """

    app = mkQApp()
    
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
    win.show()
    if start_qt_app:
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
    
