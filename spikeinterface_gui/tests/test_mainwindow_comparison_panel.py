from argparse import ArgumentParser
from pathlib import Path

from spikeinterface import load_sorting_analyzer

from spikeinterface_gui import run_mainwindow_comparison

from spikeinterface_gui.tests.testingtools import clean_all, make_comparison_analyzer_folders


test_folder = Path(__file__).parents[2] / "my_dataset_comparison_small"


def setup_module():
    case = test_folder.stem.split('_')[-1]
    make_comparison_analyzer_folders(test_folder, case=case, unit_dtype="int")


def teardown_module():
    clean_all(test_folder)


def test_mainwindow_comparison(start_app=False, verbose=True, port=0):

    analyzer1 = load_sorting_analyzer(test_folder / "sorting_analyzer_1")
    analyzer2 = load_sorting_analyzer(test_folder / "sorting_analyzer_2")

    print(analyzer1)
    print(analyzer2)

    win = run_mainwindow_comparison(
        analyzer1,
        analyzer2,
        analyzer1_name="sorter1",
        analyzer2_name="sorter2",
        mode="web",
        start_app=start_app,
        verbose=verbose,
        port=port,
    )

    return win


parser = ArgumentParser()
parser.add_argument('--dataset', default="small", help='Path to the dataset folder')

if __name__ == '__main__':
    args = parser.parse_args()
    if args.dataset is not None:
        test_folder = Path(__file__).parents[2] / f"my_dataset_comparison_{args.dataset}"

    if not test_folder.is_dir():
        setup_module()

    win = test_mainwindow_comparison(start_app=True, verbose=True, port=0)

# TO RUN with panel serve:
# win = test_mainwindow_comparison(start_app=False, verbose=True)
# >>> panel serve test_mainwindow_comparison_panel.py --autoreload
