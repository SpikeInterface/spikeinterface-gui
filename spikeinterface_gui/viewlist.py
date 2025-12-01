import importlib.metadata

from .unitlistview import UnitListView
from .spikelistview import SpikeListView
from .mergeview import MergeView
from .traceview import TraceView
from .waveformview import WaveformView
from .waveformheatmapview import WaveformHeatMapView
from .isiview import ISIView
from .crosscorrelogramview import CrossCorrelogramView
from .probeview import ProbeView
from .ndscatterview import NDScatterView
from .similarityview import SimilarityView
from .spikeamplitudeview import SpikeAmplitudeView
from .spikedepthview import SpikeDepthView
from .tracemapview import TraceMapView
from .curationview import CurationView
from .mainsettingsview import MainSettingsView
from .metricsview import MetricsView
from .spikerateview import SpikeRateView

# probe and mainsettings view are first, since they affect other views (e.g., time info)
builtin_views = [
    ProbeView, MainSettingsView, UnitListView, SpikeRateView, MergeView,
    TraceView, TraceMapView, WaveformView, WaveformHeatMapView, ISIView,
    CrossCorrelogramView, NDScatterView, SimilarityView, SpikeAmplitudeView,
    SpikeDepthView, SpikeRateView, CurationView, MetricsView
]

# id is a unique identifier
possible_class_views = {}
for view in builtin_views:
    possible_class_views[view.id] = view

# Flag to track if plugins have been loaded
_plugins_loaded = False

def _load_plugin_views():
    """
    Lazy-load plugin views from entry points.
    
    This is done lazily to avoid circular import issues when plugins
    import from spikeinterface_gui during module initialization.
    """
    global _plugins_loaded
    if _plugins_loaded:
        return
    
    _plugins_loaded = True
    eps = importlib.metadata.entry_points(group="spikeinterface_gui.views")
    for ep in eps:
        try:
            view_class = ep.load()
            possible_class_views[ep.name] = view_class
        except Exception as e:
            # Log but don't crash if a plugin fails to load
            print(f"Warning: Failed to load plugin view '{ep.name}': {e}")


# Create a dict subclass that loads plugins on first access
class _ViewDict(dict):
    """Dictionary that lazy-loads plugin views on first access."""
    
    def __getitem__(self, key):
        _load_plugin_views()
        return super().__getitem__(key)
    
    def __contains__(self, key):
        _load_plugin_views()
        return super().__contains__(key)
    
    def keys(self):
        _load_plugin_views()
        return super().keys()
    
    def values(self):
        _load_plugin_views()
        return super().values()
    
    def items(self):
        _load_plugin_views()
        return super().items()
    
    def get(self, key, default=None):
        _load_plugin_views()
        return super().get(key, default)


# Convert to lazy-loading dict
possible_class_views = _ViewDict(possible_class_views)