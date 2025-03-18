import numpy as np



from .view_base import ViewBase

from spikeinterface.postprocessing.unit_locations import possible_localization_methods


class ProbeView(ViewBase):
    _supported_backend = ['qt']
    _settings = [
            #~ {'name': 'colormap', 'type': 'list', 'value': 'inferno', 'values': ['inferno', 'summer', 'viridis', 'jet'] },
            {'name': 'show_channel_id', 'type': 'bool', 'value': False},
            {'name': 'radius_channel', 'type': 'float', 'value': 50.},
            {'name': 'radius_units', 'type': 'float', 'value': 30.},
            # {'name': 'roi_channel', 'type': 'bool', 'value': True},
            # {'name': 'roi_units', 'type': 'bool', 'value': True},
            {'name': 'auto_zoom_on_unit_selection', 'type': 'bool', 'value': True},
            {'name': 'method_localize_unit', 'type': 'list', 'limits': possible_localization_methods},
            
            
        ]
    
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    def _make_layout_qt(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleClickToPosition
    
        
        self.layout = QT.QVBoxLayout()
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.viewBox = ViewBoxHandlingDoubleClickToPosition()
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
    
        # probes
        self.contact_positions = self.controller.get_contact_location()

        probes = self.controller.get_probegroup().probes
        for probe in probes:
            contact_vertices = probe.get_contact_vertices()
            # small hack to connect to the first point
            contact_vertices = [np.concatenate([e, e[:1, :]], axis=0) for e in contact_vertices]
            vertices = np.concatenate(contact_vertices)
            connect = np.ones(vertices.shape[0], dtype='bool')
            pos = 0
            for e in contact_vertices[:-1]:
                pos += e .shape[0]
                connect[pos-1] = False
            contacts = pg.PlotCurveItem(vertices[:, 0], vertices[:, 1], pen='#7FFF00', fill='#7F7F0C', connect=connect)
            self.plot.addItem(contacts)

            planar_contour = probe.probe_planar_contour
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

        radius = self.settings['radius_channel']
        x, y = self.contact_positions.mean(axis=0)
        self.roi_channel = pg.CircleROI([x - radius, y - radius], [radius * 2, radius * 2],  pen='#7F7F0C') #pen=(4,9),
        self.plot.addItem(self.roi_channel)
        self.roi_channel.sigRegionChanged.connect(self.on_roi_channel_changed)
        # self.roi_channel.sigRegionChangeFinished.connect(self.on_roi_channel_changed)
        

        radius = self.settings['radius_units']
        x, y = self.contact_positions.mean(axis=0)
        self.roi_units = pg.CircleROI([x - radius, y - radius], [radius * 2, radius * 2],  pen='#d68910') #pen=(4,9),
        self.plot.addItem(self.roi_units)
        self.roi_units.sigRegionChangeFinished.connect(self.on_roi_units_changed)

        # units
        #~ self.unit_positions
        unit_positions = self.controller.unit_positions
        brush = [self.get_unit_color(u) for u in self.controller.unit_ids]
        self.scatter = pg.ScatterPlotItem(pos=unit_positions, pxMode=False, size=10, brush=brush)
        self.plot.addItem(self.scatter)


        
        # range
        xlim0 = np.min(self.contact_positions[:, 0]) - 20
        xlim1 = np.max(self.contact_positions[:, 0]) + 20
        ylim0 = np.min(self.contact_positions[:, 1]) - 20
        ylim1 = np.max(self.contact_positions[:, 1]) + 20
        self.plot.setXRange(xlim0, xlim1)
        self.plot.setYRange(ylim0, ylim1)
        
        

    
    def _refresh_qt(self):
        r, x, y = circle_from_roi(self.roi_channel)
        radius = self.settings['radius_channel']
        self.roi_channel.setSize(radius * 2)
        self.roi_channel.setPos(x - radius, y-radius)

        r, x, y = circle_from_roi(self.roi_units)
        radius = self.settings['radius_units']
        self.roi_units.setSize(radius * 2)
        self.roi_units.setPos(x - radius, y-radius)

        
        if self.settings['show_channel_id']:
            for label in self.channel_labels:
                label.show()
        else:
            for label in self.channel_labels:
                label.hide()
            
    
    def update_channel_visibility_from_roi(self, emit_signals=False):
            r, x, y = circle_from_roi(self.roi_channel)
        
            dist = np.sqrt(np.sum((self.contact_positions - np.array([[x, y]]))**2, axis=1))
            visible_channel_inds,  = np.nonzero(dist < r)
            pos = self.contact_positions[visible_channel_inds, :]
            order = np.lexsort((-pos[:, 0], pos[:, 1], ))[::-1]
            visible_channel_inds = visible_channel_inds[order]
            self.controller.set_channel_visibility(visible_channel_inds)
            if emit_signals:
                self.notify_channel_visibility_changed()

    
    def on_roi_channel_changed(self, emit_signals=True):
        
        r, x, y = circle_from_roi(self.roi_channel)
        
        self.settings.blockSignals(True)
        self.settings['radius_channel'] = r
        self.settings.blockSignals(False)
        
        if emit_signals:
            self.roi_channel.blockSignals(True)
            # if self.settings['roi_channel']:
            
            self.update_channel_visibility_from_roi(emit_signals=True)

            # if self.settings['roi_units']:
            #     dist = np.sqrt(np.sum((self.controller.unit_positions - np.array([[x, y]]))**2, axis=1))
            #     for unit_index, unit_id in enumerate(self.controller.unit_ids):
            #         self.controller.unit_visible_dict[unit_id] = (dist[unit_index] < r)
            #     self.controller.update_visible_spikes()
            #     self.unit_visibility_changed.emit()
            #     self.on_unit_visibility_changed(auto_zoom=False)
                
            self.roi_channel.blockSignals(False)
    
    def on_roi_units_changed(self, emit_signals=True):
        r, x, y = circle_from_roi(self.roi_units)

        self.settings.blockSignals(True)
        self.settings['radius_units'] = r
        self.settings.blockSignals(False)


        if emit_signals:
            self.roi_units.blockSignals(True)

            dist = np.sqrt(np.sum((self.controller.unit_positions - np.array([[x, y]]))**2, axis=1))
            for unit_index, unit_id in enumerate(self.controller.unit_ids):
                self.controller.unit_visible_dict[unit_id] = (dist[unit_index] < r)
            # self.controller.update_visible_spikes()
            self.notify_unit_visibility_changed()
            self.on_unit_visibility_changed(auto_zoom=False)
                
            self.roi_units.blockSignals(False)
        
        # also change channel
        self.roi_channel.blockSignals(True)
        radius = self.settings['radius_channel']
        self.roi_channel.setPos(x - radius, y - radius)
        self.roi_channel.blockSignals(False)
        self.on_roi_channel_changed(emit_signals=True)
            


    
    def on_unit_visibility_changed(self, auto_zoom=None):
        import pyqtgraph as pg

        

        # this change the ROI and so change also channel_visibility
        visible_mask = np.array(list(self.controller.unit_visible_dict.values()))
        unit_inds = np.flatnonzero(visible_mask)
        n = unit_inds.size
        x, y = None, None
        if n == 1:
            # always refresh the channel ROI
            unit_index  = unit_inds[0]
            x, y = self.controller.unit_positions[unit_index, :]
        elif n > 1:
            # change ROI only if all units are inside the radius
            positions = self.controller.unit_positions[unit_inds, :]
            distances = np.linalg.norm(positions[:, np.newaxis] - positions[np.newaxis, :], axis=2)
            if np.max(distances) < (self.settings['radius_units'] * 2):
                x, y = np.mean(positions, axis=0)

        if x is not None:
            radius = self.settings['radius_channel']
            self.roi_channel.blockSignals(True)
            self.roi_channel.setPos(x - radius, y - radius)
            self.roi_channel.blockSignals(False)
            self.on_roi_channel_changed(emit_signals=False)
            radius = self.settings['radius_units']
            self.roi_units.blockSignals(True)
            self.roi_units.setPos(x - radius, y - radius)
            self.roi_units.blockSignals(False)
            self.on_roi_units_changed(emit_signals=False)

            self.update_channel_visibility_from_roi(emit_signals=True)
        
        # change scatter pen for selection
        pen = [pg.mkPen('white', width=4)
                    if self.controller.unit_visible_dict[u] else pg.mkPen('black', width=4)
                    for u in self.controller.unit_ids]
        self.scatter.setPen(pen)
        
        # auto zoom
        if auto_zoom is None:
            auto_zoom = self.settings['auto_zoom_on_unit_selection']
        
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
            radius = self.settings['radius_channel']
            unit_id = self.controller.unit_ids[ind]
            if multi_select:
                self.controller.unit_visible_dict[unit_id] = not(self.controller.unit_visible_dict[unit_id])
            else:
                self.controller.unit_visible_dict = {unit_id:False for unit_id in self.controller.unit_ids}
                self.controller.unit_visible_dict[unit_id] = True
                self.roi_channel.blockSignals(True)
                self.roi_channel.setPos(x - radius, y - radius)
                self.roi_channel.blockSignals(False)

            r, _, _ = circle_from_roi(self.roi_units)
            self.roi_units.blockSignals(True)
            self.roi_units.setPos(x - r, y - r)
            self.roi_units.blockSignals(False)

            # self.controller.update_visible_spikes()
            self.on_unit_visibility_changed()

            self.notify_unit_visibility_changed()


    
    def on_add_units(self, x, y):
        self.on_pick_unit(x, y, multi_select=True)
    

    def compute(self):
        # TODO : option by method
        method_kwargs ={} 
        self.controller.compute_unit_positions(self.settings['method_localize_unit'], method_kwargs)
        unit_positions = self.controller.unit_positions
        brush = [self.controller.qcolors[u] for u in self.controller.unit_ids]
        self.scatter.setData(pos=unit_positions, pxMode=False, size=10, brush=brush)
        
        self.refresh()
    
    #~ def compute_unit_positions

def circle_from_roi(roi):
    r = roi.state['size'][0] / 2
    x = roi.state['pos'].x() + r
    y = roi.state['pos'].y() + r
    return r, x, y



ProbeView._gui_help_txt = """Probe view
Show contact and probe shape.
Units are color coded.
Mouse drag ROI : change channel visibilty and unit visibility on other views
Right click on the background : zoom
Left click on the background : move
Double click one unit: select one unique unit
Ctrl + double click : select multiple units"""
