from .myqt import QT
import pyqtgraph as pg

import numpy as np
import matplotlib.cm
import matplotlib.colors

import time

from .base import WidgetBase
from .tools import ParamDialog

class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    gain_zoom = QT.pyqtSignal(float)
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() == QT.Qt.ControlModifier:
            z = 10 if ev.delta()>0 else 1/10.
        else:
            z = 1.3 if ev.delta()>0 else 1/1.3
        self.gain_zoom.emit(z)
        ev.accept()
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass
        

class WaveformHeatMapView(WidgetBase):
    """
    **Waveform histogram viewer** is also a important thing.
    
    It is equivalent to **Waveform veiwer** in **flatten** mode but with
    a 2d histogram that show the density (probability) of a cluster.
    So waveforms are flatten from (nb_peak, nb_sample, nb_channel) to
    (nb_peak, nb_channel*nb_sample) and are binarized on a 2d histogram.
    Then this is plotted as a map. The color code the density.
    
    This is the best friend to see if two cluster are well discrimitated somewhere or
    if one cluster must be split.
    
    Important:
      * use right click for X/Y zoom
      * use left clik to move
      * use **mouse wheel** for color zoom.Really important to play with this
        to discover low density
      * intentionnaly not all cluster are displayed other we see nothing. The best is to plot
        2 by 2. Furthermore it faster to plot with few cluster.
      * don't forget to display the **noise snippet** to validate that the mad is 1 for all channel.
    
    Settings:
      * **colormap** hot is good because loaw density are black like background.
      * **data** choose waveforms or features
      * **bin_min** y limts of histogram
      * **bin_max** y limts of histogram
      * **bin_size**
      * **display_threshold**
      * **max_label** maximum number of labels displayed simulteneously 
        (2 by default but you can set more)
    
    """
    _params = [
                      {'name': 'colormap', 'type': 'list', 'limits' : ['hot', 'viridis', 'jet', 'gray',  ] },
                      {'name': 'show_channel_id', 'type': 'bool', 'value': True},
                      #~ {'name': 'data', 'type': 'list', 'limits' : ['waveforms', 'features', ] },
                      {'name': 'bin_min', 'type': 'float', 'value' : -20. },
                      {'name': 'bin_max', 'type': 'float', 'value' : 8. },
                      {'name': 'bin_size', 'type': 'float', 'value' : .1 },
                      #~ {'name': 'display_threshold', 'type': 'bool', 'value' : True },
                      {'name': 'max_unit', 'type': 'int', 'value' : 4 },
                      #~ {'name': 'n_spike_for_centroid', 'type': 'int', 'value' : 300 },
                      {'name': 'sparse_display', 'type': 'bool', 'value' : True },
                      ]
    
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)

        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        # TODO
        #~ but = QT.QPushButton('Show 1D dist', checkable=True)
        #~ h.addWidget(but)
        #~ but.clicked.connect(self.show_hide_1d_dist)
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)

        self.graphicsview2 = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview2)
        self.graphicsview2.hide()
        
        self.create_settings()
        
        self.initialize_plot()
        self.similarity = None

        self.on_params_changed()#this do refresh
    
    
    def on_params_changed(self, ): #params, changes
        #~ for param, change, data in changes:
            #~ if change != 'value': continue
            #~ if param.name()=='data':
        
        N = 512
        cmap_name = self.params['colormap']
        cmap = matplotlib.cm.get_cmap(cmap_name , N)
        
        lut = []
        for i in range(N):
            r,g,b,_ =  matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r*255,g*255,b*255])
        self.lut = np.array(lut, dtype='uint8')

        self._x_range = None
        self._y_range = None


        
        
        
        self.refresh()
    
    def initialize_plot(self):
        #~ if self.controller.some_peaks_index is None:
            #~ return
        
        self.viewBox = MyViewBox()
        self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.gain_zoom.connect(self.gain_zoom)
        self.viewBox.disableAutoRange()
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        
        #~ self.curve1 = pg.PlotCurveItem()
        #~ self.plot.addItem(self.curve1)
        #~ self.curve2 = pg.PlotCurveItem()
        #~ self.plot.addItem(self.curve2)
        
        self.curves = []
        
        #~ thresh = self.controller.get_threshold()
        #~ self.thresh_line = pg.InfiniteLine(pos=thresh, angle=0, movable=False, pen = pg.mkPen('w'))
        #~ self.plot.addItem(self.thresh_line)

        self.params.blockSignals(True)
        #~ self.params['bin_min'] = np.min(self.controller.some_waveforms)
        #~ self.params['bin_max'] = np.max(self.controller.some_waveforms)
        
        # this is too slow and take too much mem
        #~ ind, = np.nonzero(self.controller.spike_label[self.controller.some_peaks_index]>=0)
        #~ if ind.size > 0:
            #~ wfs = self.controller.some_waveforms.take(ind, axis=0)
            #~ self.params['bin_min'] = np.percentile(wfs, .001)
            #~ self.params['bin_max'] = np.percentile(wfs, 99.999)
        
        #~ ind, = np.nonzero(self.controller.spike_label[self.controller.some_peaks_index]>=0)
        #~ n_left, n_right = self.controller.get_waveform_left_right()
        #~ if ind.size > 0:
            #~ if ind.size > 1000:
                #~ ind = ind[np.random.choice(ind.size, 1000, replace=False)]
            #~ mins, maxs = [], []
            #~ for c in range(self.controller.nb_channel):
                #~ wfs = self.controller.some_waveforms[:, :, c].take(ind, axis=0)
                #~ mins.append(np.percentile(wfs, .001))
                #~ maxs.append(np.percentile(wfs, 99.999))
            #~ self.params['bin_min'] = min(mins)
            #~ self.params['bin_max'] = max(maxs)
            
            #~ if (self.params['bin_max'] - self.params['bin_min']) < 60:
                #~ self.params['bin_size'] = 0.1
            #~ else:
                #~ self.params['bin_size'] = (self.params['bin_max'] - self.params['bin_min']) / 600

        #~ n_left, n_right = self.controller.get_waveform_left_right()
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter        
        
        #~ get_min_max_centroids
        #~ peak_sign = self.controller.get_peak_sign()
        #~ if peak_sign == '+':
            #~ m = np.max(self.controller.spikes['extremum_amplitude'])
            #~ self.params['bin_min'] = min(-m / 10,  -5.)
            #~ self.params['bin_max'] = m * 1.2
        #~ elif peak_sign == '-':
            #~ m = np.min(self.controller.spikes['extremum_amplitude'])
            #~ self.params['bin_min'] = m * 1.2
            #~ self.params['bin_max'] = max(-m / 10,  5.)
        
        self.wf_min, self.wf_max = self.controller.get_waveforms_range()
        self.params['bin_min'] = min(self.wf_min * 2, -5.)
        self.params['bin_max'] = max(self.wf_max * 2, 5)
        
        
        #~ if (self.params['bin_max'] - self.params['bin_min']) < 60:
            #~ self.params['bin_size'] = 0.1
        #~ else:
        self.params['bin_size'] = (self.params['bin_max'] - self.params['bin_min']) / 600
        
        self.params.blockSignals(False)
        
        
        self.channel_labels = []
        for chan_id in self.controller.channel_ids:
            label = pg.TextItem(f'{chan_id}', anchor=(.5,.5), color='#FFFF00')
            label.setFont(QT.QFont('', pointSize=12))
            self.plot.addItem(label)
            label.hide()
            label.setZValue(1000)
            self.channel_labels.append(label)
            
    

    def gain_zoom(self, v):
        #~ print('v', v)
        levels = self.image.getLevels()
        if levels is not None:
            self.image.setLevels(levels * v, update=True)
    
    def _hide_all(self):
        self.image.hide()
        for label in self.channel_labels:
            label.hide()
    
    def _refresh(self):
        #~ if not hasattr(self, 'viewBox'):
            #~ self.initialize_plot()
        
        #~ if not hasattr(self, 'viewBox'):
            #~ return
        
        #~ if self._x_range is not None:
            #~ #this may change with pyqtgraph
            #~ self._x_range = tuple(self.viewBox.state['viewRange'][0])
            #~ self._y_range = tuple(self.viewBox.state['viewRange'][1])
        
        
        
        unit_visible_dict = self.controller.unit_visible_dict
        
        #~ noise_visible = unit_visible_dict.get(labelcodes.LABEL_NOISE, False)
        
        #~ visibles = [k for k, v in unit_visible_dict.items() if v and k>=-1 ]
        visible_unit_ids = [unit_id for unit_id, v in unit_visible_dict.items() if v ]
        
        #~ sparse = self.controller.have_sparse_template and self.params['sparse_display']
        sparse = self.params['sparse_display']
        # get common visible channels
        #~ if sparse:
            #~ if len(visibles) > 0:
                #~ common_channels = self.controller.get_common_sparse_channels(visibles)
            #~ elif noise_visible:
                #~ common_channels = self.controller.channels
            #~ else:
                #~ common_channels = np.array([], dtype='int64')
        #~ else:
            #~ common_channels = self.controller.channels

        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                self._hide_all()
                return
        else:
            #~ common_channel_indexes = self.controller.channels
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype='int64')


        #remove old curves
        for curve in self.curves:
            self.plot.removeItem(curve)
        self.curves = []
        
        if len(visible_unit_ids)>self.params['max_unit'] or (len(visible_unit_ids)==0 and not noise_visible):
            self._hide_all()
            return
        
        if len(common_channel_indexes) ==0:
            self._hide_all()
            return
        
        #~ keep = np.zeros(self.controller.spikes.size, dtype='bool')
        #~ for label in visibles:
            #~ unit_index = list(self.controller.unit_ids).index(unit_id)
            #~ ind_keep, = np.nonzero(self.controller.spikes['unit_index'] == unit_index)
            #~ if ind_keep.size > self.params['n_spike_for_centroid']:
                #~ sub_sel = np.random.choice(ind_keep.size, self.params['n_spike_for_centroid'], replace=False)
                #~ ind_keep = ind_keep[sub_sel]
            #~ keep[ind_keep] = True
        #~ ind_keep, = np.nonzero(keep)
        
        #~ if self.params['data']=='waveforms':
            #~ if ind_keep.size == 0 and not noise_visible:
                #~ self.plot.clear()
                #~ return
            #~ seg_nums = self.controller.spikes['segment'][ind_keep]
            #~ peak_sample_indexes = self.controller.spikes['index'][ind_keep]
            
            #~ if noise_visible:
                #~ noise_index = self.controller.some_noise_index
                #~ seg_nums = np.concatenate([seg_nums, noise_index['segment']], axis=0)
                #~ peak_sample_indexes = np.concatenate([peak_sample_indexes, noise_index['index']], axis=0)
            
            #~ data_kept = self.controller.get_some_waveforms(seg_nums, peak_sample_indexes, channel_indexes=common_channels)
            
            #~ if data_kept.size == 0:
                #~ self.plot.clear()
                #~ return
            #~ data_kept = data_kept.swapaxes(1,2).reshape(data_kept.shape[0], -1)
        
        #~ elif self.params['data']=='features':
            #~ data = self.controller.some_features
            #~ if data is None:
                #~ self.plot.clear()
                #~ return

            #~ labels = self.controller.spike_label[self.controller.some_peaks_index]
            #~ keep = np.in1d(labels, visibles)
            #~ ind_keep,  = np.nonzero(keep)
            
            #~ nb_feature_by_channel = data.shape[1] // self.controller.nb_channel
            #~ mask_feat = np.zeros(data.shape[1], dtype='bool')
            #~ for i in range(nb_feature_by_channel):
                #~ mask_feat[common_channels*nb_feature_by_channel+i] = True
            
            #~ data_kept = data[ind_keep, :][:, mask_feat]
            #~ if data_kept.size == 0:
                #~ self.plot.clear()
                #~ return
        
        waveforms = []
        for unit_id in visible_unit_ids:
            waveforms.append(self.controller.get_waveforms(unit_id)[:, :, common_channel_indexes])
        waveforms = np.concatenate(waveforms)
        data  = waveforms.swapaxes(1,2).reshape(waveforms.shape[0], -1)
        #~ print(data.shape)
        
        #TODO change for PCA
        #~ if self.params['data']=='waveforms':
            #~ bin_min, bin_max = self.params['bin_min'], self.params['bin_max']
            #~ bin_size = max(self.params['bin_size'], 0.01)
            #~ bins = np.arange(bin_min, bin_max, self.params['bin_size'])
            
        #~ elif self.params['data']=='features':
            #~ bin_min, bin_max = np.min(data_kept), np.max(data_kept)
            #~ bins = np.linspace(bin_min, bin_max, 500)
            #~ bin_size = bins[1]  - bins[0]

        bin_min, bin_max = self.params['bin_min'], self.params['bin_max']
        bin_size = max(self.params['bin_size'], 0.01)
        bins = np.arange(bin_min, bin_max, self.params['bin_size'])


        n = bins.size

        hist2d = np.zeros((data.shape[1], bins.size))
        indexes0 = np.arange(data.shape[1])
        
        data_bined = np.floor((data-bin_min)/bin_size).astype('int32')
        data_bined = data_bined.clip(0, bins.size-1)
        
        for d in data_bined:
            hist2d[indexes0, d] += 1
        
        #~ # for catalogue window only
        #~ if self.controller.unit_visible_dict.get(labelcodes.LABEL_NOISE, False) and self.controller.some_noise_snippet is not None:
            #~ if self.params['data']=='waveforms':
                #~ noise = self.controller.some_noise_snippet[:, :, common_channels]
                #~ noise = noise.swapaxes(1,2).reshape(noise.shape[0], -1)
                #~ noise_bined = np.floor((noise-bin_min)/bin_size).astype('int32')
                #~ noise_bined = noise_bined.clip(0, bins.size-1)
                #~ for d in noise_bined:
                    #~ hist2d[indexes0, d] += 1
            

        self.image.setImage(hist2d, lut=self.lut)#, levels=[0, self._max])
        #~ self.image.setRect(QT.QRectF(-0.5, bin_min, data_kept.shape[1], bin_max-bin_min))
        self.image.setRect(QT.QRectF(-0.5, bin_min, data.shape[1], bin_max-bin_min))
        self.image.show()
        
        
        #~ for k, curve in zip(visibles, [self.curve1, self.curve2]):
        
        #~ for k in visibles:
        #~ for unit_id in visible_unit_ids:
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if unit_id not in visible_unit_ids:
                continue
            
            
            #~ median, chans = self.controller.get_waveform_centroid(k, 'median', channels=common_channels)
            #~ if median is None:
                #~ continue
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            
            #~ if self.params['data']=='waveforms':
                #~ y = median.T.flatten()
            #~ else:
                #~ sel = labels[ind_keep] == k
                #~ y = np.median(data_kept[sel, :], axis=0)
            color = self.controller.qcolors.get(unit_id, QT.QColor( 'white'))
            
            y = template_avg.T.flatten()
            
            curve = pg.PlotCurveItem(x=indexes0, y=y, pen=pg.mkPen(color, width=2))
            self.plot.addItem(curve)
            self.curves.append(curve)
            
            #~ curve.setData()
            #~ curve.setPen()
            #~ curve.show()
        
        #~ if self.params['display_threshold'] and self.params['data']=='waveforms' :
            #~ self.thresh_line.show()
        #~ else:
            #~ self.thresh_line.hide()
        
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter        
        pos = 0
        for chan_ind, chan_id in enumerate(self.controller.channel_ids):
            label = self.channel_labels[chan_ind]
            if self.params['show_channel_id'] and chan_ind in common_channel_indexes:
                label.show()
                label.setPos(pos * width + nbefore, 0)
                pos += 1
            else:
                label.hide()
        
        #~ if self._x_range is None:
        if True:
            self._x_range = 0, indexes0[-1] #hist2d.shape[1]
            self._y_range = bin_min, bin_max
        

        self.plot.setXRange(*self._x_range, padding = 0.0)
        self.plot.setYRange(*self._y_range, padding = 0.0)
    
    def on_spike_selection_changed(self):
        pass

    def on_spike_label_changed(self):
        self.refresh()
        
    def on_colors_changed(self):
        self.refresh()
    
    def on_unit_visibility_changed(self):
        self.refresh()
    
    def on_cluster_tag_changed(self):
        pass

    def show_hide_1d_dist(self, v=None):
        #~ print(v)
        if v:
            self.graphicsview2.show()
        else:
            self.graphicsview2.hide()



WaveformHeatMapView._gui_help_txt = """Unit waveform heat map
Check density around the average template for each unit.
Usefull to check overlap between units.

right click : X/Y zoom
left clik : move
mouse wheel : color range for density (important!!)

For efficiency : no more than  4 units visible at same time.
This can be change in settings."""