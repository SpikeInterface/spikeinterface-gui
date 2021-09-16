"""
GUI without copy on top of spikeinterface objects
"""

from .version import version as __version__

from .myqt import QT, mkQApp
from .mainwindow import MainWindow
from .controller import SpikeinterfaceController

# views
from .unitlist import UnitListView
from .spikelist import SpikeListView
from .pairlist import PairListView
from .traceview import TraceView
from .waveformview import WaveformView
from .waveformheatmapview import WaveformHeatMapView
from .isiview import ISIView
from .crosscorrelogramview import CrossCorrelogramView
