import numpy as np

import matplotlib.cm
import matplotlib.colors

from .view_base import ViewBase

from .traceview import MixinViewTrace


class TraceMapView(ViewBase, MixinViewTrace):

    _supported_backend = ['qt']
    _depend_on = ['recording']
    _settings = [
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


    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        MixinViewTrace.__init__(self)


    def make_color_lut(self):
        N = 512
        cmap_name = self.settings['colormap']
        cmap = matplotlib.colormaps[cmap_name].resampled(N)
        lut = []
        for i in range(N):
            r,g,b,_ =  matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r*255,g*255,b*255])
        self.lut = np.array(lut, dtype='uint8')
        if self.settings['reverse_colormap']:
            self.lut = self.lut[::-1]


    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()
        
        self._qt_create_toolbar()
        
        
        # create graphic view and 2 scroll bar
        g = QT.QGridLayout()
        self.layout.addLayout(g)
        self.graphicsview = pg.GraphicsView()
        g.addWidget(self.graphicsview, 0,1)
        self._qt_initialize_plot()
        self.scroll_time = QT.QScrollBar(orientation=QT.Qt.Horizontal)
        g.addWidget(self.scroll_time, 1,1)
        self.scroll_time.valueChanged.connect(self._qt_on_scroll_time)



        pos = self.controller.get_contact_location()
        self.channel_order = np.lexsort((-pos[:, 0], pos[:, 1], ))
        self.channel_order_reverse = np.argsort(self.channel_order, kind="stable")
        
        self.make_color_lut()


        #handle time by segments
        self.time_by_seg = np.array([0.]*self.controller.num_segments, dtype='float64')

        # self.on_params_changed(do_refresh=False)
        #this do refresh
        self._qt_change_segment(0)
        self.color_limit = None

    def _qt_initialize_plot(self):
        MixinViewTrace._qt_initialize_plot(self)
        import pyqtgraph as pg
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        self.scatter = pg.ScatterPlotItem(size=10, pxMode = True)
        self.plot.addItem(self.scatter)

    def _on_settings_changed_qt(self, do_refresh=True):

        self.spinbox_xsize.opts['bounds'] = [0.001, self.settings['xsize_max']]
        if self.xsize > self.settings['xsize_max']:
            self.spinbox_xsize.sigValueChanged.disconnect(self.on_xsize_changed)
            self.spinbox_xsize.setValue(self.settings['xsize_max'])
            self.xsize = self.settings['xsize_max']
            self.spinbox_xsize.sigValueChanged.connect(self.on_xsize_changed)

        self.make_color_lut()

        if do_refresh:
            self.refresh()

    def _qt_on_spike_selection_changed(self):
        print('tracemap _qt_on_spike_selection_changed')
        self._qt_seek_with_selected_spike()


    def _qt_scatter_item_clicked(self, x, y):
        # useless but needed for the MixinViewTrace
        pass


    def _qt_gain_zoom(self, factor_ratio, ):
        if self.color_limit is None:
            return
        self.color_limit = self.color_limit * factor_ratio
        self.image.setLevels([-self.color_limit, self.color_limit], update=True)
        self.refresh()

    def _qt_auto_scale(self):
        self._qt_seek(self.time_by_seg[self.seg_num], auto_scale=True)

    def _qt_refresh(self):
        self._qt_seek(self.time_by_seg[self.seg_num])

    def _qt_seek(self, t, auto_scale=False):
        from .myqt import QT
        import pyqtgraph as pg

        if self.qt_widget.sender() is not self.timeseeker:
            self.timeseeker.seek(t, emit=False)

        self.time_by_seg[self.seg_num] = t
        t1,t2 = t-self.xsize/3. , t+self.xsize*2/3.
        t_start = 0.
        sr = self.controller.sampling_frequency

        self.scroll_time.valueChanged.disconnect(self._qt_on_scroll_time)
        self.scroll_time.setValue(int(sr*t))
        self.scroll_time.setPageStep(int(sr*self.xsize))
        self.scroll_time.valueChanged.connect(self._qt_on_scroll_time)
        
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
            if self.settings['show_on_selected_units'] and not self.controller.unit_visible_dict[unit_id]:
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


            # color = QT.QColor(self.controller.qcolors.get(unit_id, self._default_color))
            color = QT.QColor(self.get_unit_color(unit_id))
            color.setAlpha(int(self.settings['alpha']*255))
            
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

