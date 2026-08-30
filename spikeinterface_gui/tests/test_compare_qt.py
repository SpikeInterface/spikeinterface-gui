from argparse import ArgumentParser
from spikeinterface_gui import run_compare_analyzer

from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder, make_curation_dict

from spikeinterface import load_sorting_analyzer


from pathlib import Path

import numpy as np
import sys




def setup_module():
    global test_folder
    case = test_folder.stem.split('_')[-1]
    make_analyzer_folder(test_folder, case=case)

def teardown_module():
    clean_all(test_folder)


def test_run_compare_analyzer():
    analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    analyzers = [analyzer, analyzer]
    run_compare_analyzer(
        analyzers,
        mode="desktop",
        verbose=True,
    )

if __name__ == '__main__':
    global test_folder

    dataset = "small"
    test_folder = Path(dataset).parent / f"my_dataset_{dataset}"
    if not test_folder.is_dir():
        setup_module()

    win = test_run_compare_analyzer()
