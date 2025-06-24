from spikeinterface_gui import run_mainwindow

from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder, make_curation_dict

from spikeinterface import load_sorting_analyzer
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics


from pathlib import Path

import numpy as np

# import logging


# logger = logging.getLogger('bokeh')
# logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)


test_folder = Path(__file__).parent / 'my_dataset_small'
# test_folder = Path(__file__).parent / 'my_dataset_big'
# test_folder = Path(__file__).parent / 'my_dataset_multiprobe'


def setup_module():
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
    win = None

    win = run_mainwindow(
        analyzer,
        mode="web",
        start_app=start_app, verbose=verbose,
        curation=curation, curation_dict=curation_dict, 
        displayed_unit_properties=None,
        extra_unit_properties=extra_unit_properties,
        layout_preset='default',
        # skip_extensions=["waveforms", "principal_components", "template_similarity", "spike_amplitudes"],
        # address="10.69.168.40",
        # port=5000,
    )
    return win

if not test_folder.is_dir():
    setup_module()

win = test_mainwindow(start_app=True, verbose=True, curation=True)

# TO RUN with panel serve:
# win = test_mainwindow(start_app=False, verbose=True, curation=True)
# >>> panel serve test_mainwindow_panel.py --autoreload
