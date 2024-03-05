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

def test_mainwindow(interactive=False):
    app = sigui.mkQApp()
    sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    print(sorting_analyzer)
    win = sigui.MainWindow(sorting_analyzer, verbose=False)
    
    if interactive:
        win.show()
        app.exec_()
    else:
        # close thread properly
        win.close()

    
if __name__ == '__main__':
    # setup_module()
    
    test_mainwindow(interactive=True)

    # import spikeinterface.widgets as sw
    # sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    # sw.plot_sorting_summary(sorting_analyzer, backend="spikeinterface_gui")
