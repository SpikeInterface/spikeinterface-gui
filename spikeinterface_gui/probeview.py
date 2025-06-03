import warnings
import numpy as np


from .view_base import ViewBase

from spikeinterface.postprocessing.unit_locations import possible_localization_methods


class ProbeView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _settings = [
            {'name': 'show_channel_id', 'type': 'bool', 'value': False},
            {'name': 'radius_channel', 'type': 'float', 'value': 50.},
            {'name': 'radius_units', 'type': 'float', 'value': 30.},
            {'name': 'auto_zoom_on_unit_selection', 'type': 'bool', 'value': True},
            {'name': 'method_localize_unit', 'type': 'list', 'limits': possible_localization_methods},
        ]
    
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        self.contact_positions = controller.get_contact_location()
        self.probes = controller.get_probegroup().probes
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        self._unit_positions = self.controller.unit_positions

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
        mask = dist < roi_radius
        visible_unit_ids = self.controller.unit_ids[mask]
        self.controller.set_visible_unit_ids(visible_unit_ids)

    def get_view_bounds(self, margin=20):
        xlim0 = np.min(self.contact_positions[:, 0]) - margin
        xlim1 = np.max(self.contact_positions[:, 0]) + margin
        ylim0 = np.min(self.contact_positions[:, 1]) - margin
        ylim1 = np.max(self.contact_positions[:, 1]) + margin
        return xlim0, xlim1, ylim0, ylim1

    def find_closest_unit(self, x, y, max_distance=5.0):
        unit_positions = self.controller.unit_positions
        pos = np.array([x, y])[None, :]
        distances = np.sum((unit_positions - pos) ** 2, axis=1) ** 0.5
        ind = np.argmin(distances)
        if distances[ind] < max_distance:
            return self.controller.unit_ids[ind], ind
        return None, None

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingDoubleClickToPosition
    
        
        self.layout = QT.QVBoxLayout()
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.viewBox = ViewBoxHandlingDoubleClickToPosition()
        self.viewBox.doubleclicked.connect(self._qt_on_pick_unit)
        self.viewBox.ctrl_doubleclicked.connect(self._qt_on_add_units)
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.plot.getViewBox().disableAutoRange()
        self.graphicsview.setCentralItem(self.plot)
        self.plot.getViewBox().setAspectLocked(lock=True, ratio=1)
        self.plot.hideButtons()
    
        # probes
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
        

        radius = self.settings['radius_units']
        x, y = self.contact_positions.mean(axis=0)
        self.roi_units = pg.CircleROI([x - radius, y - radius], [radius * 2, radius * 2],  pen='#d68910') #pen=(4,9),
        self.plot.addItem(self.roi_units)
        

        # units
        unit_positions = self.controller.unit_positions
        brush = [self.get_unit_color(u) for u in self.controller.unit_ids]
        self.scatter = pg.ScatterPlotItem(pos=unit_positions, pxMode=False, size=10, brush=brush)
        self.plot.addItem(self.scatter)

        # range
        xlim0, xlim1, ylim0, ylim1 = self.get_view_bounds()
        self.plot.setXRange(xlim0, xlim1)
        self.plot.setYRange(ylim0, ylim1)

        self.roi_channel.sigRegionChanged.connect(self._qt_on_roi_channel_changed)
        # self.roi_channel.sigRegionChangeFinished.connect(self._qt_on_roi_channel_changed)

        self.roi_units.sigRegionChangeFinished.connect(self._qt_on_roi_units_changed)

    def _qt_refresh(self):
        current_unit_positions = self.controller.unit_positions
        # if not np.array_equal(current_unit_positions, self._unit_positions):
        if True:
        
            self._unit_positions = current_unit_positions
            brush = [self.get_unit_color(u) for u in self.controller.unit_ids]
            self.scatter.setData(pos=current_unit_positions, pxMode=False, size=10, brush=brush)
        
        r, x, y = circle_from_roi(self.roi_channel)
        radius = self.settings['radius_channel']

        self.roi_channel.sigRegionChanged.disconnect(self._qt_on_roi_channel_changed)
        self.roi_channel.setSize(radius * 2)
        self.roi_channel.setPos(x - radius, y-radius)
        self.roi_channel.sigRegionChanged.connect(self._qt_on_roi_channel_changed)

        self.roi_units.sigRegionChangeFinished.disconnect(self._qt_on_roi_units_changed)
        r, x, y = circle_from_roi(self.roi_units)
        radius = self.settings['radius_units']
        self.roi_units.setSize(radius * 2)
        self.roi_units.setPos(x - radius, y-radius)
        self.roi_units.sigRegionChangeFinished.connect(self._qt_on_roi_units_changed)

        
        if self.settings['show_channel_id']:
            for label in self.channel_labels:
                label.show()
        else:
            for label in self.channel_labels:
                label.hide()
            
    
    def _qt_update_channel_visibility_from_roi(self, emit_signals=False):
        r, x, y = circle_from_roi(self.roi_channel)
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
            self._qt_update_channel_visibility_from_roi(emit_signals=True)
            self.roi_channel.blockSignals(False)
    
    def _qt_on_roi_units_changed(self, emit_signals=True):
        r, x, y = circle_from_roi(self.roi_units)

        self.settings.blockSignals(True)
        self.settings['radius_units'] = r
        self.settings.blockSignals(False)


        if emit_signals:
            self.roi_units.blockSignals(True)
            self.update_unit_visibility(x, y, r)
            self.notify_unit_visibility_changed()
            self._qt_on_unit_visibility_changed(auto_zoom=False)
            self.roi_units.blockSignals(False)
        
        # also change channel
        self.roi_channel.blockSignals(True)
        radius = self.settings['radius_channel']
        self.roi_channel.setPos(x - radius, y - radius)
        self.roi_channel.blockSignals(False)
        self._qt_on_roi_channel_changed(emit_signals=False)
            
    def _qt_on_unit_visibility_changed(self, auto_zoom=None):
        import pyqtgraph as pg

        # this change the ROI and so change also channel_visibility
        visible_mask = self.controller.get_units_visibility_mask()

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

            self._qt_update_channel_visibility_from_roi(emit_signals=False)
        
        # change scatter pen for selection
        pen = [pg.mkPen('white', width=4)
                    if self.controller.get_unit_visibility(u) else pg.mkPen('black', width=4)
                    for u in self.controller.unit_ids]
        self.scatter.setPen(pen)
        brush = [self.get_unit_color(u) for u in self.controller.unit_ids]
        self.scatter.setBrush(brush)
        
        # auto zoom
        if auto_zoom is None:
            auto_zoom = self.settings['auto_zoom_on_unit_selection']
        
        if auto_zoom:
            visible_pos = self.controller.unit_positions[visible_mask, :]
            if visible_pos.shape[0] > 0:
                x_min, x_max = np.min(visible_pos[:, 0]), np.max(visible_pos[:, 0])
                y_min, y_max = np.min(visible_pos[:, 1]), np.max(visible_pos[:, 1])
                margin =50
                self.plot.setXRange(x_min - margin, x_max+ margin)
                self.plot.setYRange(y_min - margin, y_max+ margin)

    
    def _qt_on_pick_unit(self, x, y, multi_select=False):
        unit_id, _ = self.find_closest_unit(x, y)
        if unit_id is not None:
            radius = self.settings["radius_channel"]
            if multi_select:
                self.controller.set_unit_visibility(unit_id, not self.controller.get_unit_visibility(unit_id))
            else:
                self.controller.set_visible_unit_ids([unit_id])
                self.roi_channel.blockSignals(True)
                self.roi_channel.setPos(x - radius, y - radius)
                self.roi_channel.blockSignals(False)

            r, _, _ = circle_from_roi(self.roi_units)
            self.roi_units.blockSignals(True)
            self.roi_units.setPos(x - r, y - r)
            self.roi_units.blockSignals(False)        

            r, _, _ = circle_from_roi(self.roi_units)
            self.roi_units.blockSignals(True)
            self.roi_units.setPos(x - r, y - r)
            self.roi_units.blockSignals(False)

            self.notify_unit_visibility_changed()
            self._qt_on_unit_visibility_changed()
            


    
    def _qt_on_add_units(self, x, y):
        self._qt_on_pick_unit(x, y, multi_select=True)
    
    def _compute(self):
        method_kwargs ={} 
        self.controller.compute_unit_positions(self.settings['method_localize_unit'], method_kwargs)
        
    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, HoverTool, Label, PanTool
        from bokeh.events import Tap, PanStart, PanEnd
        from .utils_panel import CustomCircle, _bg_color

        # Plot probe shape
        self.figure = bpl.figure(
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
            color = self.get_unit_color(unit_id)
            is_visible = self.controller.get_unit_visibility(unit_id)
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
        # self.unit_glyphs.data_source = data_source  # Explicitly set data source

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
            if not self.settings["show_channel_id"]:
                label.visible = False
            self.figure.add_layout(label)
            self.channel_labels.append(label)

        self._panel_update_unit_glyphs()

        # Add tap tools
        self.figure.on_event(Tap, self._panel_on_tap)

        # Selection circles with dragging
        self.channel_circle = CustomCircle(initial_x, initial_y, self.settings['radius_channel'])
        self.channel_circle.add_to_figure(self.figure)

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
        self.unit_circle.add_to_figure(self.figure)


        # Add pan tool for dragging
        pan_tool = PanTool()
        self.figure.add_tools(pan_tool)
        self.figure.toolbar.active_drag = None

        # Connect pan events for circle dragging
        self.figure.on_event(PanStart, self._panel_on_pan_start)
        self.figure.on_event(PanEnd, self._panel_on_pan_end)
        # these variables will hold the start x, y position of the drag
        self.should_move_channel_circle = None
        self.should_move_unit_circle = None
        self.should_resize_channel_circle = None
        self.should_resize_unit_circle = None

        # Main layout
        self.layout = pn.Column(
            self.figure,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

    def _panel_refresh(self):
        from bokeh.models import Range1d

        # Update unit positions
        self._panel_update_unit_glyphs()

        # chennel labels
        for label in self.channel_labels:
            label.visible = self.settings['show_channel_id']

        # Update selection circles if only one unit is visible

        selected_unit_indices = self.controller.get_visible_unit_indices()
        if len(selected_unit_indices) == 1:
            unit_index = selected_unit_indices[0]
            unit_positions = self.controller.unit_positions
            x, y = unit_positions[unit_index, 0], unit_positions[unit_index, 1]
            # Update circles position
            self.unit_circle.update_position(x, y)

            self.channel_circle.update_position(x, y)
            # Update channel visibility
            visible_channel_inds = self.update_channel_visibility(x, y, self.settings['radius_channel'])
            self.controller.set_channel_visibility(visible_channel_inds)

        if self.settings['auto_zoom_on_unit_selection']:
            visible_mask = self.controller.get_units_visibility_mask()
            if sum(visible_mask) > 0:
                visible_pos = self.controller.unit_positions[visible_mask, :]
                x_min, x_max = np.min(visible_pos[:, 0]), np.max(visible_pos[:, 0])
                y_min, y_max = np.min(visible_pos[:, 1]), np.max(visible_pos[:, 1])
                margin = 50
                self.figure.x_range = Range1d(x_min - margin, x_max + margin)
                self.figure.y_range = Range1d(y_min - margin, y_max + margin)

    def _panel_update_unit_glyphs(self):
        # Prepare unit appearance data
        unit_positions = self.controller.unit_positions
        colors = []
        border_colors = []
        alphas = []
        sizes = []

        for unit_id in self.controller.unit_ids:
            color = self.get_unit_color(unit_id)
            is_visible = self.controller.get_unit_visibility(unit_id)
            colors.append(color)
            alphas.append(self.alpha_selected if is_visible else self.alpha_unselected)
            sizes.append(self.unit_marker_size_selected if is_visible else self.unit_marker_size_unselected)
            border_colors.append("black" if is_visible else color)

        # Create new glyph with all required data
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
            
    def _panel_on_pan_start(self, event):
        self.figure.toolbar.active_drag = None
        x, y = event.x, event.y

        if self.unit_circle.is_close_to_diamond(x, y):
            self.should_resize_unit_circle = [x, y]
            self.unit_circle.select()
        elif self.unit_circle.is_position_inside(x, y, skip_other_positions=self._unit_positions):
            self.figure.toolbar.active_drag = None
            # Update unit circle
            self.should_move_unit_circle = [x, y]
            self.unit_circle.select()
        elif self.channel_circle.is_close_to_diamond(x, y):
            self.should_resize_channel_circle = [x, y]
            self.channel_circle.select()
        elif self.channel_circle.is_position_inside(x, y, skip_other_positions=self._unit_positions):
            self.figure.toolbar.active_drag = None
            # Update channel circle
            self.should_move_channel_circle = [x, y]
            self.channel_circle.select()

    def _panel_on_pan_end(self, event):
        x, y = event.x, event.y

        if self.should_move_channel_circle is not None:
            start_x, start_y = self.should_move_channel_circle
            old_center = self.channel_circle.center
            self.channel_circle.update_position(x, y, start_x, start_y)
            new_x, new_y = self.channel_circle.center

            # Update channel visibility
            visible_channel_inds = self.update_channel_visibility(new_x, new_y, self.settings['radius_channel'])
            if len(visible_channel_inds) == 0:
                warnings.warn("At least 1 channel must be visible")
                self.channel_circle.update_position(*old_center)
            else:
                self.controller.set_channel_visibility(visible_channel_inds)
            self.channel_circle.unselect()
            self.on_channel_visibility_changed()
            self.notify_channel_visibility_changed()

        elif self.should_move_unit_circle:
            start_x, start_y = self.should_move_unit_circle
            self.unit_circle.update_position(x, y, start_x, start_y)
            self.unit_circle.unselect()
            # Update unit visibility
            new_x, new_y = self.unit_circle.center
            self.update_unit_visibility(new_x, new_y, self.settings['radius_units'])
            self.notify_unit_visibility_changed()
            self._panel_update_unit_glyphs()  # Update glyphs to reflect new visibility

        elif self.should_resize_channel_circle is not None:
            x_center, y_center = self.channel_circle.center
            old_radius = self.channel_circle.radius
            new_radius = np.sqrt((x - x_center) ** 2 + (y - y_center) ** 2)
            # Update channel visibility
            visible_channel_inds = self.update_channel_visibility(x_center, y_center, new_radius)
            if len(visible_channel_inds) == 0:
                warnings.warn("Channel radius too small! At least 1 channel must be visible")
                self.channel_circle.update_radius(old_radius)
            else:
                self.settings["radius_channel"] = new_radius
                self.channel_circle.update_radius(new_radius)
            self.channel_circle.unselect()
            visible_channel_inds = self.update_channel_visibility(x_center, y_center, self.settings["radius_channel"])

            self.controller.set_channel_visibility(visible_channel_inds)
            self.on_channel_visibility_changed()
            self.notify_channel_visibility_changed()
        elif self.should_resize_unit_circle is not None:
            x_center, y_center = self.unit_circle.center
            new_radius = np.sqrt((x - x_center) ** 2 + (y - y_center) ** 2)
            self.unit_circle.update_radius(new_radius)
            self.unit_circle.unselect()
            self.settings["radius_units"] = new_radius
            # Update unit visibility
            self.update_unit_visibility(x_center, y_center, self.settings['radius_units'])
            self.notify_unit_visibility_changed()
            self._panel_update_unit_glyphs()

        self.should_move_channel_circle = None
        self.should_move_unit_circle = None
        self.should_resize_channel_circle = None
        self.should_resize_unit_circle = None


    def _panel_on_tap(self, event):
        x, y = event.x, event.y
        unit_positions = self.controller.unit_positions
        distances = np.sqrt(np.sum((unit_positions - np.array([x, y])) ** 2, axis=1))
        closest_idx = np.argmin(distances)
        if event.modifiers["ctrl"]:
            select_only = False
        else:
            select_only = True

        # Only select if within reasonable distance (5 um)
        if distances[closest_idx] < 5:
            # Get the actual unit position for better accuracy
            x = unit_positions[closest_idx, 0]
            y = unit_positions[closest_idx, 1]
            unit_id = self.controller.unit_ids[closest_idx]

            # Toggle visibility of clicked unit
            if select_only:
                # Update visibility - make only this unit visible
                self.controller.set_all_unit_visibility_off()
                self.controller.set_unit_visibility(unit_id, True)

            else:
                self.controller.set_unit_visibility(unit_id, not self.controller.get_unit_visibility(unit_id))
                # Update circles position if this is the only visible unit
                if len(self.controller.get_visible_unit_ids()) == 1:
                    select_only = True

            
            if select_only:
                # Update selection circles
                self.unit_circle.update_position(x, y)
                self.channel_circle.update_position(x, y)

                # Update channel visibility
                visible_channel_inds = self.update_channel_visibility(x, y, self.settings['radius_channel'])
                self.controller.set_channel_visibility(visible_channel_inds)
                self.notify_channel_visibility_changed
            self.notify_unit_visibility_changed()
            self._panel_update_unit_glyphs()


def circle_from_roi(roi):
    r = roi.state['size'][0] / 2
    x = roi.state['pos'].x() + r
    y = roi.state['pos'].y() + r
    return r, x, y



ProbeView._gui_help_txt = """
## Probe View
Show contact and probe shape.
Units are color coded.

### Controls
- **left click** : select single unit
- **ctrl + left click** : add unit to selection
- **mouse drag from within circle** : change channel visibilty and unit visibility on other views
- **mouse drag from "diamond"** : change channel / unit radii size
"""
