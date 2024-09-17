import spikeinterface_gui as sigui

from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder

import spikeinterface.full as si

from pathlib import Path

test_folder = Path('my_dataset')


def setup_module():
    make_analyzer_folder(test_folder)

def teardown_module():
    clean_all(test_folder)


def test_controller():
    sorting_analyzer = si.load_sorting_analyzer(test_folder / "sorting_analyzer")
    print()
    controller = sigui.SpikeinterfaceController(sorting_analyzer)
    print(controller)
    
    # print(controller.segment_slices)
    print(controller.get_isi_histograms())
    

if __name__ == '__main__':
    
    # setup_module()
    test_controller()
