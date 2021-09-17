from .myqt import QT
import pyqtgraph as pg

import numpy as np
import pandas as pd

from .base import WidgetBase



class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass


class ProbeView(WidgetBase):
    _params = [
            #~ {'name': 'colormap', 'type': 'list', 'value': 'inferno', 'values': ['inferno', 'summer', 'viridis', 'jet'] },
            {'name': 'show_channel_id', 'type': 'bool', 'value': True},
            {'name': 'radius', 'type': 'float', 'value': 40.},
            
        ]
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.initialize_plot()
        
    def initialize_plot(self):
        self.viewBox = MyViewBox()
        self.viewBox.doubleclicked.connect(self.open_settings)
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
    
        # retrieve probe info
        probe = self.controller.get_probe()
        contact_vertices = probe.get_contact_vertices()
        planar_contour = probe.probe_planar_contour
        self.contact_positions = probe.contact_positions
        
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
        
        xlim0 = np.min(self.contact_positions[:, 0]) - 20
        xlim1 = np.max(self.contact_positions[:, 0]) + 20
        ylim0 = np.min(self.contact_positions[:, 1]) - 20
        ylim1 = np.max(self.contact_positions[:, 1]) + 20
        self.plot.setXRange(xlim0, xlim1)
        self.plot.setYRange(ylim0, ylim1)
        
        

    
    def refresh(self):
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
            
        
    
    def on_roi_change(self):
        
        r = self.roi.state['size'][0] / 2
        x = self.roi.state['pos'].x() + r
        y = self.roi.state['pos'].y() + r
        
        self.params.blockSignals(True)
        self.params['radius'] = r
        self.params.blockSignals(False)
        
        dist = np.sqrt(np.sum((self.contact_positions - np.array([[x, y]]))**2, axis=1))
        visible_channel_inds,  = np.nonzero(dist < r)
        order = np.argsort(dist[visible_channel_inds])
        visible_channel_inds = visible_channel_inds[order]
        
        self.controller.set_channel_visibility(visible_channel_inds)
        self.channel_visibility_changed.emit()
        

