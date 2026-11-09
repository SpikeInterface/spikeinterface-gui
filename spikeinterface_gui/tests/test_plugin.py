"""The views of plugin_example, found through the entry points. Runs only when plugin_example is installed."""
import pytest

import spikeinterface.full as si

from spikeinterface_gui import run_mainwindow
from spikeinterface_gui.viewlist import get_all_possible_views

pytest.importorskip("my_custom_view_plugin")


def test_plugin_views_registered():
    views = get_all_possible_views()
    assert "custom1view" in views
    assert "custom2view" in views


def test_mainwindow_with_plugin_views(analyzer_folder, qapp):
    analyzer = si.load_sorting_analyzer(analyzer_folder / "sorting_analyzer")
    # same layout as plugin_example/example_usage.py
    layout = {
        'zone1': ['unitlist'],
        'zone2': ['waveform', 'trace'],
        'zone3': ['similarity'],
        'zone4': ['custom1view', 'custom2view'],
    }
    win = run_mainwindow(analyzer, mode="desktop", start_app=False, layout=layout)
    assert "custom1view" in win.views
    assert "custom2view" in win.views
