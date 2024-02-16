#~ import PySide6
import spikeinterface_gui as sigui

from spikeinterface_gui.tests.testingtools import clean_all, make_one_folder

from spikeinterface import load_sorting_result
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
    sorting_result = load_sorting_result(test_folder / "sorting_result")
    print(sorting_result)
    win = sigui.MainWindow(sorting_result)
    
    if interactive:
        win.show()
        app.exec_()
    else:
        # close thread properly
        win.close()

    
if __name__ == '__main__':
    
    # setup_module()
    
    test_mainwindow(interactive=True)




    