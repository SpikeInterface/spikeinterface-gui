"""
Some design notes:
  * controller is a layer between spikeinterface objects and every view
  * every view can notify some signals to other view that are centralized bu the controller
  * views have settings
  * views have 2 implementations : qt (legacy) and panel (for the web)
    They need to implement the make_layout and the refresh for each backends (qt, panel).
    They do not hinerits from qt or panel objects for contains qt or panel object (design by composition).
    Internally, methods related to qt starts with _qt_XXX.
    Internally, methods related to panel starts with _panel_XXX.
"""

from .version import version as __version__

from .main import run_mainwindow, run_launcher

