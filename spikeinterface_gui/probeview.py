from .myqt import QT
import pyqtgraph as pg

import numpy as np
import pandas as pd

from .base import WidgetBase

import time

from spikeinterface.postprocessing.unit_localization import possible_localization_methods


class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal(float, float)
    ctrl_doubleclicked = QT.pyqtSignal(float, float)
    
    def mouseDoubleClickEvent(self, ev):
        pos = self.mapToView(ev.pos())
        x, y = pos.x(), pos.y()
        if ev.modifiers() == QT.ControlModifier:
            self.ctrl_doubleclicked.emit(x, y)
        else:
            self.doubleclicked.emit(x, y)
        ev.accept()
    
    #~ def mouseClickEvent(self, ev):
        #~ print('mouseClickEvent', ev.modifiers(), QT.ControlModifier, ev.modifiers() == QT.ControlModifier)
        #~ if ev.modifiers() == QT.ControlModifier:
            #~ pos = self.mapToView(ev.pos())
            #~ x, y = pos.x(), pos.y()
            #~ self.ctrl_doubleclicked.emit(x, y)
        #~ ev.accept()
        #~ else:
            #~ pg.ViewBox.mouseClickEvent(self, ev)
    
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass


class ProbeView(WidgetBase):
    _params = [
            #~ {'name': 'colormap', 'type': 'list', 'value': 'inferno', 'values': ['inferno', 'summer', 'viridis', 'jet'] },
            {'name': 'show_channel_id', 'type': 'bool', 'value': False},
            {'name': 'radius', 'type': 'float', 'value': 40.},
            {'name': 'roi_change_channel_visibility', 'type': 'bool', 'value': True},
            {'name': 'roi_change_unit_visibility', 'type': 'bool', 'value': True},
            {'name': 'auto_zoom_on_unit_selection', 'type': 'bool', 'value': True},
            {'name': 'method_localize_unit', 'type': 'list', 'limits': possible_localization_methods},
            
            
        ]
    
    _need_compute = True
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.initialize_plot()
        
    def initialize_plot(self):
        self.viewBox = MyViewBox()
        #~ self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.doubleclicked.connect(self.on_pick_unit)
        self.viewBox.ctrl_doubleclicked.connect(self.on_add_units)
        
        #~ self.viewBox.disableAutoRange()
        
        #~ self.plot = pg.PlotItem(viewBox=self.viewBox)
        #~ self.graphicsview.setCentralItem(self.plot)
        #~ self.plot.hideButtons()

        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.plot.getViewBox().disableAutoRange()
        self.graphicsview.setCentralItem(self.plot)
        self.plot.getViewBox().setAspectLocked(lock=True, ratio=1)
        self.plot.hideButtons()
        #~ self.plot.showAxis('left', False)
        #~ self.plot.showAxis('bottom', False)
    
        # probe
        probe = self.controller.get_probe()
        contact_vertices = probe.get_contact_vertices()
        planar_contour = probe.probe_planar_contour
        self.contact_positions = probe.contact_positions
        
        # small hack to connect to the first point
        contact_vertices = [np.concatenate([e, e[:1, :]], axis=0) for e in contact_vertices]
        
        vertices = np.concatenate(contact_vertices)
        connect = np.ones(vertices.shape[0], dtype='bool')
        pos = 0
        for e in contact_vertices[:-1]:
            pos += e .shape[0]
            connect[pos-1] = False

        self.contacts = pg.PlotCurveItem(vertices[:, 0], vertices[:, 1], pen='#7FFF00', fill='#7F7F0C', connect=connect)
        self.plot.addItem(self.contacts)
        
        if planar_contour is not None:
            self.contour = pg.PlotCurveItem(planar_contour[:, 0], planar_contour[:, 1], pen='#7FFF00')
            self.plot.addItem(self.contour)
            
        # ROI
        self.channel_labels = []
        for i, channel_id in enumerate(self.controller.channel_ids):
            #TODO label channels
            label = pg.TextItem(f'{channel_id}', color='#FFFFFF', anchor=(0.5, 0.5), border=None)#, fill=pg.mkColor((128,128,128, 180)))
            label.setPos(self.contact_positions[i, 0], self.contact_positions[i, 1])
            self.plot.addItem(label)
            self.channel_labels.append(label)

        radius = self.params['radius']
        x, y = self.contact_positions.mean(axis=0)
        self.roi = pg.CircleROI([x - radius, y - radius], [radius * 2, radius * 2],  pen='#7F7F0C') #pen=(4,9),
        self.plot.addItem(self.roi)
        
        self.roi.sigRegionChanged.connect(self.on_roi_change)
        
        # units
        #~ self.unit_positions
        unit_positions = self.controller.unit_positions
        brush = [self.controller.qcolors[u] for u in self.controller.unit_ids]
        self.scatter = pg.ScatterPlotItem(pos=unit_positions, pxMode=False, size=10, brush=brush)
        self.plot.addItem(self.scatter)


        
        # range
        xlim0 = np.min(self.contact_positions[:, 0]) - 20
        xlim1 = np.max(self.contact_positions[:, 0]) + 20
        ylim0 = np.min(self.contact_positions[:, 1]) - 20
        ylim1 = np.max(self.contact_positions[:, 1]) + 20
        self.plot.setXRange(xlim0, xlim1)
        self.plot.setYRange(ylim0, ylim1)
        
        

    
    def _refresh(self):
        r = self.roi.state['size'][0] / 2
        x = self.roi.state['pos'].x() + r
        y = self.roi.state['pos'].y() + r

        radius = self.params['radius']
        self.roi.setSize(radius * 2)
        self.roi.setPos(x - radius, y-radius)
        
        
        if self.params['show_channel_id']:
            for label in self.channel_labels:
                label.show()
        else:
            for label in self.channel_labels:
                label.hide()
            
        
    
    def on_roi_change(self, emit_signals=True):
        
        r = self.roi.state['size'][0] / 2
        x = self.roi.state['pos'].x() + r
        y = self.roi.state['pos'].y() + r
        
        self.params.blockSignals(True)
        self.params['radius'] = r
        self.params.blockSignals(False)
        
        if emit_signals:
            self.roi.blockSignals(True)
            if self.params['roi_change_channel_visibility']:
                #~ t0 = time.perf_counter()
                dist = np.sqrt(np.sum((self.contact_positions - np.array([[x, y]]))**2, axis=1))
                visible_channel_inds,  = np.nonzero(dist < r)
                order = np.argsort(dist[visible_channel_inds])
                visible_channel_inds = visible_channel_inds[order]
                self.controller.set_channel_visibility(visible_channel_inds)
                self.channel_visibility_changed.emit()
                #~ t1 = time.perf_counter()
                #~ print(' probe view change_channel_visibility', t1-t0)

            if self.params['roi_change_unit_visibility']:
                #~ t0 = time.perf_counter()
                dist = np.sqrt(np.sum((self.controller.unit_positions - np.array([[x, y]]))**2, axis=1))
                for unit_index, unit_id in enumerate(self.controller.unit_ids):
                    self.controller.unit_visible_dict[unit_id] = (dist[unit_index] < r)
                #~ t1 = time.perf_counter()
                #~ print(' probe view part1 change_unit_visibility', t1-t0)
                self.controller.update_visible_spikes()
                self.unit_visibility_changed.emit()
                self.on_unit_visibility_changed(auto_zoom=False)
                #~ t2 = time.perf_counter()
                #~ print(' probe view part2 change_unit_visibility', t2-t0)
                
            self.roi.blockSignals(False)
    
    def on_unit_visibility_changed(self, auto_zoom=None):
        # this change the ROI and so change also channel_visibility
        visible_mask = list(self.controller.unit_visible_dict.values())
        n = np.sum(visible_mask)
        if n == 1:
            unit_index  = np.nonzero(visible_mask)[0][0]
            x, y = self.controller.unit_positions[unit_index, :]
            radius = self.params['radius']
            self.roi.blockSignals(True)
            self.roi.setPos(x - radius, y - radius)
            self.roi.blockSignals(False)
            self.on_roi_change(emit_signals=False)
        
        # change scatter pen for selection
        pen = [pg.mkPen('magenta', width=4)
                    if self.controller.unit_visible_dict[u] else pg.mkPen('black', width=4)
                    for u in self.controller.unit_ids]
        self.scatter.setPen(pen)
        
        # auto zoom
        if auto_zoom is None:
            auto_zoom = self.params['auto_zoom_on_unit_selection']
        
        if auto_zoom:
            visible_pos = self.controller.unit_positions[visible_mask, :]
            x_min, x_max = np.min(visible_pos[:, 0]), np.max(visible_pos[:, 0])
            y_min, y_max = np.min(visible_pos[:, 1]), np.max(visible_pos[:, 1])
            margin =50
            self.plot.setXRange(x_min - margin, x_max+ margin)
            self.plot.setYRange(y_min - margin, y_max+ margin)

    
    def on_channel_visibility_changed(self):
        pass
    
    def on_pick_unit(self, x, y, multi_select=False):
        unit_positions = self.controller.unit_positions
        pos = np.array([x, y])[None, :]
        distances = np.sum((unit_positions - pos) **2, axis=1) ** 0.5
        ind = np.argmin(distances)
        if distances[ind] < 5.:
            radius = self.params['radius']
            unit_id = self.controller.unit_ids[ind]
            if multi_select:
                self.controller.unit_visible_dict[unit_id] = not(self.controller.unit_visible_dict[unit_id])
            else:
                self.controller.unit_visible_dict = {unit_id:False for unit_id in self.controller.unit_ids}
                self.controller.unit_visible_dict[unit_id] = True
                self.roi.blockSignals(True)
                self.roi.setPos(x - radius, y - radius)
                self.roi.blockSignals(False)

            self.controller.update_visible_spikes()
            self.on_unit_visibility_changed()
            self.unit_visibility_changed.emit()
    
    def on_add_units(self, x, y):
        self.on_pick_unit(x, y, multi_select=True)
    

    def compute(self):
        # TODO : option by method
        method_kwargs ={} 
        self.controller.compute_unit_positions(self.params['method_localize_unit'], method_kwargs)
        unit_positions = self.controller.unit_positions
        brush = [self.controller.qcolors[u] for u in self.controller.unit_ids]
        self.scatter.setData(pos=unit_positions, pxMode=False, size=10, brush=brush)
        
        self.refresh()
    
    #~ def compute_unit_positions


ProbeView._gui_help_txt = """Probe view
Show contact and probe shape.
Units are color coded.
Mouse drag ROI : change channel visibilty and unit visibility on other views
Right click on the background : zoom
Left click on the background : move
Double click one one unit: select one unique unit"""
