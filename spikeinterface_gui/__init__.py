"""
GUI without copy on top of spikeinterface objects
"""

from .version import version as __version__

from .myqt import QT, mkQApp
from .mainwindow import MainWindow
from .controller import SpikeinterfaceController

# views
from .viewlist import *
