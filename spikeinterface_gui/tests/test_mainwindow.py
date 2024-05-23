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

def test_mainwindow(interactive=False, verbose=True):
    app = sigui.mkQApp()
    sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    print(sorting_analyzer)

    win = sigui.MainWindow(sorting_analyzer, verbose=verbose)
    
    if interactive:
        win.show()
        app.exec()
    else:
        # close thread properly
        win.close()


def test_mainwindow_few(interactive=False, verbose=True):
    app = sigui.mkQApp()
    sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    
    # sorting_analyzer._recording = None
    sorting_analyzer = sorting_analyzer.copy()
    for k in ("principal_components", "template_similarity", "spike_amplitudes"):
        sorting_analyzer.delete_extension(k)
    print(sorting_analyzer)


    win = sigui.MainWindow(sorting_analyzer, verbose=verbose)
    
    if interactive:
        win.show()
        app.exec()
    else:
        # close thread properly
        win.close()


    
if __name__ == '__main__':
    # setup_module()
    
    test_mainwindow(interactive=True)
    # test_mainwindow_few(interactive=True, verbose=True)

    # import spikeinterface.widgets as sw
    # sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    # sw.plot_sorting_summary(sorting_analyzer, backend="spikeinterface_gui")
