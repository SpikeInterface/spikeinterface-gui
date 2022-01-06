import spikeinterface_gui as sigui

from spikeinterface_gui.tests.testingtools import clean_all, make_one_folder

from spikeinterface import WaveformExtractor, extract_waveforms

from pathlib import Path

test_folder = Path('my_dataset')


def setup_module():
    make_one_folder(test_folder)

def teardown_module():
    clean_all(test_folder)


def test_controller(interactive=False):
    we = WaveformExtractor.load_from_folder(test_folder / 'waveforms')
    controller = sigui.SpikeinterfaceController(we)
    print(controller)
    print(controller.pc)
    
    
    all_labels, all_components = controller.pc.get_all_components()
    
    print(all_components.shape)
    

if __name__ == '__main__':
    
    #~ setup_module()
    
    
    test_controller(interactive=True)