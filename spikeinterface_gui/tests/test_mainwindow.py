#~ import PySide6
import spikeinterface_gui as sigui

from spikeinterface_gui.tests.testingtools import clean_all, make_one_folder

from spikeinterface import WaveformExtractor, extract_waveforms

from pathlib import Path

test_folder = Path('my_dataset')


def setup_module():
    make_one_folder(test_folder)

def teardown_module():
    clean_all(test_folder)

def test_mainwindow(interactive=False):
    app = sigui.mkQApp()
    
    we = WaveformExtractor.load_from_folder(test_folder / 'waveforms')
    #~ we = WaveformExtractor.load_from_folder('/home/samuel/Bureau/bug_si_synaptic_sage/waveforms/')
    
    
    win = sigui.MainWindow(we)
    
    if interactive:
        win.show()
        app.exec_()
    else:
        # close thread properly
        win.close()

    
if __name__ == '__main__':
    
    setup_module()
    
    test_mainwindow(interactive=True)




    