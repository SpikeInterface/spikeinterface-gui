import PySide6
import spikeinterface_gui as sigui

from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder

from spikeinterface import load_sorting_analyzer
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics


from pathlib import Path

import numpy as np

test_folder = Path('my_dataset')


def setup_module():
    make_analyzer_folder(test_folder, num_probe=1)

def teardown_module():
    clean_all(test_folder)


def test_mainwindow(interactive=False, verbose=True, curation=False, only_some_extensions=False):
    app = sigui.mkQApp()
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



    # win = sigui.MainWindow(analyzer, verbose=verbose, curation=curation, curation_dict=curation_dict)
    
    # if interactive:
    #     win.show()
    #     app.exec()
    # else:
    #     # close thread properly
    #     win.close()

    print(analyzer.unit_ids, analyzer.unit_ids.dtype)
    print(analyzer.sorting.unit_ids, analyzer.sorting.unit_ids.dtype)

    analyzer.sorting.set_property(key='yep', values=np.array(["a", ] * len(analyzer.unit_ids)))

    from spikeinterface.widgets import plot_sorting_summary
    plot_sorting_summary(analyzer, backend='spikeinterface_gui',
                         curation=curation, curation_dict=curation_dict,
                         displayed_units_properties=["x","y", "snr"],
                         )






if __name__ == '__main__':
    setup_module()
    
    # test_mainwindow(interactive=True)
    # test_mainwindow(interactive=True, verbose=True, only_some_extensions=True)
    # test_mainwindow(interactive=True, curation=True)

    # import spikeinterface.widgets as sw
    # analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    # sw.plot_sorting_summary(sorting_analyzer, backend="spikeinterface_gui")
