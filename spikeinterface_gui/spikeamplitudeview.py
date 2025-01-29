from .myqt import QT
import pyqtgraph as pg

import numpy as np
from matplotlib.path import Path as mpl_path

from .base import WidgetBase



class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    lasso_drawing = QT.pyqtSignal(object)
    lasso_finished = QT.pyqtSignal(object)
    
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.drag_points = []
    
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    
    def mouseDragEvent(self, ev):
        ev.accept()
        if ev.button() != QT.MouseButton.LeftButton:
            return
        
        if ev.isStart():
            self.drag_points = []
        
        pos = self.mapToView(ev.pos())
        self.drag_points.append([pos.x(), pos.y()])
        
        if ev.isFinish():
            self.lasso_finished.emit(self.drag_points)
        else:
            self.lasso_drawing.emit(self.drag_points)
    
    def raiseContextMenu(self, ev):
        pass



class SpikeAmplitudeView(WidgetBase):
    _depend_on = ['spike_amplitudes']
    _params = [
            {'name': 'alpha', 'type': 'float', 'value' : 0.7, 'limits':(0, 1.), 'step':0.05 },
            
            {'name': 'scatter_size', 'type': 'float', 'value' : 4., 'step':0.5 },
            {'name': 'num_bins', 'type': 'int', 'value' : 400, 'step': 1 },
            {'name': 'noise_level', 'type': 'bool', 'value' : True },
            {'name': 'noise_factor', 'type': 'int', 'value' : 5 },

            
            
        ]
    _need_compute = False
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)

        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        self.combo_seg = QT.QComboBox()
        h.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {seg_index}' for seg_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self.refresh)
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        self.graphicsview = pg.GraphicsView()
        #~ self.graphicsview.setHorizontalStretch(3)
        #~ self.layout.addWidget(self.graphicsview)
        h.addWidget(self.graphicsview, 3)

        self.graphicsview2 = pg.GraphicsView()
        #~ self.layout.addWidget(self.graphicsview2)
        h.addWidget(self.graphicsview2, 1)
        #~ self.graphicsview2.setHorizontalStretch(1)


        self.initialize_plot()
        
        # Add lasso curve
        self.lasso = pg.PlotCurveItem(pen='#7FFF00')
        self.plot.addItem(self.lasso)
        
        # Add selection scatter
        brush = QT.QColor('white')
        brush.setAlpha(200)
        self.scatter_select = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=brush, size=11, pxMode=True)
        self.plot.addItem(self.scatter_select)
        self.scatter_select.setZValue(1000)

    def on_params_changed(self):
        self.refresh()
    
    def initialize_plot(self):
        self.viewBox = MyViewBox()
        self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.lasso_drawing.connect(self.on_lasso_drawing)
        self.viewBox.lasso_finished.connect(self.on_lasso_finished)
        self.viewBox.disableAutoRange()
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
    
        self.viewBox2 = MyViewBox()
        self.viewBox2.doubleclicked.connect(self.open_settings)
        self.viewBox2.disableAutoRange()
        self.plot2 = pg.PlotItem(viewBox=self.viewBox2)
        self.graphicsview2.setCentralItem(self.plot2)
        self.plot2.hideButtons()
        self.plot2.setYLink(self.plot)

        #~ l = pg.GraphicsLayout()
        
        #~ # hack to force 4 row
        #~ rem = [l.addPlot() for i in range(4)]
        #~ l.nextRow()
        
        #~ self.graphicsview.setCentralItem(l)
        #~ self.plot = l.addPlot(row=1, col=0, colspan=3)
        #~ self.plot.hideButtons()
        
        #~ self.plot2 = l.addPlot(row=1, col=3, colspan=1)
        #~ self.plot2.hideButtons()
        
        #~ self.plot2.setYLink(self.plot)
        
        #~ #end of the hack hack to force 4 row
        #~ for p in rem:
            #~ l.removeItem(p)
        
        self.scatter = pg.ScatterPlotItem(size=self.params['scatter_size'], pxMode = True)
        self.plot.addItem(self.scatter)
        
        self._text_items = []
        
        
        self._amp_min = np.min(self.controller.spike_amplitudes)
        self._amp_max = np.max(self.controller.spike_amplitudes)
        eps = (self._amp_max - self._amp_min) / 100.
        self._amp_max += eps 

        self.plot.setYRange(self._amp_min,self._amp_max, padding = 0.0)


    
    def _refresh(self):
        self.scatter.clear()
        self.plot2.clear()
        self.scatter_select.clear()
        
        if self.controller.spike_amplitudes is None:
            return
            
        seg_index =  self.combo_seg.currentIndex()
        sl = self.controller.segment_slices[seg_index]
        
        spikes_in_seg = self.controller.spikes[sl]
        
        fs = self.controller.sampling_frequency
        
        self.scatter.setSize(self.params['scatter_size'])
        
        max_count = 0
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                continue

            color = QT.QColor(self.controller.qcolors[unit_id])
            color.setAlpha(int(self.params['alpha']*255))

            

            # amps = self.controller.spike_amplitudes[seg_index][unit_id]

            spike_mask = (spikes_in_seg['unit_index'] == unit_index)
            spikes = spikes_in_seg[spike_mask]
            spike_times = spikes['sample_index'] / fs
            amps = self.controller.spike_amplitudes[sl][spike_mask]
            
            self.scatter.addPoints(x=spike_times, y=amps,  pen=pg.mkPen(None), brush=color)
            

            count, bins = np.histogram(amps, bins = np.linspace(self._amp_min, self._amp_max, self.params['num_bins']))
            # trick to avoid bad borders
            # count[0] = 0
            # count[-1] = 0
            
            max_count = max(max_count, np.max(count))
            
            #~ color = QT.QColor(self.controller.qcolors[unit_id])
            # curve = pg.PlotCurveItem(count, bins, stepMode='center', fillLevel=0, brush=color, pen=color)
            
            # curve = pg.PlotCurveItem(count, bins[:-1], fillLevel=0, fillOutline=True, brush=color, pen=color)

            color = QT.QColor(self.controller.qcolors[unit_id])

            curve = pg.PlotCurveItem(count, bins[:-1], fillLevel=None, fillOutline=True, brush=color, pen=color)
            

            self.plot2.addItem(curve)

        # average noise across channels
        if self.params["noise_level"]:
            n = self.params["noise_factor"]
            noise = np.mean(self.controller.noise_levels)
            alpha_factor = 50 / n
            for i in range(1, n + 1):
                self.plot2.addItem(
                    pg.LinearRegionItem(values=(-i * noise, i * noise), orientation="horizontal",
                                        brush=(255, 255, 255, int(i * alpha_factor)), pen=(0, 0, 0, 0))
                )
            
        
        t1 = 0.
        t2 = self.controller.get_num_samples(seg_index) / fs
        self.plot.setXRange( t1, t2, padding = 0.0)
        #~ self.plot.setYRange(-.5, nb_visible-.5, padding = 0.0)
        
        self.plot2.setXRange(0, max_count, padding = 0.0)
        
        # Update selection scatter
        seg_index = self.combo_seg.currentIndex()
        sl = self.controller.segment_slices[seg_index]
        spikes_in_seg = self.controller.spikes[sl]
        fs = self.controller.sampling_frequency
        
        selected_indices = self.controller.get_indices_spike_selected()
        mask = np.isin(sl.start + np.arange(len(spikes_in_seg)), selected_indices)
        if np.any(mask):
            selected_spikes = spikes_in_seg[mask]
            spike_times = selected_spikes['sample_index'] / fs
            amps = self.controller.spike_amplitudes[sl][mask]
            self.scatter_select.setData(spike_times, amps)
    
    def on_lasso_drawing(self, points):
        points = np.array(points)
        self.lasso.setData(points[:, 0], points[:, 1])
    
    def on_lasso_finished(self, points):
        self.lasso.setData([], [])
        vertices = np.array(points)
        
        seg_index = self.combo_seg.currentIndex()
        sl = self.controller.segment_slices[seg_index]
        spikes_in_seg = self.controller.spikes[sl]
        fs = self.controller.sampling_frequency
        
        # Create mask for visible units
        visible_mask = np.zeros(len(spikes_in_seg), dtype=bool)
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if self.controller.unit_visible_dict[unit_id]:
                visible_mask |= (spikes_in_seg['unit_index'] == unit_index)
        
        # Only consider spikes from visible units
        visible_spikes = spikes_in_seg[visible_mask]
        if len(visible_spikes) == 0:
            # Clear selection if no visible spikes
            self.controller.set_indices_spike_selected([])
            self.refresh()
            self.spike_selection_changed.emit()
            return
            
        spike_times = visible_spikes['sample_index'] / fs
        amps = self.controller.spike_amplitudes[sl][visible_mask]
        
        points = np.column_stack((spike_times, amps))
        inside = mpl_path(vertices).contains_points(points)
        
        # Clear selection if no spikes inside lasso
        if not np.any(inside):
            self.controller.set_indices_spike_selected([])
            self.refresh()
            self.spike_selection_changed.emit()
            return
            
        # Map back to original indices
        visible_indices = np.nonzero(visible_mask)[0]
        selected_indices = sl.start + visible_indices[inside]
        self.controller.set_indices_spike_selected(selected_indices)
        self.refresh()
        self.spike_selection_changed.emit()

    def on_spike_selection_changed(self):
        self.refresh()

SpikeAmplitudeView._gui_help_txt = """Spike Amplitude view
Check amplitudes of spikes across the recording time or in a histogram
comparing the distribution of ampltidues to the noise levels
Mouse click : change scaling
Left click drag : draw lasso to select spikes"""
