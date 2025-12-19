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
from .eventview import EventView

# probe and mainsettings view are first, since they affect other views (e.g., time info)
possible_class_views = dict(
    probe = ProbeView,
    mainsettings = MainSettingsView,
    unitlist = UnitListView,
    spikelist = SpikeListView,
    merge = MergeView,
    trace = TraceView,
    waveform = WaveformView,
    waveformheatmap = WaveformHeatMapView,
    isi = ISIView,
    correlogram = CrossCorrelogramView,
    ndscatter = NDScatterView,
    similarity = SimilarityView,
    spikeamplitude = SpikeAmplitudeView,
    spikedepth = SpikeDepthView,
    tracemap = TraceMapView,
    curation = CurationView,
    spikerate = SpikeRateView,
    metrics = MetricsView,
    event = EventView,
)
