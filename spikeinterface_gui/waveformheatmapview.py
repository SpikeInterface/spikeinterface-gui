import numpy as np
import matplotlib.cm
import matplotlib.colors


from .view_base import ViewBase



class WaveformHeatMapView(ViewBase):
    _supported_backend = ['qt', 'panel']
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
        self.make_color_lut()



    def make_color_lut(self):
        N = 512
        cmap_name = self.settings['colormap']
        cmap = matplotlib.colormaps[cmap_name].resampled(N)
        
        lut = []
        for i in range(N):
            r,g,b,_ =  matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r*255,g*255,b*255])
        self.lut = np.array(lut, dtype='uint8')


    def get_plotting_data(self):

        visible_unit_ids = self.controller.get_visible_unit_ids()
        if len(visible_unit_ids) == 0:
            return None

        intersect_sparse_indexes = self.controller.get_intersect_sparse_channels(visible_unit_ids)

        if len(intersect_sparse_indexes) == 0:
            return None

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
        
        data_binned = np.floor((data-bin_min)/bin_size).astype('int32')
        data_binned = data_binned.clip(0, bins.size-1)
        
        for d in data_binned:
            hist2d[indexes0, d] += 1
        
        return hist2d

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleclickAndGain

        self.layout = QT.QVBoxLayout()
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)

        self.viewBox = ViewBoxHandlingDoubleclickAndGain()
        self.viewBox.gain_zoom.connect(self._qt_gain_zoom)
        self.viewBox.disableAutoRange()
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        
        self.curves = []
        
        self.settings.blockSignals(True)


        # nbefore, nafter = self.controller.get_waveform_sweep()
        # width = nbefore + nafter
        
        # adapt bins from data
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


    def _qt_on_settings_changed(self, ):
        self.make_color_lut()
        # self._x_range = None
        # self._y_range = None
        self.refresh()
    
    def _qt_gain_zoom(self, v):
        levels = self.image.getLevels()
        if levels is not None:
            self.image.setLevels(levels * v, update=True)
    
    def _qt_hide_all(self):
        self.image.hide()
        for label in self.channel_labels:
            label.hide()
    
    def _qt_refresh(self):
        from .myqt import QT
        import pyqtgraph as pg
        
        
        visible_unit_ids = self.controller.get_visible_unit_ids()
        
        if len(visible_unit_ids) > 0:
            intersect_sparse_indexes = self.controller.get_intersect_sparse_channels(visible_unit_ids)
        else:
            self._qt_hide_all()
            return

        #remove old curves
        for curve in self.curves:
            self.plot.removeItem(curve)
        self.curves = []
        
        if len(visible_unit_ids)>self.settings['max_unit'] or (len(visible_unit_ids)==0):
            self._qt_hide_all()
            return
        
        if len(intersect_sparse_indexes) ==0:
            self._qt_hide_all()
            return

        bin_min, bin_max = self.settings['bin_min'], self.settings['bin_max']

        hist2d = self.get_plotting_data()
        
        self.image.setImage(hist2d, lut=self.lut)#, levels=[0, self._max])
        self.image.setRect(QT.QRectF(-0.5, bin_min, hist2d.shape[0], bin_max-bin_min))
        self.image.show()
        
        indexes0 = np.arange(hist2d.shape[0])

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


        self._x_range = 0, indexes0[-1] #hist2d.shape[1]
        self._y_range = bin_min, bin_max

        self.plot.setXRange(*self._x_range, padding = 0.0)
        self.plot.setYRange(*self._y_range, padding = 0.0)
    
    ## Panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from .utils_panel import _bg_color
        from bokeh.models import ColumnDataSource, LinearColorMapper
        from bokeh.events import MouseWheel


        self.wf_min, self.wf_max = self.controller.get_waveforms_range()
        self.settings['bin_min'] = min(self.wf_min * 2, -5.)
        self.settings['bin_max'] = max(self.wf_max * 2, 5)
        self.settings['bin_size'] = (self.settings['bin_max'] - self.settings['bin_min']) / 600

        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="pan,box_zoom,reset",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.figure.toolbar.logo = None
        self.figure.grid.visible = False
        self.figure.on_event(MouseWheel, self._panel_gain_zoom)

        N = 512
        cmap = matplotlib.colormaps[self.settings['colormap']]
        self.color_mapper = LinearColorMapper(palette=[matplotlib.colors.rgb2hex(cmap(i)[:3]) for i in np.linspace(0, 1, N)], low=0, high=1)
        self.image_source = ColumnDataSource({"image": [np.zeros((1, 1))], "dw": [1], "dh": [1]})
        self.image_glyph = self.figure.image(
            image="image", x=0, y=0, dw="dw", dh="dh", color_mapper=self.color_mapper, source=self.image_source
        )

        self.layout = pn.Column(
            self.figure,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both"
        )

    def _panel_refresh(self):
        hist2d = self.get_plotting_data()

        if hist2d is None:
            self.image_source.data.update({
                "image": [],
                "dw": [],
                "dh": []
            })
            return

        self.image_source.data.update({
            "image": [hist2d.T],
            "dw": [hist2d.shape[0]],
            "dh": [hist2d.shape[1]]
        })

        self.color_mapper.low = 0
        self.color_mapper.high = np.max(hist2d)

        self.figure.x_range.start = 0
        self.figure.x_range.end = hist2d.shape[0]
        self.figure.y_range.start = 0
        self.figure.y_range.end = hist2d.shape[1]


    def _panel_gain_zoom(self, event):
        factor = 1.3 if event.delta > 0 else 1 / 1.3
        self.color_mapper.high = self.color_mapper.high * factor



WaveformHeatMapView._gui_help_txt = """
## Waveform Heatmap View

Check density around the average template for each unit, which is useful to check overlap between units.
For efficiency, no more than 4 units visible at same time.
This can be changed in the settings.

### Controls
* **mouse wheel** : color range for density (important!!)
* **right click** : X/Y zoom
* **left click** : move
"""
