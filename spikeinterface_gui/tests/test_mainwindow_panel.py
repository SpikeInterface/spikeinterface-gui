from argparse import ArgumentParser
from spikeinterface_gui import run_mainwindow, run_launcher

from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder, make_curation_dict

from spikeinterface import load_sorting_analyzer


from pathlib import Path

import numpy as np

# import logging


# logger = logging.getLogger('bokeh')
# logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)


# test_folder = Path(__file__).parent / 'my_dataset_small'
test_folder = Path(__file__).parent / 'my_dataset_big'
# test_folder = Path(__file__).parent / 'my_dataset_multiprobe'


def setup_module():
    case = test_folder.stem.split('_')[-1]
    make_analyzer_folder(test_folder, case=case)

def teardown_module():
    clean_all(test_folder)


def test_mainwindow(start_app=False, verbose=True, curation=False, only_some_extensions=False, from_si_api=False, port=0):


    analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    # analyzer = load_analyzer(test_folder / "sorting_analyzer.zarr")

    print(analyzer)

    if curation:
        curation_dict = make_curation_dict(analyzer)
    else:
        curation_dict = None
    
    if only_some_extensions:
        analyzer = analyzer.copy()
        # analyzer._recording = None
        for k in ("principal_components", "template_similarity", "spike_amplitudes"):
            analyzer.delete_extension(k)
        print(analyzer)

    n = analyzer.unit_ids.size
    analyzer.sorting.set_property(key='yep', values=np.array([f"yep{i}" for i in range(n)]))

    extra_unit_properties = dict(
        yop=np.array([f"yop{i}" for i in range(n)]),
        yip=np.array([f"yip{i}" for i in range(n)]),
    )
    win = None

    for segment_index in range(analyzer.get_num_segments()):
        shift = (segment_index + 1) * 100
        # add a gap to times
        gap = 5
        times = analyzer.recording.get_times(segment_index)
        times = times + shift
        times[len(times)//2:] += gap  # add a gap in the middle
        analyzer.recording.set_times(
            times,
            segment_index=segment_index
        )

    win = run_mainwindow(
        analyzer,
        mode="web",
        start_app=start_app, verbose=verbose,
        curation=curation, curation_dict=curation_dict, 
        displayed_unit_properties=None,
        extra_unit_properties=extra_unit_properties,
        layout_preset='default',
        # address="10.69.168.40",
        port=port,
        # user_settings={"mainsettings": {"color_mode": "color_by_visibility", "max_visible_units": 5}}
    )
    return win


def test_launcher(verbose=True):

    # case 1
    analyzer_folders = None
    # case 2 : explore parent
    analyzer_folders = Path(__file__).parent 
    # case 3 : list
    analyzer_folders = [
        Path(__file__).parent / 'my_dataset_small/sorting_analyzer',
        Path(__file__).parent / 'my_dataset_big/sorting_analyzer',
    ]
    # case 4 : dict
    analyzer_folders = {
        'small' : Path(__file__).parent / 'my_dataset_small/sorting_analyzer',
        'big' : Path(__file__).parent / 'my_dataset_big/sorting_analyzer',
    }

    win = run_launcher(mode="web", analyzer_folders=analyzer_folders, verbose=verbose)




parser = ArgumentParser()
parser.add_argument('--dataset', default="small", help='Path to the dataset folder')

if __name__ == '__main__':
    args = parser.parse_args()
    dataset = args.dataset
    if dataset == "small":
        test_folder = Path(__file__).parent / 'my_dataset_small'
    elif dataset == "big":
        test_folder = Path(__file__).parent / 'my_dataset_big'
    elif dataset == "multiprobe":
        test_folder = Path(__file__).parent / 'my_dataset_multiprobe'
    else:
        test_folder = Path(dataset)
    if not test_folder.is_dir():
        setup_module()

    win = test_mainwindow(start_app=True, verbose=True, curation=True, port=0)

    # test_launcher(verbose=True)

# TO RUN with panel serve:
# win = test_mainwindow(start_app=False, verbose=True, curation=True)
# >>> panel serve test_mainwindow_panel.py --autoreload
