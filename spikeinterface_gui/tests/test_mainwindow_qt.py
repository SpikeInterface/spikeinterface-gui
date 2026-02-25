from argparse import ArgumentParser
from spikeinterface_gui import run_mainwindow, run_launcher

from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder, make_curation_dict

from spikeinterface import load_sorting_analyzer


from pathlib import Path

import numpy as np
import sys



# yep is for testing
yep_layout = dict(
    zone1=['curation', 'spikelist'],
    zone2=['unitlist', 'mergelist'],
    zone3=['trace', 'tracemap', 'spikeamplitude'],
    zone4=['similarity'],
    zone5=['probe'],
    zone6=['ndscatter', ],
    zone7=['waveform', 'waveformheatmap', ],
    zone8=['correlogram', 'isi'],
)


def setup_module():
    global test_folder
    case = test_folder.stem.split('_')[-1]
    make_analyzer_folder(test_folder, case=case)

def teardown_module():
    clean_all(test_folder)


def test_mainwindow(start_app=False, verbose=True, curation=False, only_some_extensions=False, from_si_api=False):


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
        mode="desktop",
        start_app=start_app,
        verbose=verbose,
        curation=curation, curation_dict=curation_dict, 
        displayed_unit_properties=None,
        extra_unit_properties=extra_unit_properties,
        layout_preset='default',
        # user_settings={"mainsettings": {"color_mode": "color_by_visibility", "max_visible_units": 5}}
    )


def test_launcher(verbose=True):

    # case 1
    analyzer_folders = None
    root_folder = None
    
    # case 2 : explore parent
    analyzer_folders = None
    root_folder = Path(__file__).parent 
    
    # case 3 : list
    # analyzer_folders = [
    #     Path(__file__).parent / 'my_dataset_small/sorting_analyzer',
    #     Path(__file__).parent / 'my_dataset_big/sorting_analyzer',
    # ]
    # root_folder = None

    # case 4 : dict
    # analyzer_folders = {
    #     'small' : Path(__file__).parent / 'my_dataset_small/sorting_analyzer',
    #     'big' : Path(__file__).parent / 'my_dataset_big/sorting_analyzer',
    # }
    # root_folder = None

    win = run_launcher(mode="desktop", analyzer_folders=analyzer_folders, root_folder=root_folder,  verbose=verbose)


parser = ArgumentParser()
parser.add_argument('--dataset', default="small", help='Path to the dataset folder')

if __name__ == '__main__':
    args = parser.parse_args()
    dataset = args.dataset
    global test_folder
    if dataset is not None:
        test_folder = Path(dataset).parent / f"my_dataset_{dataset}"
    if not test_folder.is_dir():
        setup_module()

    win = test_mainwindow(start_app=True, verbose=True, curation=True)
    # win = test_mainwindow(start_app=True, verbose=True, curation=False)

    # test_launcher(verbose=True)
