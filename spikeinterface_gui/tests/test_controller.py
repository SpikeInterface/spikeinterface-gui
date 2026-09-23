from pathlib import Path

import numpy as np

import spikeinterface.full as si

from spikeinterface_gui.controller import Controller
from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder

test_folder = Path('my_dataset')


def setup_module():
    make_analyzer_folder(test_folder)


def teardown_module():
    clean_all(test_folder)


def _load_controller(curation=False):
    sorting_analyzer = si.load_sorting_analyzer(test_folder / "sorting_analyzer")
    return Controller(sorting_analyzer, curation=curation)


def test_controller():
    controller = _load_controller()

    # unit_ids mirror the analyzer
    assert list(controller.unit_ids) == list(controller.analyzer.unit_ids)

    # isi histograms were computed and are shaped consistently with the units
    isi_histograms, isi_bins = controller.get_isi_histograms()
    assert isi_histograms.shape[0] == controller.unit_ids.size
    assert isi_bins.shape[0] == isi_histograms.shape[1] + 1




if __name__ == '__main__':
    setup_module()
    try:
        test_controller()
    finally:
        teardown_module()
