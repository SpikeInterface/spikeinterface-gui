import numpy as np

from .view_base import ViewBase



class MainChannelView(ViewBase):
    id = "mainchannel"
    _supported_backend = ['qt', ]
    _depend_on = ["templates"]
    _settings = [
        {'name': 'ncols', 'type': 'int', 'value': 5 },
    ]
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

        nbefore, nafter = self.controller.get_waveform_sweep()
        self.time_vect = np.arange(-nbefore, nafter) / self.controller.sampling_frequency * 1000.

    
    def _on_settings_changed(self):
        self.refresh()

    ## Qt ##

    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)

        self.grid = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.grid)


    def _qt_refresh(self):
        import pyqtgraph as pg

        self.grid.clear()
        
        visible_unit_ids = self.controller.get_visible_unit_ids()

        n = len(visible_unit_ids)
        ncols = self.settings['ncols']
        nrows = int(np.ceil(n / ncols))

        for i in range(n):
            col = i % ncols
            row = i // ncols

            plot = pg.PlotItem()
            self.grid.addItem(plot, row=row, col=col)

            unit_id = visible_unit_ids[i]
            unit_index = list(self.controller.unit_ids).index(unit_id)
            chan_ind = self.controller.get_extremum_channel(unit_id)
            color = self.get_unit_color(unit_id)
            
            template_avg = self.controller.templates_average[unit_index, :, chan_ind]
            curve = pg.PlotCurveItem(self.time_vect, template_avg,
                                    #  brush=color,
                                     pen=pg.mkPen(color, width=3))
            plot.addItem(curve)
        
    