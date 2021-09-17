import sys
import os
import argparse

from spikeinterface import WaveformExtractor

from spikeinterface_gui import MainWindow, mkQApp




def run_mainwindow(waveform_folder):
    app = mkQApp()
    we = WaveformExtractor.load_from_folder(waveform_folder)
    win = MainWindow(we)
    win.show()
    app.exec_()


def run_mainwindow_cli():
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='spikeinterface-gui')
    parser.add_argument('waveform_folder', help='Waveform folder path', default=None, nargs='?')
    
    
    args = parser.parse_args(argv)

    waveform_folder = args.waveform_folder
    if waveform_folder is None:
        print('Should must specify the waveform folder like this: sigui /path/to/mywaveform/folder')
        exit()
    
    run_mainwindow(waveform_folder)
    
