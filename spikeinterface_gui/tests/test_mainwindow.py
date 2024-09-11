# import PySide6
import spikeinterface_gui as sigui

from spikeinterface_gui.tests.testingtools import clean_all, make_one_folder

from spikeinterface import load_sorting_analyzer
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics


from pathlib import Path

test_folder = Path('my_dataset')


def setup_module():
    make_one_folder(test_folder)

def teardown_module():
    clean_all(test_folder)


def test_mainwindow(interactive=False, verbose=True, curation=False, only_some_extensions=False):
    app = sigui.mkQApp()
    sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    # sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer.zarr")

    print(sorting_analyzer)

    if curation:
        unit_ids = sorting_analyzer.unit_ids.tolist()
        curation_data = {
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
        curation_data = None
    
    if only_some_extensions:
        sorting_analyzer = sorting_analyzer.copy()
        # sorting_analyzer._recording = None
        for k in ("principal_components", "template_similarity", "spike_amplitudes"):
            sorting_analyzer.delete_extension(k)
        print(sorting_analyzer)



    win = sigui.MainWindow(sorting_analyzer, verbose=verbose, curation=curation, curation_data=curation_data)
    
    if interactive:
        win.show()
        app.exec()
    else:
        # close thread properly
        win.close()





if __name__ == '__main__':
    # setup_module()
    
    # test_mainwindow(interactive=True)
    # test_mainwindow(interactive=True, verbose=True, only_some_extensions=True)
    test_mainwindow(interactive=True, curation=True)

    # import spikeinterface.widgets as sw
    # sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    # sw.plot_sorting_summary(sorting_analyzer, backend="spikeinterface_gui")
