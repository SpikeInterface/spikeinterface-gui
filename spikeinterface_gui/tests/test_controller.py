import PySide6
import spikeinterface_gui as sigui

from spikeinterface_gui.tests.testingtools import clean_all, make_one_folder

from spikeinterface import WaveformExtractor, extract_waveforms

from pathlib import Path

test_folder = Path('my_dataset')


def setup_module():
    make_one_folder()

def teardown_module():
    clean_all()

def test_controller(interactive=False):
    we = WaveformExtractor.load_from_folder(test_folder / 'waveforms')
    controller = sigui.SpikeinterfaceController(we)
    #~ print(controller)

if __name__ == '__main__':
    
    #~ setup_module()
    
    
    test_controller(interactive=True)