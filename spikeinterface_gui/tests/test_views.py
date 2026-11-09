"""Every view, built and refreshed on its own, for each backend and kind of controller."""
import pytest

from spikeinterface_gui.viewlist import get_all_possible_views
from spikeinterface_gui.tests.conftest import load_controller, load_comparison_controller

VIEWS = get_all_possible_views()


@pytest.fixture(scope="module")
def controllers(analyzer_folder, comparison_folder):
    # one controller per (kind, backend), built on first use and shared by the views
    cache = {}

    def get(kind, backend):
        if (kind, backend) not in cache:
            if kind == "main":
                cache[kind, backend] = load_controller(analyzer_folder, backend)
            else:
                cache[kind, backend] = load_comparison_controller(comparison_folder, backend)
        return cache[kind, backend]

    return get


@pytest.mark.parametrize("kind", ["main", "comparison"])
@pytest.mark.parametrize("backend", ["qt", "panel"])
@pytest.mark.parametrize("view_name", list(VIEWS))
def test_view(view_name, backend, kind, controllers, request):
    view_class = VIEWS[view_name]
    if backend not in view_class._supported_backend:
        pytest.skip(f"{view_name} does not support {backend}")
    if backend == "qt":
        request.getfixturevalue("qapp")
    controller = controllers(kind, backend)
    if not controller.check_is_view_possible(view_name):
        pytest.skip(f"{view_name} is not possible with the {kind} controller")
    if view_name == "curation" and not controller.curation:
        pytest.skip("no curation in comparison mode")

    if backend == "qt":
        from spikeinterface_gui.backend_qt import ViewWidget
        widget = ViewWidget(view_class)
        view = view_class(controller=controller, parent=widget, backend="qt")
        widget.set_view(view)
    else:
        view = view_class(controller=controller, parent=None, backend="panel")
    view.refresh()
