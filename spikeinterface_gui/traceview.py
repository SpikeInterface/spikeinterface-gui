from .myqt import QT
import pyqtgraph as pg

import numpy as np
import time

from .base import WidgetBase
from .tools import TimeSeeker


# _trace_sources = ['preprocessed', 'raw']
_trace_sources = ['preprocessed']

class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal(float, float)
    gain_zoom = QT.pyqtSignal(float)
    xsize_zoom = QT.pyqtSignal(float)
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
    def mouseClickEvent(self, ev):
        ev.accept()
    def mouseDoubleClickEvent(self, ev):
        pos = self.mapToView(ev.pos())
        x, y = pos.x(), pos.y()
        self.doubleclicked.emit(x, y)
        ev.accept()
    def mouseDragEvent(self, ev):
        ev.ignore()
    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() == QT.Qt.ControlModifier:
            z = 10 if ev.delta()>0 else 1/10.
        else:
            z = 1.3 if ev.delta()>0 else 1/1.3
        self.gain_zoom.emit(z)
        ev.accept()
    def mouseDragEvent(self, ev):
        ev.accept()
        self.xsize_zoom.emit((ev.pos()-ev.lastPos()).x())


class TraceView(WidgetBase):
    
    _params = [{'name': 'auto_zoom_on_select', 'type': 'bool', 'value': True },
                       {'name': 'zoom_size', 'type': 'float', 'value':  0.08, 'step' : 0.001 },
                      {'name': 'plot_threshold', 'type': 'bool', 'value':  True },
                      {'name': 'alpha', 'type': 'float', 'value' : 0.8, 'limits':(0, 1.), 'step':0.05 },
                      {'name': 'xsize_max', 'type': 'float', 'value': 4.0, 'step': 1.0, 'limits':(1.0, np.inf)},
                      {'name': 'max_visible_channel', 'type': 'int', 'value':  16},
                      
                      
                      ]
    
    def __init__(self,controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
    
        self.trace_source = _trace_sources[0]
        
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
        
        #handle time by segments
        self.time_by_seg = np.array([0.]*self.controller.num_segments, dtype='float64')

        self.change_segment(0)
        self.refresh()
    
    _default_color = QT.QColor( 'white')
    
    def create_toolbar(self):
        tb = self.toolbar = QT.QToolBar()
        
        #Segment selection
        self.combo_seg = QT.QComboBox()
        tb.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {seg_index}' for seg_index in range(self.controller.num_segments) ])
        self._seg_index = 0
        self.seg_num = self._seg_index
        self.combo_seg.currentIndexChanged.connect(self.on_combo_seg_changed)
        tb.addSeparator()
        
        #~ self.combo_type = QT.QComboBox()
        #~ tb.addWidget(self.combo_type)
        #~ self.combo_type.addItems([ trace_source for trace_source in _trace_sources ])
        #~ self.combo_type.setCurrentIndex(_trace_sources.index(self.trace_source))
        #~ self.combo_type.currentIndexChanged.connect(self.on_combo_type_changed)

        # time slider
        self.timeseeker = TimeSeeker(show_slider=False)
        tb.addWidget(self.timeseeker)
        self.timeseeker.time_changed.connect(self.seek)
        
        # winsize
        self.xsize = .5
        tb.addWidget(QT.QLabel(u'X size (s)'))
        self.spinbox_xsize = pg.SpinBox(value = self.xsize, bounds = [0.001, self.params['xsize_max']], suffix = 's',
                            siPrefix = True, step = 0.1, dec = True)
        self.spinbox_xsize.sigValueChanged.connect(self.on_xsize_changed)
        tb.addWidget(self.spinbox_xsize)
        tb.addSeparator()
        self.spinbox_xsize.sigValueChanged.connect(self.refresh)
        
        #
        but = QT.QPushButton('auto scale')
        but.clicked.connect(self.auto_scale)
        tb.addWidget(but)
        
        self.layout.addWidget(self.toolbar)
        

    @property
    def visible_channel_inds(self):
        # TODO add option to order by depth
        inds = self.controller.visible_channel_inds
        n_max =self.params['max_visible_channel']
        if inds.size > n_max:
            inds = inds[:n_max]
        return inds
        
    
    def initialize_plot(self):
        self.viewBox = MyViewBox()
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        self.plot.showAxis('left', False)
        
        self.viewBox.doubleclicked.connect(self.scatter_item_clicked)
        
        
        self.viewBox.gain_zoom.connect(self.gain_zoom)
        self.viewBox.xsize_zoom.connect(self.xsize_zoom)
        
        self.signals_curve = pg.PlotCurveItem(pen='#7FFF00', connect='finite')
        self.plot.addItem(self.signals_curve)

        self.scatter = pg.ScatterPlotItem(size=10, pxMode = True)
        self.plot.addItem(self.scatter)
        #~ self.scatter.sigClicked.connect(self.scatter_item_clicked)
        
        self.channel_labels = []
        self.threshold_lines =[]
        for i, channel_id in enumerate(self.controller.channel_ids):
            label = pg.TextItem(f'{i}: {channel_id}', color='#FFFFFF', anchor=(0, 0.5), border=None, fill=pg.mkColor((128,128,128, 180)))
            self.plot.addItem(label)
            self.channel_labels.append(label)
        
        pen = pg.mkPen(color=(128,0,128, 120), width=3, style=QT.Qt.DashLine)
        self.selection_line = pg.InfiniteLine(pos = 0., angle=90, movable=False, pen = pen)
        self.plot.addItem(self.selection_line)
        self.selection_line.hide()
        
        self._initialize_plot()
        
        self.gains = None
        self.offsets = None

    def prev_segment(self):
        self.change_segment(self._seg_index - 1)
        
    def next_segment(self):
        self.change_segment(self._seg_index + 1)

    def change_segment(self, seg_pos):
        #TODO: dirty because now seg_pos IS seg_num
        self._seg_index  =  seg_pos
        if self._seg_index<0:
            self._seg_index = self.controller.num_segments-1
        if self._seg_index == self.controller.num_segments:
            self._seg_index = 0
        self.seg_num = self._seg_index
        self.combo_seg.setCurrentIndex(self._seg_index)
        
        length = self.controller.get_num_samples(self.seg_num)
        t_start = 0.
        t_stop = length/self.controller.sampling_frequency
        self.timeseeker.set_start_stop(t_start, t_stop, seek = False)

        self.scroll_time.setMinimum(0)
        self.scroll_time.setMaximum(length)
        
        if self.isVisible():
            self.refresh()
    
    def on_params_changed(self):
        # adjust xsize spinbox bounds, and adjust xsize if out of bounds
        self.spinbox_xsize.opts['bounds'] = [0.001, self.params['xsize_max']]
        if self.xsize > self.params['xsize_max']:
            self.spinbox_xsize.sigValueChanged.disconnect(self.on_xsize_changed)
            self.spinbox_xsize.setValue(self.params['xsize_max'])
            self.xsize = self.params['xsize_max']
            self.spinbox_xsize.sigValueChanged.connect(self.on_xsize_changed)
        
        self.reset_gain_and_offset()
        self.refresh()
    
    def on_combo_seg_changed(self):
        s =  self.combo_seg.currentIndex()
        self.change_segment(s)
    
    #~ def on_combo_type_changed(self):
        #~ s =  self.combo_type.currentIndex()
        #~ self.trace_source = _trace_sources[s]
        #~ self.estimate_auto_scale()
        #~ self.change_segment(self._seg_index)
    
    def on_xsize_changed(self):
        self.xsize = self.spinbox_xsize.value()
        if self.isVisible():
            self.refresh()
    
    def _refresh(self):
        self.seek(self.time_by_seg[self.seg_num])

    def xsize_zoom(self, xmove):
        factor = xmove/100.
        newsize = self.xsize*(factor+1.)
        limits = self.spinbox_xsize.opts['bounds']
        if newsize>0. and newsize<limits[1]:
            self.spinbox_xsize.setValue(newsize)
    
    def auto_scale(self):
        self.estimate_auto_scale()
        self.refresh()
    
    def estimate_auto_scale(self):

        #~ end_frame = min(int(1. * self.controller.sampling_frequency),
                #~ self.controller.get_num_samples(self.seg_num))
                
        #~ sigs = self.controller.get_traces(trace_source=self.trace_source, 
                #~ segment_index=self.seg_num, 
                #~ start_frame=0, end_frame=end_frame)

        #~ self.med = np.median(sigs, axis=0).astype('float32')
        #~ self.mad = np.median(np.abs(sigs - self.med),axis=0).astype('float32') * 1.4826
        
        self.med, self.mad = self.controller.estimate_noise()

        self.factor = 1.
        self.gain_zoom(15.)
    
    def gain_zoom(self, factor_ratio):
        self.factor *= factor_ratio
        self.reset_gain_and_offset()
        self.refresh()
        
    def reset_gain_and_offset(self):
        num_chans = len(self.controller.channel_ids)
        self.gains = np.zeros(num_chans, dtype='float32')
        self.offsets = np.zeros(num_chans, dtype='float32')
        
        n = self.visible_channel_inds.size
        self.gains[self.visible_channel_inds] = np.ones(n, dtype=float) * 1./(self.factor*max(self.mad))
        self.offsets[self.visible_channel_inds] = np.arange(n)[::-1] - self.med[self.visible_channel_inds]*self.gains[self.visible_channel_inds]
        
    def on_scroll_time(self, val):
        sr = self.controller.sampling_frequency
        self.timeseeker.seek(val/sr)
    
    def scatter_item_clicked(self, x, y):
        ind_click = int(x*self.controller.sampling_frequency )
        in_seg, = np.nonzero(self.controller.spikes['segment_index'] == self.seg_num)
        nearest = np.argmin(np.abs(self.controller.spikes[in_seg]['sample_index'] - ind_click))
        
        ind_spike_nearest = in_seg[nearest]
        sample_index = self.controller.spikes[ind_spike_nearest]['sample_index']
        
        if np.abs(ind_click - sample_index) > (self.controller.sampling_frequency // 30):
            return
        
        #~ self.controller.spikes['selected'][:] = False
        #~ self.controller.spikes['selected'][ind_spike_nearest] = True
        self.controller.set_indices_spike_selected([ind_spike_nearest])
        
        self.spike_selection_changed.emit()
        self.refresh()
    
    def on_spike_selection_changed(self):
        
        #~ ind_selected, = np.nonzero(self.controller.spikes['selected'])
        ind_selected = self.controller.get_indices_spike_selected()
        n_selected = ind_selected.size
        
        if self.params['auto_zoom_on_select'] and n_selected==1:
            #~ ind_selected, = np.nonzero(self.controller.spikes['selected'])
            ind = ind_selected[0]
            peak_ind = self.controller.spikes[ind]['sample_index']
            seg_num = self.controller.spikes[ind]['segment_index']
            peak_time = peak_ind / self.controller.sampling_frequency
            unit_index = self.controller.spikes[ind]['unit_index']
            unit_id = self.controller.unit_ids[unit_index ]
            
            if seg_num != self.seg_num:
                self.combo_seg.setCurrentIndex(seg_num)
            
            self.spinbox_xsize.sigValueChanged.disconnect(self.on_xsize_changed)
            self.spinbox_xsize.setValue(self.params['zoom_size'])
            self.xsize = self.params['zoom_size']
            self.spinbox_xsize.sigValueChanged.connect(self.on_xsize_changed)
            
            self.seek(peak_time)
            
        else:
            self.refresh()

    def on_channel_visibility_changed(self):
        self.reset_gain_and_offset()
        self.refresh()
    
    def seek(self, t):
        if self.sender() is not self.timeseeker:
            self.timeseeker.seek(t, emit = False)
        
        self.time_by_seg[self.seg_num] = t
        t1,t2 = t-self.xsize/3. , t+self.xsize*2/3.
        t_start = 0.
        sr = self.controller.sampling_frequency

        self.scroll_time.valueChanged.disconnect(self.on_scroll_time)
        self.scroll_time.setValue(int(sr*t))
        self.scroll_time.setPageStep(int(sr*self.xsize))
        self.scroll_time.valueChanged.connect(self.on_scroll_time)
        
        ind1 = max(0, int((t1-t_start)*sr))
        ind2 = int((t2-t_start)*sr)

        sigs_chunk = self.controller.get_traces(trace_source=self.trace_source, 
                segment_index=self.seg_num, 
                start_frame=ind1, end_frame=ind2)


        
        if sigs_chunk is None: 
            return
        
        if self.gains is None:
            self.estimate_auto_scale()

        nb_visible = self.visible_channel_inds.size
        
        data_curves = sigs_chunk[:, self.visible_channel_inds].T.copy()
        
        
        
        if data_curves.dtype!='float32':
            data_curves = data_curves.astype('float32')
        
        data_curves *= self.gains[self.visible_channel_inds, None]
        data_curves += self.offsets[self.visible_channel_inds, None]
        
        connect = np.ones(data_curves.shape, dtype='bool')
        connect[:, -1] = 0
        
        times_chunk = np.arange(sigs_chunk.shape[0], dtype='float64')/self.controller.sampling_frequency+max(t1, 0)
        times_chunk_tile = np.tile(times_chunk, nb_visible)
        self.signals_curve.setData(times_chunk_tile, data_curves.flatten(), connect=connect.flatten())
        
        #channel labels
        for chan_ind, chan_id in enumerate(self.controller.channel_ids):
            self.channel_labels[chan_ind].hide()
        
        for i, chan_ind in enumerate(self.visible_channel_inds):
            self.channel_labels[chan_ind].setPos(t1, nb_visible - 1 - i)
            self.channel_labels[chan_ind].show()
        
        # plot peak on signal
        all_spikes = self.controller.spikes

        keep = (all_spikes['segment_index']==self.seg_num) & (all_spikes['sample_index']>=ind1) & (all_spikes['sample_index']<ind2)
        spikes_chunk = all_spikes[keep].copy()
        spikes_chunk['sample_index'] -= ind1
        
        self.scatter.clear()
        all_x = []
        all_y = []
        all_brush = []
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                continue
            
            unit_mask = (spikes_chunk['unit_index'] == unit_index)
            if np.sum(unit_mask)==0:
                continue
            
            channel_inds = spikes_chunk['channel_index'][unit_mask]
            sample_inds = spikes_chunk['sample_index'][unit_mask]
            
            chan_mask = np.in1d(channel_inds, self.visible_channel_inds)
            if not np.any(chan_mask):
                continue
            channel_inds = channel_inds[chan_mask]
            sample_inds = sample_inds[chan_mask]
            
            x = times_chunk[sample_inds]
            y = sigs_chunk[sample_inds, channel_inds] * self.gains[channel_inds] + self.offsets[channel_inds]

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
            
            
            if np.sum(spikes_chunk['selected']) == 1:
                sample_index = spikes_chunk['sample_index'][spikes_chunk['selected']][0]
                t = times_chunk[sample_index]
                self.selection_line.setPos(t)
                self.selection_line.show()
            else:
                self.selection_line.hide()            

        #ranges
        self.plot.setXRange( t1, t2, padding = 0.0)
        self.plot.setYRange(-.5, nb_visible-.5, padding = 0.0)
        
    
    def _initialize_plot(self):
        self.curve_predictions = pg.PlotCurveItem(pen='#FF00FF', connect='finite')
        self.plot.addItem(self.curve_predictions)
        self.curve_residuals = pg.PlotCurveItem(pen='#FFFF00', connect='finite')
        self.plot.addItem(self.curve_residuals)

    
TraceView._gui_help_txt = """Trace view
Show trace and spike (on best channel) of visible units.
Mouse right lick : zoom
Scroll bar at bottom : navigate on time
channel visibility is done vwith probe view
double click : pick on spike"""
