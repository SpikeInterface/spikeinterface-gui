import warnings
import numpy as np


from .view_base import ViewBase

from spikeinterface.postprocessing.unit_locations import possible_localization_methods


class MetricsView(ViewBase):
    _supported_backend = ['qt', ]
    _settings = [
        ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        self.contact_positions = controller.get_contact_location()
        self.probes = controller.get_probegroup().probes
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        self._unit_positions = self.controller.unit_positions

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleClickToPosition
    
        self.layout = QT.QVBoxLayout()

    def _qt_refresh(self):
        pass




    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, HoverTool, Label, PanTool
        from bokeh.events import Tap, PanStart, PanEnd
        from .utils_panel import CustomCircle, _bg_color
