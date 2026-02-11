import importlib.metadata

from .unitlistview import UnitListView
from .spikelistview import SpikeListView
from .mergeview import MergeView
from .traceview import TraceView
from .waveformview import WaveformView
from .waveformheatmapview import WaveformHeatMapView
from .isiview import ISIView
from .correlogramview import CorrelogramView
from .probeview import ProbeView
from .ndscatterview import NDScatterView
from .similarityview import SimilarityView
from .spikeamplitudeview import SpikeAmplitudeView
from .spikedepthview import SpikeDepthView
from .amplitudescalingsview import AmplitudeScalingsView
from .tracemapview import TraceMapView
from .curationview import CurationView
from .mainsettingsview import MainSettingsView
from .metricsview import MetricsView
from .spikerateview import SpikeRateView

# probe and mainsettings view are first, since they affect other views (e.g., time info)
builtin_views = [
    ProbeView, MainSettingsView, UnitListView, SpikeRateView, MergeView,
    TraceView, TraceMapView, WaveformView, WaveformHeatMapView, ISIView,
    CorrelogramView, NDScatterView, SimilarityView, SpikeAmplitudeView,
    SpikeDepthView, SpikeRateView, CurationView, MetricsView, SpikeListView,
    AmplitudeScalingsView,
]

def get_all_possible_views():
    """
    Get all possible view classes, including built-in and plugin views.

    Returns
    -------
    dict
        A dictionary mapping view IDs to view classes.
    """
    # id is a unique identifier
    possible_class_views = {}
    for view in builtin_views:
        possible_class_views[view.id] = view
    # Load plugin views
    eps = importlib.metadata.entry_points(group="spikeinterface_gui.views")
    for ep in eps:
        try:
            view_class = ep.load()
            possible_class_views[ep.name] = view_class
        except Exception as e:
            # Log but don't crash if a plugin fails to load
            print(f"Warning: Failed to load plugin view '{ep.name}': {e}")

    return possible_class_views