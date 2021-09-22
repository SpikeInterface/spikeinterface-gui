from .unitlist import UnitListView
from .spikelist import SpikeListView
from .pairlist import PairListView
from .traceview import TraceView
from .waveformview import WaveformView
from .waveformheatmapview import WaveformHeatMapView
from .isiview import ISIView
from .crosscorrelogramview import CrossCorrelogramView
from .probeview import ProbeView
from .ndscatterview import NDScatterView
from .similarityview import SimilarityView

possible_class_views = dict(
    unitlist = UnitListView,
    spikelist = SpikeListView,
    pairlist = PairListView,
    traceview = TraceView,
    waveformview = WaveformView,
    waveformheatmapview = WaveformHeatMapView,
    isiview = ISIView,
    crosscorrelogramview = CrossCorrelogramView,
    probeview = ProbeView,
    ndscatterview = NDScatterView,
    similarityview = SimilarityView,
)