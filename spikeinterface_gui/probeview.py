import numpy as np



from .view_base import ViewBase

from spikeinterface.postprocessing.unit_locations import possible_localization_methods


# TODO handle better compte

class ProbeView(ViewBase):
    _supported_backend = ['qt', 'panel']
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
        self.contact_positions = controller.get_contact_location()
        self.probes = controller.get_probegroup().probes
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    def get_probe_vertices(self):
        all_vertices = []
        all_connects = []
        all_contours = []

        for probe in self.probes:
            contact_vertices = probe.get_contact_vertices()
            # small hack to connect to the first point
            contact_vertices = [np.concatenate([e, e[:1, :]], axis=0) for e in contact_vertices]
            vertices = np.concatenate(contact_vertices)
            connect = np.ones(vertices.shape[0], dtype="bool")
            pos = 0
            for e in contact_vertices[:-1]:
                pos += e.shape[0]
                connect[pos - 1] = False

            all_vertices.append(vertices)
            all_connects.append(connect)
            all_contours.append(probe.probe_planar_contour)

        return all_vertices, all_connects, all_contours

    def update_channel_visibility(self, x, y, roi_radius):
        dist = np.sqrt(np.sum((self.contact_positions - np.array([[x, y]])) ** 2, axis=1))
        visible_channel_inds = np.flatnonzero(dist < roi_radius)
        pos = self.contact_positions[visible_channel_inds, :]
        order = np.lexsort((-pos[:, 0],pos[:, 1]))[::-1]
        visible_channel_inds = visible_channel_inds[order]
        return visible_channel_inds

    def update_unit_visibility(self, x, y, roi_radius):
        dist = np.sqrt(np.sum((self.controller.unit_positions - np.array([[x, y]])) ** 2, axis=1))
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            self.controller.unit_visible_dict[unit_id] = dist[unit_index] < roi_radius

    def get_view_bounds(self, margin=20):
        xlim0 = np.min(self.contact_positions[:, 0]) - margin
        xlim1 = np.max(self.contact_positions[:, 0]) + margin
        ylim0 = np.min(self.contact_positions[:, 1]) - margin
        ylim1 = np.max(self.contact_positions[:, 1]) + margin
        return xlim0, xlim1, ylim0, ylim1

    # def get_unit_bounds(self, visible_mask, margin=50):
    #     """Get boundaries for visible units"""
    #     visible_pos = self.controller.unit_positions[visible_mask, :]
    #     x_min, x_max = np.min(visible_pos[:, 0]), np.max(visible_pos[:, 0])
    #     y_min, y_max = np.min(visible_pos[:, 1]), np.max(visible_pos[:, 1])
    #     return x_min - margin, x_max + margin, y_min - margin, y_max + margin

    def find_closest_unit(self, x, y, max_distance=5.0):
        unit_positions = self.controller.unit_positions
        pos = np.array([x, y])[None, :]
        distances = np.sum((unit_positions - pos) ** 2, axis=1) ** 0.5
        ind = np.argmin(distances)
        if distances[ind] < max_distance:
            return self.controller.unit_ids[ind], ind
        return None, None

    # def compute_unit_positions(self, method, method_kwargs=None):
    #     """Compute unit positions using specified method"""
    #     if method_kwargs is None:
    #         method_kwargs = {}
    #     self.controller.compute_unit_positions(method, method_kwargs)
    #     return self.controller.unit_positions


    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleClickToPosition
    
        
        self.layout = QT.QVBoxLayout()
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.viewBox = ViewBoxHandlingDoubleClickToPosition()
        #~ self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.doubleclicked.connect(self._qt_on_pick_unit)
        self.viewBox.ctrl_doubleclicked.connect(self._qt_on_add_units)
        
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
        

        probes = self.controller.get_probegroup().probes
        # for probe in probes:
        #     contact_vertices = probe.get_contact_vertices()
        #     # small hack to connect to the first point
        #     contact_vertices = [np.concatenate([e, e[:1, :]], axis=0) for e in contact_vertices]
        #     vertices = np.concatenate(contact_vertices)
        #     connect = np.ones(vertices.shape[0], dtype='bool')
        #     pos = 0
        #     for e in contact_vertices[:-1]:
        #         pos += e .shape[0]
        #         connect[pos-1] = False
        #     contacts = pg.PlotCurveItem(vertices[:, 0], vertices[:, 1], pen='#7FFF00', fill='#7F7F0C', connect=connect)
        #     self.plot.addItem(contacts)

        #     planar_contour = probe.probe_planar_contour
        #     if planar_contour is not None:
        #         self.contour = pg.PlotCurveItem(planar_contour[:, 0], planar_contour[:, 1], pen='#7FFF00')
        #         self.plot.addItem(self.contour)
        vertices_list, connects_list, contours = self.get_probe_vertices()
        for vertices, connect in zip(vertices_list, connects_list):
            contacts = pg.PlotCurveItem(vertices[:, 0], vertices[:, 1], pen="#7FFF00", fill="#7F7F0C", connect=connect)
            self.plot.addItem(contacts)

        for contour in contours:
            if contour is not None:
                self.contour = pg.PlotCurveItem(contour[:, 0], contour[:, 1], pen="#7FFF00")
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
        self.roi_channel.sigRegionChanged.connect(self._qt_on_roi_channel_changed)
        # self.roi_channel.sigRegionChangeFinished.connect(self._qt_on_roi_channel_changed)
        

        radius = self.settings['radius_units']
        x, y = self.contact_positions.mean(axis=0)
        self.roi_units = pg.CircleROI([x - radius, y - radius], [radius * 2, radius * 2],  pen='#d68910') #pen=(4,9),
        self.plot.addItem(self.roi_units)
        self.roi_units.sigRegionChangeFinished.connect(self._qt_on_roi_units_changed)

        # units
        #~ self.unit_positions
        unit_positions = self.controller.unit_positions
        brush = [self.get_unit_color(u) for u in self.controller.unit_ids]
        self.scatter = pg.ScatterPlotItem(pos=unit_positions, pxMode=False, size=10, brush=brush)
        self.plot.addItem(self.scatter)


        
        # range
        xlim0, xlim1, ylim0, ylim1 = self.get_view_bounds()
        self.plot.setXRange(xlim0, xlim1)
        self.plot.setYRange(ylim0, ylim1)
    
    def _qt_refresh(self):
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
            
    
    def _qt_update_channel_visibility_from_roi(self, emit_signals=False):
            r, x, y = circle_from_roi(self.roi_channel)
        
            # dist = np.sqrt(np.sum((self.contact_positions - np.array([[x, y]]))**2, axis=1))
            # visible_channel_inds,  = np.nonzero(dist < r)
            # pos = self.contact_positions[visible_channel_inds, :]
            # order = np.lexsort((-pos[:, 0], pos[:, 1], ))[::-1]
            # visible_channel_inds = visible_channel_inds[order]
            visible_channel_inds = self.update_channel_visibility(x, y, r)
            self.controller.set_channel_visibility(visible_channel_inds)
            if emit_signals:
                self.notify_channel_visibility_changed()

    
    def _qt_on_roi_channel_changed(self, emit_signals=True):
        
        r, x, y = circle_from_roi(self.roi_channel)
        
        self.settings.blockSignals(True)
        self.settings['radius_channel'] = r
        self.settings.blockSignals(False)
        
        if emit_signals:
            self.roi_channel.blockSignals(True)
            # if self.settings['roi_channel']:
            
            self._qt_update_channel_visibility_from_roi(emit_signals=True)

            # if self.settings['roi_units']:
            #     dist = np.sqrt(np.sum((self.controller.unit_positions - np.array([[x, y]]))**2, axis=1))
            #     for unit_index, unit_id in enumerate(self.controller.unit_ids):
            #         self.controller.unit_visible_dict[unit_id] = (dist[unit_index] < r)
            #     self.controller.update_visible_spikes()
            #     self.unit_visibility_changed.emit()
            #     self.on_unit_visibility_changed(auto_zoom=False)
                
            self.roi_channel.blockSignals(False)
    
    def _qt_on_roi_units_changed(self, emit_signals=True):
        r, x, y = circle_from_roi(self.roi_units)

        self.settings.blockSignals(True)
        self.settings['radius_units'] = r
        self.settings.blockSignals(False)


        if emit_signals:
            self.roi_units.blockSignals(True)

            # dist = np.sqrt(np.sum((self.controller.unit_positions - np.array([[x, y]]))**2, axis=1))
            # for unit_index, unit_id in enumerate(self.controller.unit_ids):
            #     self.controller.unit_visible_dict[unit_id] = (dist[unit_index] < r)
            self.update_unit_visibility(x, y, r)

            # self.controller.update_visible_spikes()
            self.notify_unit_visibility_changed()
            self._qt_on_unit_visibility_changed(auto_zoom=False)
                
            self.roi_units.blockSignals(False)
        
        # also change channel
        self.roi_channel.blockSignals(True)
        radius = self.settings['radius_channel']
        self.roi_channel.setPos(x - radius, y - radius)
        self.roi_channel.blockSignals(False)
        self._qt_on_roi_channel_changed(emit_signals=True)
            
    def _qt_on_unit_visibility_changed(self, auto_zoom=None):
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
            self._qt_on_roi_channel_changed(emit_signals=False)
            radius = self.settings['radius_units']
            self.roi_units.blockSignals(True)
            self.roi_units.setPos(x - radius, y - radius)
            self.roi_units.blockSignals(False)
            self._qt_on_roi_units_changed(emit_signals=False)

            self._qt_update_channel_visibility_from_roi(emit_signals=True)
        
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

    
    def _qt_on_pick_unit(self, x, y, multi_select=False):
        unit_id, _ = self.find_closest_unit(x, y)
        if unit_id is not None:
            radius = self.params["radius_channel"]
            if multi_select:
                self.controller.unit_visible_dict[unit_id] = not (self.controller.unit_visible_dict[unit_id])
            else:
                self.controller.unit_visible_dict = {unit_id: False for unit_id in self.controller.unit_ids}
                self.controller.unit_visible_dict[unit_id] = True
                self.roi_channel.blockSignals(True)
                self.roi_channel.setPos(x - radius, y - radius)
                self.roi_channel.blockSignals(False)

            r, _, _ = circle_from_roi(self.roi_units)
            self.roi_units.blockSignals(True)
            self.roi_units.setPos(x - r, y - r)
            self.roi_units.blockSignals(False)        

        # unit_positions = self.controller.unit_positions
        # pos = np.array([x, y])[None, :]
        # distances = np.sum((unit_positions - pos) **2, axis=1) ** 0.5
        # ind = np.argmin(distances)
        # if distances[ind] < 5.:
        #     radius = self.settings['radius_channel']
        #     unit_id = self.controller.unit_ids[ind]
        #     if multi_select:
        #         self.controller.unit_visible_dict[unit_id] = not(self.controller.unit_visible_dict[unit_id])
        #     else:
        #         self.controller.unit_visible_dict = {unit_id:False for unit_id in self.controller.unit_ids}
        #         self.controller.unit_visible_dict[unit_id] = True
        #         self.roi_channel.blockSignals(True)
        #         self.roi_channel.setPos(x - radius, y - radius)
        #         self.roi_channel.blockSignals(False)

            r, _, _ = circle_from_roi(self.roi_units)
            self.roi_units.blockSignals(True)
            self.roi_units.setPos(x - r, y - r)
            self.roi_units.blockSignals(False)

            # self.controller.update_visible_spikes()
            self._qt_on_unit_visibility_changed()

            self.notify_unit_visibility_changed()


    
    def _qt_on_add_units(self, x, y):
        self._qt_on_pick_unit(x, y, multi_select=True)
    
    # TODO handle better compte this is only for qt
    def compute(self):
        # TODO : option by method
        method_kwargs ={} 
        self.controller.compute_unit_positions(self.settings['method_localize_unit'], method_kwargs)
        unit_positions = self.controller.unit_positions
        brush = [self.controller.qcolors[u] for u in self.controller.unit_ids]
        self.scatter.setData(pos=unit_positions, pxMode=False, size=10, brush=brush)
        
        self.refresh()

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        from .utils_panel import _bg_color
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, HoverTool, Label, PanTool
        from bokeh.events import DoubleTap, Tap, Pan, PanEnd
        from .utils_panel import CustomCircle

        # Plot probe shape
        self.figure = bpl.figure(
            # width=400,
            # height=600,
            sizing_mode="stretch_both",
            tools="wheel_zoom,reset",
            active_scroll="wheel_zoom",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            match_aspect=True,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.figure.axis.visible = False
        self.figure.grid.visible = False
        self.figure.toolbar.logo = None

        # Draw probes
        vertices_list, connects_list, contours = self.get_probe_vertices()
        for vertices, connect in zip(vertices_list, connects_list):
            # Create patches for each contact
            start_idx = 0
            while start_idx < len(vertices):
                # Find end of current contact (where connect is False or end of array)
                end_idx = start_idx + 1
                while end_idx < len(vertices) and connect[end_idx - 1]:
                    end_idx += 1

                # Extract contact vertices
                contact = vertices[start_idx:end_idx]
                if len(contact) > 2:  # Need at least 3 points for a patch
                    xs = contact[:, 0].tolist()
                    ys = contact[:, 1].tolist()
                    # Draw both outline and fill
                    self.figure.patch(xs, ys, line_color="#7FFF00", fill_color="#7F7F0C", fill_alpha=0.1)

                start_idx = end_idx

        # Draw probe contours
        for contour in contours:
            if contour is not None:
                self.figure.line(contour[:, 0], contour[:, 1], line_color="#7FFF00")

        self.alpha_selected = 1
        self.alpha_unselected = 0.3
        self.unit_marker_size_unselected = 15
        self.unit_marker_size_selected = 20

        # Initialize unit glyphs
        unit_positions = self.controller.unit_positions
        initial_x = unit_positions[0, 0]
        initial_y = unit_positions[0, 1]

        # Create initial empty glyph that will be replaced by _update_unit_glyphs
        # Prepare unit appearance data
        unit_positions = self.controller.unit_positions
        colors = []
        border_colors = []
        alphas = []
        sizes = []

        for unit_id in self.controller.unit_ids:
            # color = self.controller.qcolors[uid].name()
            color = self.get_unit_color(unit_id)
            is_visible = self.controller.unit_visible_dict[unit_id]
            colors.append(color)
            alphas.append(self.alpha_selected if is_visible else self.alpha_unselected)
            sizes.append(self.unit_marker_size_selected if is_visible else self.unit_marker_size_unselected)
            border_colors.append("black" if is_visible else color)

        # Create new glyph
        data_source = ColumnDataSource(
            {
                "x": unit_positions[:, 0].tolist(),
                "y": unit_positions[:, 1].tolist(),
                "color": colors,
                "line_color": border_colors,
                "alpha": alphas,
                "size": sizes,
                "unit_id": [str(u) for u in self.controller.unit_ids],
            }
        )
        self.unit_glyphs = self.figure.scatter(
            "x", "y", source=data_source, size="size", fill_color="color", 
            line_color="line_color", alpha="alpha"
        )
        self.unit_glyphs.data_source = data_source  # Explicitly set data source

        # Add hover tool to new glyph
        hover = HoverTool(renderers=[self.unit_glyphs], tooltips=[("Unit", "@unit_id")])
        self.figure.add_tools(hover)

        # Add channel labels
        self.channel_labels = []
        for i, channel_id in enumerate(self.controller.channel_ids):
            contact_position = self.contact_positions[i, :]
            label = Label(
                x=contact_position[0],
                y=contact_position[1],
                text=f"{channel_id}",
                text_color="#FFFFFF",
                text_font_size="14pt",
            )
            self.figure.add_layout(label)
            self.channel_labels.append(label)

        self._panel_update_unit_glyphs()

        # Add tap tools
        self.figure.on_event(Tap, self._panel_on_tap)
        self.figure.on_event(DoubleTap, self._panel_on_double_tap)

        # Selection circles with dragging
        self.channel_circle = CustomCircle(initial_x, initial_y, self.settings['radius_channel'])
        self.figure.add_glyph(self.channel_circle.source, self.channel_circle.circle)

        # Unit circle (inner, draggable)
        self.unit_circle = CustomCircle(
            initial_x,
            initial_y,
            self.settings['radius_units'],
            line_color="#d68910",
            fill_color="#d68910",
            line_width=2,
            fill_alpha=0.2,
        )
        self.figure.add_glyph(self.unit_circle.source, self.unit_circle.circle)

        # Add pan tool for dragging
        pan_tool = PanTool()
        self.figure.add_tools(pan_tool)
        self.figure.toolbar.active_drag = pan_tool

        # Connect pan events for circle dragging
        self.figure.on_event(Pan, self._panel_on_pan)
        self.figure.on_event(PanEnd, self._panel_on_pan_end)
        self.should_update_channel_circle = False
        self.should_update_unit_circle = False

        # Main layout
        self.layout = pn.Column(
            self.figure,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

    def _panel_refresh(self):
        self._panel_update_unit_glyphs()

        # Update selection circles if only one unit is visible
        if sum(list(self.controller.unit_visible_dict.values())) == 1:
            selected_unit = np.flatnonzero(list(self.controller.unit_visible_dict.values()))[0]
            unit_positions = self.controller.unit_positions
            self.unit_circle.update_position(unit_positions[selected_unit, 0], unit_positions[selected_unit, 1])
            self.channel_circle.update_position(unit_positions[selected_unit, 0], unit_positions[selected_unit, 1])



    def _panel_update_unit_glyphs(self):
        """Update unit glyphs with current visibility states."""
        # # Remove existing glyphs
        # if hasattr(self, "unit_glyphs"):
        #     self.unit_glyphs.visible = False
        #     if self.unit_glyphs in self.figure.renderers:
        #         self.figure.renderers.remove(self.unit_glyphs)
        #     # Also remove any existing hover tools
        #     hover_tools = [t for t in self.figure.tools if isinstance(t, HoverTool)]
        #     for tool in hover_tools:
        #         self.figure.tools.remove(tool)

        # Prepare unit appearance data
        unit_positions = self.controller.unit_positions
        colors = []
        border_colors = []
        alphas = []
        sizes = []

        for unit_id in self.controller.unit_ids:
            color = self.get_unit_color(unit_id)
            is_visible = self.controller.unit_visible_dict[unit_id]
            colors.append(color)
            alphas.append(self.alpha_selected if is_visible else self.alpha_unselected)
            sizes.append(self.unit_marker_size_selected if is_visible else self.unit_marker_size_unselected)
            border_colors.append("black" if is_visible else color)

        # Create new glyph with all required data
        if hasattr(self, "unit_glyphs") and self.unit_glyphs.data_source is not None:
            data_source = {
                "x": unit_positions[:, 0].tolist(),
                "y": unit_positions[:, 1].tolist(),
                "color": colors,
                "line_color": border_colors,
                "alpha": alphas,
                "size": sizes,
                "unit_id": [str(u) for u in self.controller.unit_ids],
            }
            self.unit_glyphs.data_source.data.update(data_source)

        # chennel labels
        for label in self.channel_labels:
            label.visible = self.settings['show_channel_id']
            
        # # Add hover tool to new glyph
        # hover = HoverTool(renderers=[self.unit_glyphs], tooltips=[("Unit", "@unit_id")])
        # self.figure.add_tools(hover)



    def _panel_on_pan(self, event):
        if hasattr(event, "x") and hasattr(event, "y"):
            x, y = event.x, event.y
            print(f"On pan: {x}, {y}")
            if self.channel_circle.is_close_to_border(x, y):
                # Update channel circle
                self.should_update_channel_circle = True
                print("Should update channel circle")
            if self.unit_circle.is_close_to_border(x, y):
                # Update unit circle
                self.should_update_unit_circle = True
                print("Should update unit circle")

    def _panel_on_pan_end(self, event):
        print("On pan end")
        if hasattr(event, "x") and hasattr(event, "y"):
            x, y = event.x, event.y

            if self.should_update_channel_circle:
                self.channel_circle.update_position(x, y)
                # Update channel visibility
                visible_channel_inds = self.update_channel_visibility(x, y, self.settings['radius_channel'])
                self.controller.set_channel_visibility(visible_channel_inds)
                self.on_channel_visibility_changed()
                self.notify_channel_visibility_changed()

            if self.should_update_unit_circle:
                self.unit_circle.update_position(x, y)

                # Update unit visibility
                self.update_unit_visibility(x, y, self.settings['radius_units'])
                self._panel_update_unit_glyphs()  # Update glyphs to reflect new visibility

                # Notify other views
                self.notify_unit_visibility_changed()

            self.should_update_channel_circle = False
            self.should_update_unit_circle = False
    
    def _panel_on_tap(self, event):
        x, y = event.x, event.y
        unit_positions = self.controller.unit_positions
        distances = np.sqrt(np.sum((unit_positions - np.array([x, y])) ** 2, axis=1))
        closest_idx = np.argmin(distances)

        # Only select if within reasonable distance (5 um)
        if distances[closest_idx] < 5:
            # Get the actual unit position for better accuracy
            x = unit_positions[closest_idx, 0]
            y = unit_positions[closest_idx, 1]
            unit_id = self.controller.unit_ids[closest_idx]

            # Toggle visibility of clicked unit
            self.controller.unit_visible_dict[unit_id] = not self.controller.unit_visible_dict[unit_id]

            # Update circles position if this is the only visible unit
            if sum(self.controller.unit_visible_dict.values()) == 1:
                self.unit_circle.update_position(x, y)
                self.channel_circle.update_position(x, y)
                # Update channel visibility
                visible_channel_inds = self.update_channel_visibility(x, y, self.settings['radius_channel'])
                self.controller.set_channel_visibility(visible_channel_inds)
                self.param.trigger("channel_visibility_changed")

            self.param.trigger("unit_visibility_changed")
            self.on_unit_visibility_changed()
            self._refresh_view()  # Ensure view is updated after visibility changes

    def _panel_on_double_tap(self, event):
        # Find closest unit to click position
        x, y = event.x, event.y
        unit_positions = np.column_stack(
            (self.unit_glyphs.data_source.data["x"], self.unit_glyphs.data_source.data["y"])
        )
        distances = np.sqrt(np.sum((unit_positions - np.array([x, y])) ** 2, axis=1))
        closest_idx = np.argmin(distances)

        # Only select if within reasonable distance (5 um)
        if distances[closest_idx] < 5:
            # Get the actual unit position for better accuracy
            x = unit_positions[closest_idx, 0]
            y = unit_positions[closest_idx, 1]
            unit_id = self.controller.unit_ids[closest_idx]  # Use original unit_id from controller

            # Update visibility - make only this unit visible
            self.controller.unit_visible_dict = {u: False for u in self.controller.unit_ids}
            self.controller.unit_visible_dict[unit_id] = True

            # Update selection circles
            self.unit_circle.update_position(x, y)
            self.channel_circle.update_position(x, y)

            # Update channel visibility
            visible_channel_inds = self.update_channel_visibility(x, y, self.settings['radius_channel'])
            self.controller.set_channel_visibility(visible_channel_inds)

            # Auto zoom if enabled
            if self.settings['auto_zoom_on_unit_selection']:
                margin = 50
                self.figure.x_range.start = x - margin
                self.figure.x_range.end = x + margin
                self.figure.y_range.start = y - margin
                self.figure.y_range.end = y + margin

            # Notify other views
            self.notify_unit_visibility_changed()
            self.notify_channel_visibility_changed()
            self._refresh_view()



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
