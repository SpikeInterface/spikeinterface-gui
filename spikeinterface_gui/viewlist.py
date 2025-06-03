from .unitlist import UnitListView
from .spikelist import SpikeListView
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

possible_class_views = dict(
    probe = ProbeView, # probe view is first, since it updates channels upon unit changes
    unitlist = UnitListView,
    spikelist = SpikeListView,
    mergelist = MergeView,
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
    mainsettings=MainSettingsView,
)
