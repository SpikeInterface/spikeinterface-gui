import spikeinterface_gui as sigui

from spikeinterface_gui.tests.testingtools import clean_all, make_one_folder

import spikeinterface.full as si

from pathlib import Path

test_folder = Path('my_dataset')


def setup_module():
    make_one_folder(test_folder)

def teardown_module():
    clean_all(test_folder)


def test_controller():
    sorting_result = si.load_sorting_result(test_folder / "sorting_result")
    print()
    controller = sigui.SpikeinterfaceController(sorting_result)
    print(controller)
    
    print(controller.segment_slices)
    
    

if __name__ == '__main__':
    
    # setup_module()
    test_controller()
