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
                      {'name': 'metrics', 'type': 'list', 'limits': ['median/mad'] },
                      {'name': 'fillbetween', 'type': 'bool', 'value': True },
                      {'name': 'show_channel_id', 'type': 'bool', 'value': False},
                      {'name': 'flip_bottom_up', 'type': 'bool', 'value': False},
                      {'name': 'display_threshold', 'type': 'bool', 'value' : True },
                      {'name': 'sparse_display', 'type': 'bool', 'value' : True },
                      {'name': 'auto_zoom_on_unit_selection', 'type': 'bool', 'value': True},
                      {'name': 'background_color', 'type': 'color', 'value' : 'k' },
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
            

            num_chan = len(self.controller.channel_ids)

            self.xvect = np.zeros((num_chan, width), dtype='float32')
            
            self.contact_location = self.controller.get_contact_location().copy()
            
            if self.params['flip_bottom_up']:
                self.contact_location[:, 1] *= -1.
            
            xpos = self.contact_location[:,0]
            ypos = self.contact_location[:,1]
            
            unique_x = np.sort(np.unique(xpos))
            if unique_x.size>1:
                self.delta_x = np.min(np.diff(unique_x))
            else:
                self.delta_x = 40. # um
            
            unique_y = np.sort(np.unique(ypos))
            if unique_y.size>1:
                self.delta_y = np.min(np.diff(unique_y))
            else:
                self.delta_y = 40. # um

            self.factor_y = .05
            
            espx = self.delta_x / 2.5
            for chan_ind, chan_id in enumerate(self.controller.channel_ids):
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
        
        selected_inds = self.controller.get_indices_spike_selected()
        n_selected = selected_inds.size
        
        if self.params['show_only_selected_cluster'] and n_selected==1:
            unit_visible_dict = {k:False for k in self.controller.unit_visible_dict}
            ind = selected_inds[0]
            unit_index = self.controller.spikes[ind]['unit_index']
            unit_id = self.controller.unit_ids[unit_index]
            unit_visible_dict[unit_id] = True
        else:
            unit_visible_dict = self.controller.unit_visible_dict
        self.viewBox1.setBackgroundColor(self.params['background_color'])
        if self.mode=='flatten':
            self.plot1.setAspectLocked(lock=False, ratio=None)
            self.refresh_mode_flatten(unit_visible_dict, keep_range)
            self.viewBox2.setBackgroundColor(self.params['background_color'])
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
        
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        
        
        sparse = self.params['sparse_display']
        
        visible_unit_ids = [unit_id for unit_id, v in unit_visible_dict.items() if v ]
        
        
        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                return
        else:
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype='int64')
        
        self._common_channel_indexes_flat = common_channel_indexes
        
        #lines
        def addSpan(plot):
            white = pg.mkColor(255, 255, 255, 20)
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
        
        shape = (width, len(common_channel_indexes))
        xvect = np.arange(shape[0]*shape[1])
        min_std = 0
        max_std = 0
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not unit_visible_dict[unit_id]:
                continue
            
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            template_std = self.controller.templates_std[unit_index, :, :][:, common_channel_indexes]
            
            color = self.controller.qcolors.get(unit_id, QT.QColor( 'white'))
            curve = pg.PlotCurveItem(xvect, template_avg.T.flatten(), pen=pg.mkPen(color, width=2))
            self.plot1.addItem(curve)
            
            
            if self.params['fillbetween']:
                color2 = QT.QColor(color)
                color2.setAlpha(self.alpha)
                curve1 = pg.PlotCurveItem(xvect, template_avg.T.flatten() + template_std.T.flatten(), pen=color2)
                curve2 = pg.PlotCurveItem(xvect, template_avg.T.flatten() - template_std.T.flatten(), pen=color2)
                self.plot1.addItem(curve1)
                self.plot1.addItem(curve2)
                
                fill = pg.FillBetweenItem(curve1=curve1, curve2=curve2, brush=color2)
                self.plot1.addItem(fill)
            
            if template_std is not None:
                template_std_flatten = template_std.T.flatten()
                curve = pg.PlotCurveItem(xvect, template_std_flatten, pen=color)
                self.plot2.addItem(curve)
                min_std = min(min_std,template_std_flatten.min())
                max_std = max(max_std,template_std_flatten.max())
        if self.params['show_channel_id']:
            for i, chan_ind in enumerate(common_channel_indexes):
                chan_id = self.controller.channel_ids[chan_ind]
                itemtxt = pg.TextItem(f'{chan_id}', anchor=(.5,.5), color='#FFFF00')
                itemtxt.setFont(QT.QFont('', pointSize=12))
                self.plot1.addItem(itemtxt)
                itemtxt.setPos(width * i +nbefore, 0)

        
        if self._x_range is None or not keep_range :
            if xvect.size>0:
                self._x_range = xvect[0], xvect[-1]
                self._y1_range = self.wf_min*1.1, self.wf_max*1.1
                self._y2_range = min_std*0.9, max_std*1.1
                
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

        sparse = self.params['sparse_display']
        visible_unit_ids = [unit_id for unit_id, v in unit_visible_dict.items() if v ]
        
        if sparse:
            if len(visible_unit_ids) > 0:
                common_channel_indexes = self.controller.get_common_sparse_channels(visible_unit_ids)
            else:
                return
        else:
            common_channel_indexes = np.arange(len(self.controller.channel_ids), dtype='int64')

        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter

        if width != self.xvect.shape[1]:
            self.initialize_plot()
        
        self.plot1.addItem(self.curve_one_waveform)


        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not unit_visible_dict[unit_id]:
                continue
            
            template_avg = self.controller.templates_average[unit_index, :, :][:, common_channel_indexes]
            
            ypos = self.contact_location[common_channel_indexes,1]
            
            wf = template_avg
            wf = wf * self.factor_y * self.delta_y + ypos[None, :]
            
            connect = np.ones(wf.shape, dtype='bool')
            connect[0, :] = 0
            connect[-1, :] = 0
            
            xvect = self.xvect[common_channel_indexes, :]
            
            
            
            color = self.controller.qcolors.get(unit_id, QT.QColor( 'white'))
            
            curve = pg.PlotCurveItem(xvect.flatten(), wf.T.flatten(), pen=pg.mkPen(color, width=2), connect=connect.T.flatten())
            self.plot1.addItem(curve)
        
        if self.params['show_channel_id']:
            for chan_ind in common_channel_indexes:
                chan_id = self.controller.channel_ids[chan_ind]
                x, y = self.contact_location[chan_ind, : ]
                itemtxt = pg.TextItem(f'{chan_id}', anchor=(.5,.5), color='#FFFF00')
                itemtxt.setFont(QT.QFont('', pointSize=12))
                self.plot1.addItem(itemtxt)
                itemtxt.setPos(x, y)
        
        if self._x_range is None or not keep_range :

            x_margin =50
            y_margin =150
            self._x_range = np.min(self.xvect) - x_margin , np.max(self.xvect) + x_margin
            visible_mask = list(self.controller.unit_visible_dict.values())
            visible_pos = self.controller.unit_positions[visible_mask, :]
            self._y1_range = np.min(visible_pos[:,1]) - y_margin , np.max(visible_pos[:,1]) + y_margin
        
        self.plot1.setXRange(*self._x_range, padding = 0.0)
        self.plot1.setYRange(*self._y1_range, padding = 0.0)
        
    
    def _refresh_one_spike(self, n_selected):

        if n_selected!=1 or not self.params['plot_selected_spike']: 
            self.curve_one_waveform.setData([], [])
            return
        
        selected_inds = self.controller.get_indices_spike_selected()
        ind = selected_inds[0]
        
        seg_num = self.controller.spikes['segment_index'][ind]
        peak_ind = self.controller.spikes['sample_index'][ind]
        
        nbefore, nafter = self.controller.get_waveform_sweep()
        width = nbefore + nafter
        
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
        self.refresh(keep_range=True)
    
    def on_unit_visibility_changed(self):
        keep_range = not(self.params['auto_zoom_on_unit_selection'])
        self.refresh(keep_range=keep_range)

WaveformView._gui_help_txt = """Waveform view
Display average template for visible units.
If one spike is selected (in spike list) then the spike is super imposed (white trace).

2 mode :
  * 'geometry' : snipet are displayed center on contact position
  * 'flatten' : snipet are concatenated in flatten way (better to check variance)

Please check all settings."""

