import numpy as np
import matplotlib.cm
import matplotlib.colors


from .view_base import ViewBase



class WaveformHeatMapView(ViewBase):
    _supported_backend = ['qt']
    _settings = [
                      {'name': 'colormap', 'type': 'list', 'limits' : ['hot', 'viridis', 'jet', 'gray',  ] },
                      {'name': 'show_channel_id', 'type': 'bool', 'value': True},
                      #~ {'name': 'data', 'type': 'list', 'limits' : ['waveforms', 'features', ] },
                      {'name': 'bin_min', 'type': 'float', 'value' : -20. },
                      {'name': 'bin_max', 'type': 'float', 'value' : 8. },
                      {'name': 'bin_size', 'type': 'float', 'value' : .1 },
                      {'name': 'max_unit', 'type': 'int', 'value' : 4 },
                      ]
    
    _depend_on = ['waveforms']


    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    def _make_layout_qt(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleclickAndGain

        self.layout = QT.QVBoxLayout()
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)

        # self.graphicsview2 = pg.GraphicsView()
        # self.layout.addWidget(self.graphicsview2)
        # self.graphicsview2.hide()
        

        self.viewBox = ViewBoxHandlingDoubleclickAndGain()
        # self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.gain_zoom.connect(self.gain_zoom)
        self.viewBox.disableAutoRange()
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        
        self.curves = []
        
        self.settings.blockSignals(True)


        nbefore, nafter = self.controller.get_waveform_sweep()
        # width = nbefore + nafter
        
        
        self.wf_min, self.wf_max = self.controller.get_waveforms_range()
        self.settings['bin_min'] = min(self.wf_min * 2, -5.)
        self.settings['bin_max'] = max(self.wf_max * 2, 5)
        
        self.settings['bin_size'] = (self.settings['bin_max'] - self.settings['bin_min']) / 600
        
        self.settings.blockSignals(False)
        
        self.channel_labels = []
        for chan_id in self.controller.channel_ids:
            label = pg.TextItem(f'{chan_id}', anchor=(.5,.5), color='#FFFF00')
            label.setFont(QT.QFont('', pointSize=12))
            self.plot.addItem(label)
            label.hide()
            label.setZValue(1000)
            self.channel_labels.append(label)

        self.similarity = None

        self.on_params_changed()#this do refresh
    
    
    def on_params_changed(self, ): 
        
        N = 512
        cmap_name = self.settings['colormap']
        cmap = matplotlib.colormaps[cmap_name].resampled(N)
        
        lut = []
        for i in range(N):
            r,g,b,_ =  matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r*255,g*255,b*255])
        self.lut = np.array(lut, dtype='uint8')

        self._x_range = None
        self._y_range = None
        
        self.refresh()
    
    def gain_zoom(self, v):
        levels = self.image.getLevels()
        if levels is not None:
            self.image.setLevels(levels * v, update=True)
    
    def _hide_all(self):
        self.image.hide()
        for label in self.channel_labels:
            label.hide()
    
    def _refresh_qt(self):
        from .myqt import QT
        import pyqtgraph as pg
        
        unit_visible_dict = self.controller.unit_visible_dict
        
        visible_unit_ids = [unit_id for unit_id, v in unit_visible_dict.items() if v ]
        
        if len(visible_unit_ids) > 0:
            intersect_sparse_indexes = self.controller.get_intersect_sparse_channels(visible_unit_ids)
        else:
            self._hide_all()
            return

        #remove old curves
        for curve in self.curves:
            self.plot.removeItem(curve)
        self.curves = []
        
        if len(visible_unit_ids)>self.settings['max_unit'] or (len(visible_unit_ids)==0):
            self._hide_all()
            return
        
        if len(intersect_sparse_indexes) ==0:
            self._hide_all()
            return
                
        waveforms = []
        for unit_id in visible_unit_ids:
            wfs, channel_inds = self.controller.get_waveforms(unit_id)
            wfs, chan_inds = self.controller.get_waveforms(unit_id)
            keep = np.isin(chan_inds, intersect_sparse_indexes)
            waveforms.append(wfs[:, :, keep])
        waveforms = np.concatenate(waveforms)
        data  = waveforms.swapaxes(1,2).reshape(waveforms.shape[0], -1)
        
        bin_min, bin_max = self.settings['bin_min'], self.settings['bin_max']
        bin_size = max(self.settings['bin_size'], 0.01)
        bins = np.arange(bin_min, bin_max, self.settings['bin_size'])


        n = bins.size

        hist2d = np.zeros((data.shape[1], bins.size))
        indexes0 = np.arange(data.shape[1])
        
        data_bined = np.floor((data-bin_min)/bin_size).astype('int32')
        data_bined = data_bined.clip(0, bins.size-1)
        
        for d in data_bined:
            hist2d[indexes0, d] += 1
        
        self.image.setImage(hist2d, lut=self.lut)#, levels=[0, self._max])
        self.image.setRect(QT.QRectF(-0.5, bin_min, data.shape[1], bin_max-bin_min))
        self.image.show()
        
        
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if unit_id not in visible_unit_ids:
                continue
            
            
            template_avg = self.controller.templates_average[unit_index, :, :][:, intersect_sparse_indexes]
            
            color = self.get_unit_color(unit_id)
            
            y = template_avg.T.flatten()
            
            curve = pg.PlotCurveItem(x=indexes0, y=y, pen=pg.mkPen(color, width=2))
            self.plot.addItem(curve)
            self.curves.append(curve)
            
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter        
        pos = 0
        for chan_ind, chan_id in enumerate(self.controller.channel_ids):
            label = self.channel_labels[chan_ind]
            if self.settings['show_channel_id'] and chan_ind in intersect_sparse_indexes:
                label.show()
                label.setPos(pos * width + nbefore, 0)
                pos += 1
            else:
                label.hide()
        
        if True:
            self._x_range = 0, indexes0[-1] #hist2d.shape[1]
            self._y_range = bin_min, bin_max
        

        self.plot.setXRange(*self._x_range, padding = 0.0)
        self.plot.setYRange(*self._y_range, padding = 0.0)
    
    # def show_hide_1d_dist(self, v=None):
    #     if v:
    #         self.graphicsview2.show()
    #     else:
    #         self.graphicsview2.hide()



WaveformHeatMapView._gui_help_txt = """Unit waveform heat map
Check density around the average template for each unit.
Useful to check overlap between units.

right click : X/Y zoom
left click : move
mouse wheel : color range for density (important!!)

For efficiency : no more than  4 units visible at same time.
This can be changed in the settings."""