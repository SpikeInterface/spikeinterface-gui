import os

# headless Qt, for the tests and the CI; set before anything imports Qt
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import spikeinterface.full as si

from spikeinterface_gui.tests.testingtools import (
    get_dataset_folder, make_curation_dict, prepare_analyzer_for_gui, set_comparison_labels,
)


@pytest.fixture(scope="session")
def analyzer_folder():
    return get_dataset_folder("small")


@pytest.fixture(scope="session")
def comparison_folder():
    return get_dataset_folder("small", comparison=True)


@pytest.fixture(scope="session")
def qapp():
    pytest.importorskip("PySide6")
    pytest.importorskip("pyqtgraph")
    from spikeinterface_gui.myqt import mkQApp
    return mkQApp()


def _skip_if_backend_missing(backend):
    if backend == "qt":
        pytest.importorskip("PySide6")
        pytest.importorskip("pyqtgraph")
    else:
        pytest.importorskip("panel")


def load_controller(analyzer_folder, backend):
    """A Controller with curation and events, so every view of the main GUI is possible."""
    from spikeinterface_gui.controller import Controller

    _skip_if_backend_missing(backend)
    analyzer = si.load_sorting_analyzer(analyzer_folder / "sorting_analyzer")
    extra_unit_properties, events = prepare_analyzer_for_gui(analyzer, events="times", seed=0)
    return Controller(analyzer, backend=backend, curation=True, curation_data=make_curation_dict(analyzer),
                      extra_unit_properties=extra_unit_properties, events=events)


def load_comparison_controller(comparison_folder, backend):
    from spikeinterface_gui.controllercomparison import ControllerComparison

    _skip_if_backend_missing(backend)
    analyzer1 = si.load_sorting_analyzer(comparison_folder / "sorting_analyzer_1")
    analyzer2 = si.load_sorting_analyzer(comparison_folder / "sorting_analyzer_2")
    set_comparison_labels(analyzer1, analyzer2)
    return ControllerComparison(analyzer1, analyzer2, analyzer1_name="sorter1", analyzer2_name="sorter2",
                                backend=backend)
