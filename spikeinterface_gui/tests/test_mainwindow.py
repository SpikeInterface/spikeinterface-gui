from spikeinterface_gui import run_mainwindow

from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder

from spikeinterface import load_sorting_analyzer
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics


from pathlib import Path

import numpy as np

# import logging


# logger = logging.getLogger('bokeh')
# logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)

test_folder = Path(__file__).parent / 'my_dataset'


def setup_module():
    make_analyzer_folder(test_folder, num_probe=1)

def teardown_module():
    clean_all(test_folder)


def test_mainwindow(start_app=False, verbose=True, curation=False, only_some_extensions=False, from_si_api=False):


    analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    # analyzer = load_analyzer(test_folder / "sorting_analyzer.zarr")

    print(analyzer)

    if curation:
        unit_ids = analyzer.unit_ids.tolist()
        curation_dict = {
            "unit_ids": unit_ids,
            "label_definitions": {
                "quality":{
                    "label_options": ["good", "noise", "MUA", "artifact"],
                    "exclusive": True,
                }, 
                "putative_type":{
                    "label_options": ["excitatory", "inhibitory", "pyramidal", "mitral"],
                    "exclusive": True,
                }
            },
            "manual_labels": [
                {'unit_id': unit_ids[1], "quality": ["MUA"]},
                {'unit_id': unit_ids[2], "putative_type": ["exitatory"]},
                {'unit_id': unit_ids[3], "quality": ["noise"], "putative_type": ["inhibitory"]},
            ],
            "merge_unit_groups": [unit_ids[:3], unit_ids[3:5]],
            "removed_units": unit_ids[5:8],
        }
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
    if from_si_api:
        from spikeinterface.widgets import plot_sorting_summary
        plot_sorting_summary(analyzer, backend='spikeinterface_gui',
                            curation=curation, curation_dict=curation_dict,
                            displayed_unit_properties=None,
                            extra_unit_properties=extra_unit_properties,
                            )
    else:
        win = run_mainwindow(
            analyzer,
            backend="panel",
            start_app=start_app, verbose=verbose,
            curation=curation, curation_dict=curation_dict, 
            displayed_unit_properties=None,
            extra_unit_properties=extra_unit_properties,
            layout_preset='default',
        )
    return win





# if __name__ == '__main__':
if not test_folder.is_dir():
    setup_module()
    
    # test_mainwindow(start_qt_app=True, verbose=False)
    # test_mainwindow(start_qt_app=True, verbose=True, only_some_extensions=True)
    # test_mainwindow(start_qt_app=True, curation=True, from_si_api=False)
    # test_mainwindow(start_qt_app=True, curation=True, from_si_api=True)

    # import spikeinterface.widgets as sw
    # analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    # sw.plot_sorting_summary(sorting_analyzer, backend="spikeinterface_gui")

win = test_mainwindow(start_app=False, verbose=True, curation=True)
# print("Saving to HTML")
# win.main_layout.save(filename=str(test_folder.parent / "panel_app.html"), embed=True)

