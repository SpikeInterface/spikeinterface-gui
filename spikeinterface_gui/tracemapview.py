from .myqt import QT
import pyqtgraph as pg

import numpy as np
import time

import matplotlib.cm
import matplotlib.colors


from .base import WidgetBase
from .tools import TimeSeeker
from .traceview import MixinViewTrace


class TraceMapView(WidgetBase, MixinViewTrace):
    _depend_on = ['recording']
    
    _params = [
        {'name': 'auto_zoom_on_select', 'type': 'bool', 'value': True },
        {'name': 'zoom_size', 'type': 'float', 'value':  0.03, 'step' : 0.001 },
        # {'name': 'plot_threshold', 'type': 'bool', 'value':  True },
        {'name': 'alpha', 'type': 'float', 'value' : 0.8, 'limits':(0, 1.), 'step':0.05 },
        {'name': 'xsize_max', 'type': 'float', 'value': 4.0, 'step': 1.0, 'limits':(1.0, np.inf)},
        # {'name': 'max_visible_channel', 'type': 'int', 'value':  16},
        {'name': 'colormap', 'type': 'list', 'limits' : ['gray', 'bwr',  'PiYG', 'jet', 'hot', ] },
        {'name': 'reverse_colormap', 'type': 'bool', 'value': True },
        {'name': 'show_on_selected_units', 'type': 'bool', 'value': True },
    ]
    
    def __init__(self,controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)

        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.create_toolbar()
        
        
        # create graphic view and 2 scroll bar
        g = QT.QGridLayout()
        self.layout.addLayout(g)
        self.graphicsview = pg.GraphicsView()
        g.addWidget(self.graphicsview, 0,1)
        self.initialize_plot()
        self.scroll_time = QT.QScrollBar(orientation=QT.Qt.Horizontal)
        g.addWidget(self.scroll_time, 1,1)
        self.scroll_time.valueChanged.connect(self.on_scroll_time)



        pos = self.controller.get_contact_location()
        self.channel_order = np.lexsort((-pos[:, 0], pos[:, 1], ))
        self.channel_order_reverse = np.argsort(self.channel_order, kind="stable")
        


        #handle time by segments
        self.time_by_seg = np.array([0.]*self.controller.num_segments, dtype='float64')

        self.on_params_changed(do_refresh=False)
        #this do refresh
        self.change_segment(0)
        self.color_limit = None

    @property
    def visible_channel_inds(self):
        inds = self.controller.visible_channel_inds
        return inds


    def on_params_changed(self, do_refresh=True):

        self.spinbox_xsize.opts['bounds'] = [0.001, self.params['xsize_max']]
        if self.xsize > self.params['xsize_max']:
            self.spinbox_xsize.sigValueChanged.disconnect(self.on_xsize_changed)
            self.spinbox_xsize.setValue(self.params['xsize_max'])
            self.xsize = self.params['xsize_max']
            self.spinbox_xsize.sigValueChanged.connect(self.on_xsize_changed)


        N = 512
        cmap_name = self.params['colormap']
        cmap = matplotlib.colormaps[cmap_name].resampled(N)
        lut = []
        for i in range(N):
            r,g,b,_ =  matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r*255,g*255,b*255])
        self.lut = np.array(lut, dtype='uint8')
        if self.params['reverse_colormap']:
            self.lut = self.lut[::-1]


        if do_refresh:
            self.refresh()

    def on_spike_selection_changed(self):
        self.seek_with_selected_spike()


    def scatter_item_clicked(self, x, y):
        pass
    
    def _initialize_plot(self):
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        self.scatter = pg.ScatterPlotItem(size=10, pxMode = True)
        self.plot.addItem(self.scatter)



    def gain_zoom(self, factor_ratio, ):
        if self.color_limit is None:
            return
        self.color_limit = self.color_limit * factor_ratio
        self.image.setLevels([-self.color_limit, self.color_limit], update=True)
        self.refresh()

    def auto_scale(self):
        self.seek(self.time_by_seg[self.seg_num], auto_scale=True)

    def _refresh(self):
        self.seek(self.time_by_seg[self.seg_num])

    def seek(self, t, auto_scale=False):
        if self.sender() is not self.timeseeker:
            self.timeseeker.seek(t, emit=False)

        self.time_by_seg[self.seg_num] = t
        t1,t2 = t-self.xsize/3. , t+self.xsize*2/3.
        t_start = 0.
        sr = self.controller.sampling_frequency

        self.scroll_time.valueChanged.disconnect(self.on_scroll_time)
        self.scroll_time.setValue(int(sr*t))
        self.scroll_time.setPageStep(int(sr*self.xsize))
        self.scroll_time.valueChanged.connect(self.on_scroll_time)
        
        ind1 = max(0, int((t1-t_start)*sr))
        ind2 = min(self.controller.get_num_samples(self.seg_num), int((t2-t_start)*sr))

        sigs_chunk = self.controller.get_traces(trace_source='preprocessed',
                segment_index=self.seg_num, 
                start_frame=ind1, end_frame=ind2)

        if sigs_chunk is None: 
            self.image.hide()
            return
        
        data_curves = sigs_chunk[:, self.channel_order]

        times_chunk = np.arange(sigs_chunk.shape[0], dtype='float64')/self.controller.sampling_frequency+max(t1, 0)
        real_t1 = max(t1, 0)
        real_t2 = real_t1 + sigs_chunk.shape[0] / self.controller.sampling_frequency

        if self.color_limit is None or auto_scale:
            self.color_limit = np.max(np.abs(data_curves))

        if data_curves.dtype != 'float32':
            data_curves = data_curves.astype('float32')
        
        num_chans = data_curves.shape[1]

        self.image.setImage(data_curves, lut=self.lut, levels=[-self.color_limit, self.color_limit])
        self.image.setRect(QT.QRectF(real_t1, 0, real_t2-real_t1, num_chans))
        self.image.show()

        # plot peaks
        sl = self.controller.segment_slices[self.seg_num]
        spikes_seg = self.controller.spikes[sl]
        i1, i2 = np.searchsorted(spikes_seg['sample_index'], [ind1, ind2])
        spikes_chunk = spikes_seg[i1:i2].copy()
        spikes_chunk['sample_index'] -= ind1

        

        self.scatter.clear()
        all_x = []
        all_y = []
        all_brush = []
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if self.params['show_on_selected_units'] and not self.controller.unit_visible_dict[unit_id]:
                continue
            
            unit_mask = (spikes_chunk['unit_index'] == unit_index)
            if np.sum(unit_mask)==0:
                continue
            
            channel_inds = spikes_chunk['channel_index'][unit_mask]
            sample_inds = spikes_chunk['sample_index'][unit_mask]
            
            # chan_mask = np.isin(channel_inds, self.visible_channel_inds)
            # if not np.any(chan_mask):
            #     continue
            # channel_inds = channel_inds[chan_mask]
            # sample_inds = sample_inds[chan_mask]
            
            x = times_chunk[sample_inds]
            # print(channel_inds)
            y = self.channel_order_reverse[channel_inds] + 0.5
            # print(y)


            color = QT.QColor(self.controller.qcolors.get(unit_id, self._default_color))
            color.setAlpha(int(self.params['alpha']*255))
            
            all_x.append(x)
            all_y.append(y)
            all_brush.append(np.array([pg.mkBrush(color)]*len(x)))

        if len(all_x) > 0:
            all_x = np.concatenate(all_x)
            all_y = np.concatenate(all_y)
            all_brush = np.concatenate(all_brush)
            self.scatter.setData(x=all_x, y=all_y, brush=all_brush)


        #ranges
        self.plot.setXRange( t1, t2, padding = 0.0)
        self.plot.setYRange(0, num_chans, padding = 0.0)



        # data_curves *= self.gains[self.visible_channel_inds, None]
        # data_curves += self.offsets[self.visible_channel_inds, None]
        
        # connect = np.ones(data_curves.shape, dtype='bool')
        # connect[:, -1] = 0
        
        # times_chunk = np.arange(sigs_chunk.shape[0], dtype='float64')/self.controller.sampling_frequency+max(t1, 0)
        # times_chunk_tile = np.tile(times_chunk, nb_visible)
        # self.signals_curve.setData(times_chunk_tile, data_curves.flatten(), connect=connect.flatten())
        
        #channel labels
        # for chan_ind, chan_id in enumerate(self.controller.channel_ids):
        #     self.channel_labels[chan_ind].hide()
        
        # for i, chan_ind in enumerate(self.visible_channel_inds):
        #     self.channel_labels[chan_ind].setPos(t1, nb_visible - 1 - i)
        #     self.channel_labels[chan_ind].show()
        
        # plot peak on signal
        # all_spikes = self.controller.spikes

        # keep = (all_spikes['segment_index']==self.seg_num) & (all_spikes['sample_index']>=ind1) & (all_spikes['sample_index']<ind2)
        # spikes_chunk = all_spikes[keep].copy()
        # spikes_chunk['sample_index'] -= ind1
        
        # self.scatter.clear()
        # all_x = []
        # all_y = []
        # all_brush = []
        # for unit_index, unit_id in enumerate(self.controller.unit_ids):
        #     if not self.controller.unit_visible_dict[unit_id]:
        #         continue
            
        #     unit_mask = (spikes_chunk['unit_index'] == unit_index)
        #     if np.sum(unit_mask)==0:
        #         continue
            
        #     channel_inds = spikes_chunk['channel_index'][unit_mask]
        #     sample_inds = spikes_chunk['sample_index'][unit_mask]
            
        #     chan_mask = np.isin(channel_inds, self.visible_channel_inds)
        #     if not np.any(chan_mask):
        #         continue
        #     channel_inds = channel_inds[chan_mask]
        #     sample_inds = sample_inds[chan_mask]
            
        #     x = times_chunk[sample_inds]
        #     y = sigs_chunk[sample_inds, channel_inds] * self.gains[channel_inds] + self.offsets[channel_inds]

        #     color = QT.QColor(self.controller.qcolors.get(unit_id, self._default_color))
        #     color.setAlpha(int(self.params['alpha']*255))
            
        #     all_x.append(x)
        #     all_y.append(y)
        #     all_brush.append(np.array([pg.mkBrush(color)]*len(x)))
            
        # if len(all_x) > 0:
        #     all_x = np.concatenate(all_x)
        #     all_y = np.concatenate(all_y)
        #     all_brush = np.concatenate(all_brush)
        #     self.scatter.setData(x=all_x, y=all_y, brush=all_brush)
            
        #     if np.sum(spikes_chunk['selected']) == 1:
        #         sample_index = spikes_chunk['sample_index'][spikes_chunk['selected']][0]
        #         t = times_chunk[sample_index]
        #         self.selection_line.setPos(t)
        #         self.selection_line.show()
        #     else:
        #         self.selection_line.hide()            

