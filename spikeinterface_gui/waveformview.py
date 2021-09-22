from .myqt import QT
import pyqtgraph as pg

import numpy as np
import pandas as pd

from .base import WidgetBase


class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    gain_zoom = QT.pyqtSignal(float)
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        #~ self.disableAutoRange()
    def mouseClickEvent(self, ev):
        ev.accept()
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    #~ def mouseDragEvent(self, ev):
        #~ ev.ignore()
    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() == QT.Qt.ControlModifier:
            z = 10 if ev.delta()>0 else 1/10.
        else:
            z = 1.3 if ev.delta()>0 else 1/1.3
        self.gain_zoom.emit(z)
        ev.accept()



class WaveformView(WidgetBase):

    _params = [{'name': 'plot_selected_spike', 'type': 'bool', 'value': True },
                        {'name': 'show_only_selected_cluster', 'type': 'bool', 'value': True},
                      {'name': 'plot_limit_for_flatten', 'type': 'bool', 'value': True },
                      {'name': 'metrics', 'type': 'list', 'values': ['median/mad'] },
                      {'name': 'fillbetween', 'type': 'bool', 'value': True },
                      {'name': 'show_channel_id', 'type': 'bool', 'value': False},
                      {'name': 'flip_bottom_up', 'type': 'bool', 'value': False},
                      {'name': 'display_threshold', 'type': 'bool', 'value' : True },
                      {'name': 'sparse_display', 'type': 'bool', 'value' : True },
                      ]
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        #~ self.create_settings()
        
        self.create_toolbar()
        self.layout.addWidget(self.toolbar)

        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        self.initialize_plot()
        
        self.alpha = 60
        self.refresh()
    
    def create_toolbar(self):
        tb = self.toolbar = QT.QToolBar()
        
        #Mode flatten or geometry
        self.combo_mode = QT.QComboBox()
        tb.addWidget(self.combo_mode)
        #~ self.mode = 'flatten'
        #~ self.combo_mode.addItems([ 'flatten', 'geometry'])
        self.mode = 'geometry'
        self.combo_mode.addItems([ 'geometry', 'flatten'])
        self.combo_mode.currentIndexChanged.connect(self.on_combo_mode_changed)
        tb.addSeparator()
        
        
        but = QT.QPushButton('settings')
        but.clicked.connect(self.open_settings)
        tb.addWidget(but)

        but = QT.QPushButton('scale')
        but.clicked.connect(self.zoom_range)
        tb.addWidget(but)

        but = QT.QPushButton('refresh')
        but.clicked.connect(self.refresh)
        tb.addWidget(but)
    
    def on_combo_mode_changed(self):
        self.mode = str(self.combo_mode.currentText())
        self.initialize_plot()
        self.refresh()
    
    def on_params_changed(self, params, changes):
        for param, change, data in changes:
            if change != 'value': continue
            if param.name()=='flip_bottom_up':
                self.initialize_plot()
        self.refresh()

    def initialize_plot(self):
        #~ print('WaveformViewer.initialize_plot', self.controller.some_waveforms)
        #~ if self.controller.get_waveform_left_right()[0] is None:
            #~ return
        
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        
        self.viewBox1 = MyViewBox()
        self.viewBox1.disableAutoRange()

        grid = pg.GraphicsLayout(border=(100,100,100))
        self.graphicsview.setCentralItem(grid)
        
        self.plot1 = grid.addPlot(row=0, col=0, rowspan=2, viewBox=self.viewBox1)
        self.plot1.hideButtons()
        self.plot1.showAxis('left', True)

        self.curve_one_waveform = pg.PlotCurveItem([], [], pen=pg.mkPen(QT.QColor( 'white'), width=1), connect='finite')
        self.plot1.addItem(self.curve_one_waveform)
        
        if self.mode=='flatten':
            grid.nextRow()
            grid.nextRow()
            self.viewBox2 = MyViewBox()
            self.viewBox2.disableAutoRange()
            self.plot2 = grid.addPlot(row=2, col=0, rowspan=1, viewBox=self.viewBox2)
            self.plot2.hideButtons()
            self.plot2.showAxis('left', True)
            self.viewBox2.setXLink(self.viewBox1)
            self.factor_y = 1.
            
            self._common_channel_indexes_flat = None

        elif self.mode=='geometry':
            self.plot2 = None
            
            #~ chan_grp = self.controller.chan_grp
            #~ channel_group = self.controller.dataio.channel_groups[chan_grp]
            #~ print(channel_group['geometry'])
            #~ if channel_group['geometry'] is None:
                #~ print('no geometry')
                #~ self.xvect = None
            #~ else:
            if 1:

                #~ n_left, n_right = self.controller.get_waveform_left_right()
                #~ width = n_right - n_left
                #~ nb_channel = self.controller.nb_channel
                num_chan = len(self.controller.channel_ids)
                
                #~ self.xvect = np.zeros(shape[0]*shape[1], dtype='float32')
                #~ self.xvect = np.zeros((shape[1], shape[0]), dtype='float32')
                self.xvect = np.zeros((num_chan, width), dtype='float32')
                
                
                self.contact_location = self.controller.get_contact_location().copy()
                #~ self.contact_location = []
                #~ for i, chan in enumerate(self.controller.channel_indexes):
                    #~ x, y = channel_group['geometry'][chan]
                    #~ self.contact_location.append([x, y])
                #~ self.contact_location = np.array(self.contact_location, dtype='float64')
                
                if self.params['flip_bottom_up']:
                    self.contact_location[:, 1] *= -1.
                
                xpos = self.contact_location[:,0]
                ypos = self.contact_location[:,1]
                
                if np.unique(xpos).size>1:
                    self.delta_x = np.min(np.diff(np.sort(np.unique(xpos))))
                else:
                    self.delta_x = np.unique(xpos)[0]
                if np.unique(ypos).size>1:
                    self.delta_y = np.min(np.diff(np.sort(np.unique(ypos))))
                else:
                    self.delta_y = max(np.unique(ypos)[0], 1)
                self.factor_y = .05
                if self.delta_x>0.:
                    #~ espx = self.delta_x/2. *.95
                    espx = self.delta_x/2.5
                else:
                    espx = .5
                #~ for i, chan in enumerate(channel_group['channels']):
                for chan_ind, chan_id in enumerate(self.controller.channel_ids):
                    #~ x, y = channel_group['geometry'][chan]
                    x, y = self.contact_location[chan_ind, :]
                    self.xvect[chan_ind, :] = np.linspace(x-espx, x+espx, num=width)

        self.wf_min, self.wf_max = self.controller.get_waveforms_range()
        
        self._x_range = None
        self._y1_range = None
        self._y2_range = None
        
        self.viewBox1.gain_zoom.connect(self.gain_zoom)
        
        self.viewBox1.doubleclicked.connect(self.open_settings)
        
        #~ self.viewBox.xsize_zoom.connect(self.xsize_zoom)    
    

    def gain_zoom(self, factor_ratio):
        self.factor_y *= factor_ratio
        
        self.refresh(keep_range=True)
    
    def zoom_range(self):
        self._x_range = None
        self._y1_range = None
        self._y2_range = None
        self.refresh(keep_range=False)
    
    def refresh(self, keep_range=False):
        
        if not hasattr(self, 'viewBox1'):
            self.initialize_plot()
        
        if not hasattr(self, 'viewBox1'):
            return
        
        n_selected = np.sum(self.controller.spikes['selected'])
        
        if self.params['show_only_selected_cluster'] and n_selected==1:
            unit_visible_dict = {k:False for k in self.controller.unit_visible_dict}
            ind, = np.nonzero(self.controller.spikes['selected'])
            ind = ind[0]
            unit_index = self.controller.spikes[ind]['unit_index']
            unit_id = self.controller.unit_ids[unit_index]
            unit_visible_dict[unit_id] = True
        else:
            unit_visible_dict = self.controller.unit_visible_dict
        
        if self.mode=='flatten':
            self.plot1.setAspectLocked(lock=False, ratio=None)
            self.refresh_mode_flatten(unit_visible_dict, keep_range)
        elif self.mode=='geometry':
            self.plot1.setAspectLocked(lock=True, ratio=1)
            self.refresh_mode_geometry(unit_visible_dict, keep_range)
        
        self._refresh_one_spike(n_selected)
    
    
    def refresh_mode_flatten(self, unit_visible_dict, keep_range):
        if self._x_range is not None and keep_range:
            #this may change with pyqtgraph
            self._x_range = tuple(self.viewBox1.state['viewRange'][0])
            self._y1_range = tuple(self.viewBox1.state['viewRange'][1])
            self._y2_range = tuple(self.viewBox2.state['viewRange'][1])
        
        
        self.plot1.clear()
        self.plot2.clear()
        self.plot1.addItem(self.curve_one_waveform)
        
        #~ if self.controller.spike_index ==[]:
            #~ return

        #~ nb_channel = self.controller.nb_channel
        
        #~ n_left, n_right = self.controller.get_waveform_left_right()
        #~ width = n_right - n_left
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        
        
        #~ sparse = self.controller.have_sparse_template and self.params['sparse_display']
        sparse = self.params['sparse_display']
        
        # visibles = [k for k, v in unit_visible_dict.items() if v and k>=-1 ]
        visible_unit_ids = [unit_id for unit_id, v in unit_visible_dict.items() if v ]
        
        
        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                return
        else:
            #~ common_channel_indexes = self.controller.channels
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype='int64')
        
        self._common_channel_indexes_flat = common_channel_indexes
        
        #lines
        def addSpan(plot):
            white = pg.mkColor(255, 255, 255, 20)
            #~ for i in range(nb_channel):
            for i, c in enumerate(common_channel_indexes):
                if i%2==1:
                    region = pg.LinearRegionItem([width*i, width*(i+1)-1], movable = False, brush = white)
                    plot.addItem(region, ignoreBounds=True)
                    for l in region.lines:
                        l.setPen(white)
                vline = pg.InfiniteLine(pos = nbefore + width*i, angle=90, movable=False, pen = pg.mkPen('w'))
                plot.addItem(vline)
        
        if self.params['plot_limit_for_flatten']:
            addSpan(self.plot1)
            addSpan(self.plot2)
        
        #~ if self.params['display_threshold']:
            #~ thresh = self.controller.get_threshold()
            #~ thresh_line = pg.InfiniteLine(pos=thresh, angle=0, movable=False, pen = pg.mkPen('w'))
            #~ self.plot1.addItem(thresh_line)

            
            
        
        
        #waveforms
        
        #~ if self.params['metrics']=='median/mad':
            #~ key1, key2 = 'median', 'mad'
        #~ elif self.params['metrics']=='mean/std':
            #~ key1, key2 = 'mean', 'std'
        
        #~ shape = self.controller.get_waveforms_shape()
        #~ if shape is None:
            #~ return
        #~ n_left, n_right = self.controller.get_waveform_left_right()
        #~ if n_left is None:
            #~ return
        #~ width = n_right - n_left

        shape = (width, len(common_channel_indexes))
        xvect = np.arange(shape[0]*shape[1])
        
        #~ for i,k in enumerate(self.controller.centroids):
        #~ for unit_id in unit_visible_dict:
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            #~ if not self.controller.unit_visible_dict[k]:
            if not unit_visible_dict[unit_id]:
                continue
            
            #~ wf0 = self.controller.centroids[k][key1].T.flatten()
            #~ mad = self.controller.centroids[k][key2].T.flatten()
            #~ wf0, chans = self.controller.get_waveform_centroid(k, key1, channels=common_channel_indexes)
            #~ if wf0 is None: continue
            #~ wf0 = wf0.T.flatten()
            
            #~ mad, chans = self.controller.get_waveform_centroid(k, key2, channels=common_channel_indexes)
            
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            template_std = self.controller.templates_std[unit_index, :, :][:, common_channel_indexes]
            
            #~ wf0 = template_avg.T.flatten()
            
            color = self.controller.qcolors.get(unit_id, QT.QColor( 'white'))
            curve = pg.PlotCurveItem(xvect, template_avg.T.flatten(), pen=pg.mkPen(color, width=2))
            self.plot1.addItem(curve)
            
            
            #~ if self.params['fillbetween'] and mad is not None:
            if self.params['fillbetween']:
                #~ template_std = template_std.T.flatten()
                color2 = QT.QColor(color)
                color2.setAlpha(self.alpha)
                curve1 = pg.PlotCurveItem(xvect, template_avg.T.flatten() + template_std.T.flatten(), pen=color2)
                curve2 = pg.PlotCurveItem(xvect, template_avg.T.flatten() - template_std.T.flatten(), pen=color2)
                self.plot1.addItem(curve1)
                self.plot1.addItem(curve2)
                
                fill = pg.FillBetweenItem(curve1=curve1, curve2=curve2, brush=color2)
                self.plot1.addItem(fill)
            
            if template_std is not None:
                curve = pg.PlotCurveItem(xvect, template_std.T.flatten(), pen=color)
                self.plot2.addItem(curve)        

        if self.params['show_channel_id']:
            #~ cn = self.controller.channel_indexes_and_names
            #~ for i, c in enumerate(common_channel_indexes):
            for i, chan_ind in enumerate(common_channel_indexes):
                chan_id = self.controller.channel_ids[chan_ind]
                # chan i sabsolut chan
                #~ chan, name = cn[c]
            #~ for i, (chan, name) in enumerate(self.controller.channel_indexes_and_names):
                itemtxt = pg.TextItem(f'{chan_id}', anchor=(.5,.5), color='#FFFF00')
                itemtxt.setFont(QT.QFont('', pointSize=12))
                self.plot1.addItem(itemtxt)
                itemtxt.setPos(width * i +nbefore, 0)

        
        if self._x_range is None or not keep_range :
            if xvect.size>0:
                self._x_range = xvect[0], xvect[-1]
                self._y1_range = self.wf_min*1.1, self.wf_max*1.1
                self._y2_range = 0., 5.
        
        if self._x_range is not None:
            self.plot1.setXRange(*self._x_range, padding = 0.0)
            self.plot1.setYRange(*self._y1_range, padding = 0.0)
            self.plot2.setYRange(*self._y2_range, padding = 0.0)

        

    def refresh_mode_geometry(self, unit_visible_dict, keep_range):
        if self._x_range is not None and keep_range:
            #this may change with pyqtgraph
            self._x_range = tuple(self.viewBox1.state['viewRange'][0])
            self._y1_range = tuple(self.viewBox1.state['viewRange'][1])

        self.plot1.clear()
        
        if self.xvect is None:
            return

        #~ sparse = self.controller.have_sparse_template and self.params['sparse_display']
        sparse = self.params['sparse_display']
        #~ visibles = [k for k, v in unit_visible_dict.items() if v and k>=-1 ]
        visible_unit_ids = [unit_id for unit_id, v in unit_visible_dict.items() if v ]
        
        #~ if sparse:
            #~ if len(visibles) > 0:
                #~ common_channels = self.controller.get_common_sparse_channels(visibles)
            #~ else:
                #~ common_channels = np.array([], dtype='int64')
                #~ return
        #~ else:
            #~ common_channels = self.controller.channels

        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                return
        else:
            #~ common_channel_indexes = self.controller.channels
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype='int64')

        
        #~ n_left, n_right = self.controller.get_waveform_left_right()
        #~ if n_left is None:
            #~ return
        #~ width = n_right - n_left
        #~ shape = self.controller.get_waveforms_shape()
        #~ if shape is None:
            #~ return
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
            
        
        # if n_left/n_right have change need new xvect
        #~ if self.xvect.size != shape[0] * shape[1]:
            #~ self.initialize_plot()
        if width != self.xvect.shape[1]:
            self.initialize_plot()
        #~ shape = (shape[0], len(common_channels))
        
        self.plot1.addItem(self.curve_one_waveform)

        
        
        #~ if self.params['metrics']=='median/mad':
            #~ key1, key2 = 'median', 'mad'
        #~ elif self.params['metrics']=='mean/std':
            #~ key1, key2 = 'mean', 'std'

        #~ ypos = self.contact_location[:,1]
        #~ ypos = self.contact_location[common_channels,1]
        
        #~ xvect = self.xvect.reshape(self.controller.nb_channel, -1)[common_channels, :].flatten()
        #~ for k in unit_visible_dict:
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not unit_visible_dict[unit_id]:
                continue
            
            #~ wf, chans = self.controller.get_waveform_centroid(k, key1, sparse=sparse)
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            #~ template_std = self.controller.templates_std[unit_index, :, common_channel_indexes]
            
            
            #~ if wf is None: continue
            
            ypos = self.contact_location[common_channel_indexes,1]
            
            wf = template_avg
            #~ print(wf.shape, ypos.shape)
            wf = wf * self.factor_y * self.delta_y + ypos[None, :]
            #wf[0,:] = np.nan
            
            
            connect = np.ones(wf.shape, dtype='bool')
            connect[0, :] = 0
            connect[-1, :] = 0
            
            #~ xvect = self.xvect[chans, :]
            xvect = self.xvect[common_channel_indexes, :]
            
            
            
            color = self.controller.qcolors.get(unit_id, QT.QColor( 'white'))
            
            curve = pg.PlotCurveItem(xvect.flatten(), wf.T.flatten(), pen=pg.mkPen(color, width=2), connect=connect.T.flatten())
            self.plot1.addItem(curve)
        
        if self.params['show_channel_id']:
            #~ chan_grp = self.controller.chan_grp
            #~ channel_group = self.controller.dataio.channel_groups[chan_grp]            
            #~ for i, (chan, name) in enumerate(self.controller.channel_indexes_and_names):
            for chan_ind in common_channel_indexes:
                chan_id = self.controller.channel_ids[chan_ind]
                # chan i sabsolut chan
                #~ chan, name = cn[c]
            #~ for i, (chan, name) in enumerate(self.controller.channel_indexes_and_names):
                
            
                x, y = self.contact_location[chan_ind, : ]
                itemtxt = pg.TextItem(f'{chan_id}', anchor=(.5,.5), color='#FFFF00')
                itemtxt.setFont(QT.QFont('', pointSize=12))
                self.plot1.addItem(itemtxt)
                itemtxt.setPos(x, y)
        
        #~ if self._x_range is None:
        if self._x_range is None or not keep_range :
            self._x_range = np.min(self.xvect), np.max(self.xvect)
            self._y1_range = np.min(self.contact_location[:,1])-self.delta_y*2, np.max(self.contact_location[:,1])+self.delta_y*2
        
        self.plot1.setXRange(*self._x_range, padding = 0.0)
        self.plot1.setYRange(*self._y1_range, padding = 0.0)
        
    
    def _refresh_one_spike(self, n_selected):
        #TODO peak the selected peak if only one
        
        if n_selected!=1 or not self.params['plot_selected_spike']: 
            self.curve_one_waveform.setData([], [])
            return
        
        ind, = np.nonzero(self.controller.spikes['selected'])
        ind = ind[0]
        seg_num = self.controller.spikes['segment_index'][ind]
        peak_ind = self.controller.spikes['sample_index'][ind]
        
        #~ n_left, n_right = self.controller.get_waveform_left_right()
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        
        
        #~ wf = self.controller.dataio.get_signals_chunk(seg_num=seg_num, chan_grp=self.controller.chan_grp,
                #~ i_start=peak_ind+n_left, i_stop=peak_ind+n_right,
                #~ signal_type='processed')
        # TODO handle return_scaled
        wf = self.controller.get_traces(trace_source='preprocessed', 
                segment_index=seg_num, 
                start_frame=peak_ind - nbefore, end_frame=peak_ind + nafter,
                )
        
        if wf.shape[0] == width:
            #this avoid border bugs
            if self.mode=='flatten':
                if self._common_channel_indexes_flat is None:
                    self.curve_one_waveform.setData([], [])
                    return
                
                wf = wf[:, self._common_channel_indexes_flat].T.flatten()
                xvect = np.arange(wf.size)
                self.curve_one_waveform.setData(xvect, wf)
            elif self.mode=='geometry':
                ypos = self.contact_location[:,1]
                wf = wf*self.factor_y*self.delta_y + ypos[None, :]
                
                connect = np.ones(wf.shape, dtype='bool')
                connect[0, :] = 0
                connect[-1, :] = 0

                self.curve_one_waveform.setData(self.xvect.flatten(), wf.T.flatten(), connect=connect.T.flatten())
    
    def on_spike_selection_changed(self):
        #~ n_selected = np.sum(self.controller.spike_selection)
        #~ self._refresh_one_spike(n_selected)
        self.refresh(keep_range=True)



