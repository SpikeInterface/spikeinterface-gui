import spikeinterface_gui as sigui
from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder

from spikeinterface_gui.controller import Controller
from spikeinterface_gui.myqt import mkQApp
from spikeinterface_gui.viewlist import possible_class_views
from spikeinterface_gui.backend_qt import ViewWidget


import spikeinterface.full as si



from pathlib import Path


# test_folder = Path(__file__).parent / 'my_dataset_small'
test_folder = Path(__file__).parent / 'my_dataset_big'
# test_folder = Path(__file__).parent / 'my_dataset_multiprobe'


def debug_one_view():

    app = mkQApp()
    sorting_analyzer = si.load_sorting_analyzer(test_folder / "sorting_analyzer")
    
    
    controller = Controller(sorting_analyzer, verbose=True)

    # view_class = possible_class_views['unitlist']
    view_class = possible_class_views['spikeamplitude']
    widget = ViewWidget(view_class)
    view = view_class(controller=controller, parent=widget, backend='qt')
    widget.set_view(view)
    widget.show()

    app.exec()

    
if __name__ == '__main__':
    debug_one_view()
