# from .unitlist import UnitListView
# from .spikelist import SpikeListView
# from .mergeview import MergeView
# from .traceview import TraceView
# from .waveformview import WaveformView
# from .waveformheatmapview import WaveformHeatMapView
# from .isiview import ISIView
from .crosscorrelogramview import CrossCorrelogramView
# from .probeview import ProbeView
# from .ndscatterview import NDScatterView
# from .similarityview import SimilarityView
from .spikeamplitudeview import SpikeAmplitudeView
# from .tracemapview import TraceMapView
# from .curationview import CurationView

possible_class_views = dict(
    # unitlist = UnitListView,
    # spikelist = SpikeListView,
    # mergelist = MergeView,
    # traceview = TraceView,
    # waveformview = WaveformView,
    # waveformheatmapview = WaveformHeatMapView,
    # isiview = ISIView,
    # crosscorrelogramview = CrossCorrelogramView,
    # probeview = ProbeView,
    # ndscatterview = NDScatterView,
    # similarityview = SimilarityView,
    spikeamplitudeview = SpikeAmplitudeView,
    # tracemapview = TraceMapView,
    # curation = CurationView,
)