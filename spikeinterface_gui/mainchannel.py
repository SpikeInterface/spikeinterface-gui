import numpy as np

from .view_base import ViewBase



class MainChannelView(ViewBase):
    id = "mainchannel"
    _supported_backend = ['qt', ]
    _depend_on = ["templates", "template_metrics"]
    _settings = [
        {'name': 'ncols', 'type': 'int', 'value': 3 },
        {'name': 'width_mode', 'type': 'list', 'limits' : ['half_width', 'peak_width'] },
    ]
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

        nbefore, nafter = self.controller.get_waveform_sweep()
        fs = self.controller.sampling_frequency
        self.time_vect = np.arange(-nbefore, nafter) / fs * 1000.
        factor = self.controller.get_template_upsampling_factor()
        self.time_vect_high = np.arange(-nbefore*factor, nafter*factor) / (fs * factor) * 1000.

    
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

            unit_id = visible_unit_ids[i]

            plot = pg.PlotItem()
            self.grid.addItem(plot, row=row, col=col)

            template, template_high, peak_data = self.controller.get_upsampled_templates(unit_id)

            
            color = self.get_unit_color(unit_id)

            plot.addItem(pg.PlotCurveItem( [self.time_vect_high[0] , self.time_vect_high[-1]],
                                          [0, 0], color="grey"))

            curve = pg.PlotCurveItem(self.time_vect, template,
                                     pen=pg.mkPen("white", width=1.))
            plot.addItem(curve)
            curve = pg.PlotCurveItem(self.time_vect_high, template_high,
                                     pen=pg.mkPen(color, width=2))
            plot.addItem(curve)

            times = self.time_vect_high
            names = ('trough', 'peak_before', 'peak_after')
            peak_inds =  peak_data[[f'{k}_index' for k in names]].values
            scatter = pg.ScatterPlotItem(x = times[peak_inds], y = template_high[peak_inds],
                                size=10, pxMode = True, color="white")
            plot.addItem(scatter)
            for ind in peak_inds:
                x = [times[ind], times[ind]]
                y = [0, template_high[ind]]
                plot.addItem(pg.PlotCurveItem(x,y), color="white")

            for k in names:
                if self.settings['width_mode'] == 'half_width':
                    left = peak_data[f'{k}_half_width_left']
                    right = peak_data[f'{k}_half_width_right']
                if self.settings['width_mode'] == 'peak_width':
                    left = peak_data[f'{k}_width_left']
                    right = peak_data[f'{k}_width_right']
                
                if left != -1:
                    inds = [left, right]
                    x = times[inds]
                    # y = template_high[inds] <<<< this make a strange line
                    m = np.mean(template_high[inds])
                    y = [m, m ]
                    plot.addItem(pg.PlotCurveItem(x,y), color="white")


    