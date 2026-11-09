"""The main windows, built without starting the app loop."""
import pytest

import spikeinterface.full as si

from spikeinterface_gui import run_mainwindow, run_mainwindow_comparison
from spikeinterface_gui.tests.testingtools import make_curation_dict, prepare_analyzer_for_gui, set_comparison_labels


def _skip_if_missing(mode, request):
    if mode == "desktop":
        request.getfixturevalue("qapp")
    else:
        pytest.importorskip("panel")


@pytest.mark.parametrize("mode,events", [("desktop", "times"), ("web", "samples")])
def test_mainwindow(mode, events, analyzer_folder, request):
    _skip_if_missing(mode, request)
    analyzer = si.load_sorting_analyzer(analyzer_folder / "sorting_analyzer", load_extensions=False)
    extra_unit_properties, events_dict = prepare_analyzer_for_gui(analyzer, events=events, seed=0)
    win = run_mainwindow(
        analyzer, mode=mode, start_app=False, panel_window_servable=False,
        curation=True, curation_dict=make_curation_dict(analyzer),
        extra_unit_properties=extra_unit_properties, events=events_dict,
    )
    assert len(win.views) > 0


@pytest.mark.parametrize("mode", ["desktop", "web"])
def test_mainwindow_missing_extensions(mode, analyzer_folder, request):
    _skip_if_missing(mode, request)
    # in-memory copy, so that deleting extensions leaves the dataset intact
    analyzer = si.load_sorting_analyzer(analyzer_folder / "sorting_analyzer").copy()
    for k in ("principal_components", "template_similarity", "spike_amplitudes"):
        analyzer.delete_extension(k)
    win = run_mainwindow(analyzer, mode=mode, start_app=False, panel_window_servable=False)
    assert "ndscatter" not in win.views


@pytest.mark.parametrize("mode", ["desktop", "web"])
def test_mainwindow_comparison(mode, comparison_folder, request):
    _skip_if_missing(mode, request)
    analyzer1 = si.load_sorting_analyzer(comparison_folder / "sorting_analyzer_1")
    analyzer2 = si.load_sorting_analyzer(comparison_folder / "sorting_analyzer_2")
    set_comparison_labels(analyzer1, analyzer2)
    win = run_mainwindow_comparison(
        analyzer1, analyzer2, analyzer1_name="sorter1", analyzer2_name="sorter2",
        mode=mode, start_app=False, panel_window_servable=False,
    )
    assert len(win.views) > 0


def test_curation_callback(analyzer_folder):
    """The GUI embedded in a parent panel app, which receives the curation through a callback."""
    pn = pytest.importorskip("panel")
    analyzer = si.load_sorting_analyzer(analyzer_folder / "sorting_analyzer")
    received = []

    def on_curation_saved(curation_data, title):
        received.append((curation_data, title))

    win = run_mainwindow(
        analyzer, mode="web", start_app=False, panel_window_servable=False,
        curation=True, curation_dict=make_curation_dict(analyzer),
        curation_callback=on_curation_saved, curation_callback_kwargs={"title": "done"},
    )
    pn.Column("# Parent Application", win.main_layout)

    win.controller.save_curation_callback()

    assert len(received) == 1
    curation_data, title = received[0]
    assert title == "done"
    def merge_sets(merges):
        return {frozenset(m["unit_ids"]) for m in merges}
    assert merge_sets(curation_data["merges"]) == merge_sets(make_curation_dict(analyzer)["merges"])
    assert win.controller.current_curation_saved
