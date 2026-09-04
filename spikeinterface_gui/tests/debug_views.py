import spikeinterface_gui as sigui
from spikeinterface_gui.tests.testingtools import (
    clean_all, make_analyzer_folder, make_comparison_analyzer_folders, make_curation_dict
)

from spikeinterface_gui.controller import Controller
from spikeinterface_gui.controllercomparison import ControllerComparison
from spikeinterface_gui.myqt import mkQApp
from spikeinterface_gui.viewlist import get_all_possible_views
from spikeinterface_gui.backend_qt import ViewWidget


import spikeinterface.full as si



from pathlib import Path

test_folder = Path(__file__).parents[2] / 'my_dataset_small'
# test_folder = Path(__file__).parents[2] / 'my_dataset_big'
# test_folder = Path(__file__).parents[2] / 'my_dataset_multiprobe'

# for the comparison views, see make_comparison_analyzer_folders()
comparison_test_folder = Path(__file__).parents[2] / 'my_dataset_comparison_small'


def make_controller():
    analyzer = si.load_sorting_analyzer(test_folder / "sorting_analyzer", load_extensions=False)

    curation_dict = make_curation_dict(analyzer)
    # curation_dict = None

    curation = curation_dict is not None

    controller = Controller(analyzer, verbose=True, curation=curation, curation_data=curation_dict, 
                            skip_extensions=['principal_components'],
                            )

    controller.set_visible_unit_ids(analyzer.unit_ids[:2])
    return controller


def make_comparison_controller():
    """A ControllerComparison, to debug the comparison views (compareunitlist, agreementmatrix, venn)"""
    if not comparison_test_folder.is_dir():
        make_comparison_analyzer_folders(comparison_test_folder, case="small", unit_dtype="int")

    analyzer1 = si.load_sorting_analyzer(comparison_test_folder / "sorting_analyzer_1")
    analyzer2 = si.load_sorting_analyzer(comparison_test_folder / "sorting_analyzer_2")

    controller = ControllerComparison(analyzer1, analyzer2, analyzer1_name="sorter1", analyzer2_name="sorter2",
                                      verbose=True)
    controller.set_visible_unit_ids(controller.unit_ids[:2])
    return controller


def debug_one_view(view_name, comparison=False):

    app = mkQApp()

    if comparison:
        controller = make_comparison_controller()
    else:
        controller = make_controller()

    possible_class_views = get_all_possible_views()
    view_class = possible_class_views[view_name]
    widget = ViewWidget(view_class)
    view = view_class(controller=controller, parent=widget, backend='qt')
    widget.set_view(view)
    widget.show()
    view.refresh()
    
    app.exec()

    
if __name__ == '__main__':
    # debug_one_view('unitlist')
    # debug_one_view('mainsettings')
    # debug_one_view('spikeamplitude')
    # debug_one_view('metrics')

    # the comparison only views
    debug_one_view('venn', comparison=True)
    # debug_one_view('agreementmatrix', comparison=True)
    # debug_one_view('compareunitlist', comparison=True)
