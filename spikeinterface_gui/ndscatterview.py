"""
This try to mimic `RGGobi viewer package <http://www.ggobi.org/rggobi/>`_.
"""

import itertools
import numpy as np
from matplotlib.path import Path as mpl_path

from .view_base import ViewBase


class NDScatterView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _depend_on = ['principal_components']
    _settings = [
           {'name': 'show_projection', 'type': 'bool', 'value': True },
           {'name': 'refresh_interval', 'type': 'int', 'value': 80 },
           {'name': 'num_step', 'type': 'int', 'value':  20, 'limits' : [5, 100] },
           {'name': 'num_pc_per_channel', 'type': 'int', 'value':  2, 'limits' : [1, 100] },
        ]
    
    def __init__(self, controller=None, parent=None, backend="qt"):
        
        assert controller.has_extension('principal_components')

        self.pc_unit_index, self.pc_data = controller.get_all_pcs()
        self.data = self.pc_data.swapaxes(1,2).reshape(self.pc_data.shape[0], -1)
        self.random_spikes_indices = controller.random_spikes_indices
        
        if self.data.shape[1] == 1:
            # corner case one PC and one channel only, then force 2D
            data = np.zeros((self.data.shape[0], 2), dtype=self.data.dtype)
            data[:, 0] = self.data[:, 0]
            data[:, 1] = self.data[:, 0]
            self.data = data

        ndim = self.data.shape[1]
        self.selected_comp = np.ones((ndim), dtype='bool')
        self.projection = self.get_one_random_projection()

        #estimate limts
        data = self.data
        if data.shape[0] > 1000:
            inds = np.random.choice(data.shape[0], 1000, replace=False)
            data = data[inds, :]
        projected = self.apply_dot(data)
        projected_2d = projected[:, :2]
        self.limit = float(np.percentile(np.abs(projected_2d), 95) * 2.)
        self.limit = max(self.limit, 0.1)  # ensure limit is at least 0.1


        self.hyper_faces = list(itertools.permutations(range(ndim), 2))
        self.n_face = -1

        self.tour_step = 0
        self.auto_update_limit = True
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

        
    def new_tour_step(self):
        num_step = self.settings['num_step']
        ndim = self.data.shape[1]
        
        if self.tour_step == 0:
            self.tour_steps = np.empty( (ndim , 2 ,  num_step))
            arrival = self.get_one_random_projection()
            for i in range(ndim):
                for j in range(2):
                    self.tour_steps[i,j , : ] = np.linspace(self.projection[i,j] , arrival[i,j] , num_step)
            m = np.sqrt(np.sum(self.tour_steps**2, axis=0))
            m = m[np.newaxis, : ,  :]
            self.tour_steps /= m
        
        self.projection = self.tour_steps[:,:,self.tour_step]
        
        self.tour_step+=1
        if self.tour_step>=num_step:
            self.tour_step = 0

        # avoid printing refresh time
        self._refresh(update_colors=False, update_components=False)

    def next_face(self):
        self.n_face += 1
        self.n_face = self.n_face%len(self.hyper_faces)
        ndim = self.data.shape[1]
        self.projection = np.zeros( (ndim, 2))
        i, j = self.hyper_faces[self.n_face]
        self.projection[i,0] = 1.
        self.projection[j,1] = 1.
        self.tour_step = 0
        self.refresh()

    def get_one_random_projection(self):
        ndim = self.data.shape[1]
        projection = np.random.rand(ndim,2)*2-1.
        projection[~self.selected_comp] = 0
        m = np.sqrt(np.sum(projection**2, axis=0))
        ok = m > 0
        projection[:, ok] /= m[ok]
        return projection

    def random_projection(self):
        self.update_selected_components()
        self.projection = self.get_one_random_projection()
        self.tour_step = 0
        # here we don't want to update the components because it's been done already!
        self.refresh(update_components=False)

    def on_spike_selection_changed(self):
        self.refresh()

    def on_unit_visibility_changed(self):
        self.random_projection()
    
    def on_channel_visibility_changed(self):
        self.random_projection()

    def apply_dot(self, data):
        projected = np.dot(data[:, self.selected_comp], self.projection[self.selected_comp, :])
        return projected

    def get_plotting_data(self, return_spike_indices=False):
        scatter_x = {}
        scatter_y = {}
        all_limits = []
        spike_indices = {}
        for unit_ind, unit_id in self.controller.iter_visible_units():
            mask = np.flatnonzero(self.pc_unit_index == unit_ind)
            projected = self.apply_dot(self.data[mask, :])
            scatter_x[unit_id] = projected[:, 0]
            scatter_y[unit_id] = projected[:, 1]
            if self.auto_update_limit and len(projected) > 0:
                projected_2d = projected[:, :2]
                all_limits.append(float(np.percentile(np.abs(projected_2d), 95) * 2.))
            if return_spike_indices:
                spike_indices[unit_id] = mask
        if len(all_limits) > 0 and self.auto_update_limit:
            self.limit = max(all_limits)
        
        self.limit = max(self.limit, 0.1)  # ensure limit is at least 0.1

        mask = np.isin(self.random_spikes_indices, self.controller.get_indices_spike_selected())
        data_sel = self.data[mask, :]
        if len(data_sel) == 0:
            selected_scatter_x = np.array([])
            selected_scatter_y = np.array([])
        else:
            projected_select = self.apply_dot(data_sel)
            selected_scatter_x = projected_select[:, 0]
            selected_scatter_y = projected_select[:, 1]

        if return_spike_indices:
            return scatter_x, scatter_y, selected_scatter_x, selected_scatter_y, spike_indices
        else:
            return scatter_x, scatter_y, selected_scatter_x, selected_scatter_y
    

    def update_selected_components(self):
        n_pc_per_chan = self.pc_data.shape[1]
        n = min(self.settings['num_pc_per_channel'], n_pc_per_chan)
        self.selected_comp[:] = False
        for i in range(n):
            self.selected_comp[self.controller.visible_channel_inds * n_pc_per_chan+i] = True

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingLassoAndGain, add_stretch_to_qtoolbar


        self.layout = QT.QHBoxLayout()

        # toolbar
        tb = self.qt_widget.view_toolbar
        but = QT.QPushButton('Random')
        tb.addWidget(but)
        but.clicked.connect(self.random_projection)
        but = QT.QPushButton('Random tour', checkable = True)
        tb.addWidget(but)
        but.clicked.connect(self._qt_start_stop_tour)

        but = QT.QPushButton('next face')
        tb.addWidget(but)
        but.clicked.connect(self.next_face)


        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)

        # self.toolbar.addStretch()
        # self.graphicsview2 = pg.GraphicsView()
        # self.toolbar.addWidget(self.graphicsview2)

        self.timer_tour = QT.QTimer(interval=100)
        self.timer_tour.timeout.connect(self.new_tour_step)
        
        # initialize plot

        self.viewBox = ViewBoxHandlingLassoAndGain()
        self.viewBox.gain_zoom.connect(self._qt_gain_zoom)
        self.viewBox.lasso_drawing.connect(self._qt_on_lasso_drawing)
        self.viewBox.lasso_finished.connect(self._qt_on_lasso_finished)
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        self.scatter = pg.ScatterPlotItem(size=3, pxMode = True)
        self.plot.addItem(self.scatter)
        
        
        brush = QT.QColor('white')
        brush.setAlpha(200)
        self.scatter_select = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=brush, size=11, pxMode = True)
        self.plot.addItem(self.scatter_select)
        self.scatter_select.setZValue(1000)
        
        
        self.lasso = pg.PlotCurveItem(pen='#7FFF00')
        self.plot.addItem(self.lasso)
        
        ndim = self.data.shape[1]

        self.direction_lines = pg.PlotCurveItem(x=[], y=[], pen=(255,255,255))
        self.direction_data = np.zeros( (ndim*2, 2))
        self.plot.addItem(self.direction_lines)


        # self.plot2 = pg.PlotItem(viewBox=ViewBoxHandlingLassoAndGain(lockAspect=True))
        # self.graphicsview2.setCentralItem(self.plot2)
        # self.plot2.hideButtons()
        # angles = np.arange(0,360, .1)
        # self.circle = pg.PlotCurveItem(x=np.cos(angles), y=np.sin(angles), pen=(255,255,255))
        # self.plot2.addItem(self.circle)
        # self.direction_lines = pg.PlotCurveItem(x=[], y=[], pen=(255,255,255))
        # self.direction_data = np.zeros( (ndim*2, 2))
        # self.plot2.addItem(self.direction_lines)
        # self.plot2.setXRange(-1, 1)
        # self.plot2.setYRange(-1, 1)
        
        # n_pc_per_channel = self.pc_data.shape[1]
        # self.proj_labels = []
        # for i in range(ndim):
        #     chan_ind = i // n_pc_per_channel
        #     chan_id = self.controller.channel_ids[chan_ind]
        #     pc = i % n_pc_per_channel
        #     text = f'{chan_id}PC{pc}'
        #     label = pg.TextItem(text, color=(1,1,1), anchor=(0.5, 0.5), border=None, fill=pg.mkColor((128,128,128, 180)))
        #     self.proj_labels.append(label)
        #     self.plot2.addItem(label)
        
        # self.graphicsview2.setMaximumSize(200, 200)
        
        self.settings.param('num_pc_per_channel').setLimits((1, self.pc_data.shape[1]))

        # the color vector is precomputed
        # spike_colors = self.controller.get_spike_colors(self.pc_unit_index)
        # self.spike_qtcolors = np.array([pg.mkBrush(c) for c in spike_colors])
        
    def _qt_refresh(self, update_components=True, update_colors=True):
        import pyqtgraph as pg

        # update visible channel
        if update_components:
            self.update_selected_components()

        #ndscatter
        # TODO sam: I have the feeling taht it is a bit slow
        self.scatter.clear()

        # scatter_x, scatter_y, spike_indices, selected_scatter_x, selected_scatter_y = self.get_plotting_data(concatenated=True)
        # # scatter_colors = self.spike_qtcolors[spike_indices].tolist()
        # spike_colors = self.controller.get_spike_colors(self.pc_unit_index[spike_indices])
        # scatter_colors = [pg.mkBrush(c) for c in spike_colors]
        # self.scatter.setData(x=scatter_x, y=scatter_y, brush=scatter_colors, pen=pg.mkPen(None))
        # self.scatter_select.setData(selected_scatter_x, selected_scatter_y)

        scatter_x, scatter_y, selected_scatter_x, selected_scatter_y = self.get_plotting_data()
        for unit_index, unit_id in self.controller.iter_visible_units():
            color = self.get_unit_color(unit_id)
            self.scatter.addPoints(x=scatter_x[unit_id], y=scatter_y[unit_id],  pen=pg.mkPen(None), brush=color)
        self.scatter_select.setData(selected_scatter_x, selected_scatter_y)


        # TODO sam : kepp the old implementation in mind
        # for unit_index, unit_id in enumerate(self.controller.unit_ids):
        #     if not self.controller.get_unit_visibility(unit_id):
        #         continue
        #     #~ data = self.data_by_label(k)
        #     mask = self.pc_unit_index == unit_index
        #     data = self.data[mask, :]
        #     #~ projected = np.dot(data, self.projection )
        #     projected = self.apply_dot(data)
        #     #~ color = self.get_color(k)
        #     color = self.get_unit_color(unit_id)
        #     self.scatter.addPoints(x=projected[:,0], y=projected[:,1],  pen=pg.mkPen(None), brush=color)

        if self.settings['show_projection']:
            proj = self.projection.copy()
            proj[~self.selected_comp, :] = 0
            self.direction_data[::, :] =0
            self.direction_data[::2, :] = proj
            self.direction_lines.setData(self.direction_data[:,0], self.direction_data[:,1])
        else:
            self.direction_lines.setData([], [])


        #projection axes
        # proj = self.projection.copy()
        # proj[~self.selected_comp, :] = 0
        # self.direction_data[::, :] =0
        # self.direction_data[::2, :] = proj
        # self.direction_lines.setData(self.direction_data[:,0], self.direction_data[:,1])
        # for i, label in enumerate(self.proj_labels):
        #     if self.selected_comp[i]:
        #         label.setPos(self.projection[i,0], self.projection[i,1])
        #         label.show()
        #     else:
        #         label.hide()

        self.plot.setXRange(-self.limit, self.limit)
        self.plot.setYRange(-self.limit, self.limit)
        
        # self.graphicsview.repaint()
            
    
    def _qt_start_stop_tour(self, checked):
        if checked:
            self.tour_step = 0
            self.timer_tour.setInterval(int(self.settings['refresh_interval']))
            self.timer_tour.start()
            self.auto_update_limit = False
        else:
            self.timer_tour.stop()
            self.auto_update_limit = True
    
    def _qt_gain_zoom(self, factor):
        self.limit /= factor
        l = float(self.limit)
        self.plot.setXRange(-self.limit, self.limit)
        self.plot.setYRange(-self.limit, self.limit)
        # self.refresh()
    
    def _qt_on_lasso_drawing(self, points):
        points = np.array(points)
        self.lasso.setData(points[:, 0], points[:, 1])
    
    def _qt_on_lasso_finished(self, points):
        self.lasso.setData([], [])
        vertices = np.array(points)
        
        # inside lasso and visibles
        ind_visibles,   = np.nonzero(np.isin(self.random_spikes_indices, self.controller.get_indices_spike_visible()))
        projected = self.apply_dot(self.data[ind_visibles, :])
        inside = inside_poly(projected, vertices)
        
        inds = self.random_spikes_indices[ind_visibles[inside]]
        self.controller.set_indices_spike_selected(inds)
        
        self.refresh()
        self.notify_spike_selection_changed()


    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, LassoSelectTool, Range1d
        from bokeh.events import MouseWheel

        from .utils_panel import _bg_color, slow_lasso

        self.lasso_tool = LassoSelectTool()

        self.scatter_fig = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.scatter_fig.toolbar.logo = None
        self.scatter_fig.grid.visible = False
        self.scatter_fig.add_tools(self.lasso_tool)
        self.scatter_fig.toolbar.active_drag = None
        self.scatter_fig.xgrid.grid_line_color = None
        self.scatter_fig.ygrid.grid_line_color = None
        self.scatter_fig.x_range = Range1d(-self.limit, self.limit)
        self.scatter_fig.y_range = Range1d(-self.limit, self.limit)
        
        # remove the bokeh mousewheel zoom and keep only this one
        self.scatter_fig.on_event(MouseWheel, self._panel_gain_zoom)

        self.scatter_source = ColumnDataSource({"x": [], "y": [], "color": []})
        self.scatter_select_source = ColumnDataSource({"x": [], "y": [], "color": []})

        self.scatter = self.scatter_fig.scatter("x", "y", source=self.scatter_source, size=3, color="color", alpha=0.7)
        self.scatter_select = self.scatter_fig.scatter("x", "y", source=self.scatter_select_source,
                                                       size=11, color="white", alpha=0.8)

        # toolbar
        self.next_face_button = pn.widgets.Button(name="Next Face", button_type="default", width=100)
        self.next_face_button.on_click(self._panel_next_face)

        self.random_button = pn.widgets.Button(name="Random", button_type="default", width=100)
        self.random_button.on_click(self._panel_random_projection)

        self.random_tour_button = pn.widgets.Toggle(name="Random Tour", button_type="default", width=100)
        self.random_tour_button.param.watch(self._panel_start_stop_tour, "value")

        # self.select_toggle_button = pn.widgets.Toggle(name="Select")
        # self.select_toggle_button.param.watch(self._panel_on_select_button, 'value')

        # TODO: add a lasso selection
        # slow_lasso(self.scatter_source, self._on_panel_lasso_selected)

        self.toolbar = pn.Row(
            self.next_face_button, self.random_button, self.random_tour_button, sizing_mode="stretch_both",
            styles={"flex": "0.15"}
        )

        self.layout = pn.Column(
            self.toolbar,
            self.scatter_fig,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

        self.tour_timer = None

    def _panel_refresh(self, update_components=True, update_colors=True):
        if update_components:
            self.update_selected_components()
        scatter_x, scatter_y, selected_scatter_x, selected_scatter_y = self.get_plotting_data()

        xs, ys, colors = [], [], []
        for unit_id in scatter_x.keys():
            color = self.get_unit_color(unit_id)
            xs.extend(scatter_x[unit_id])
            ys.extend(scatter_y[unit_id])
            if update_colors:
                colors.extend([color] * len(scatter_x[unit_id]))

        if not update_colors:
            colors = self.scatter_source.data.get("color")

        self.scatter_source.data = {
            "x": xs,
            "y": ys,
            "color": colors,
        }

        self.scatter_select_source.data = {
            "x": selected_scatter_x,
            "y": selected_scatter_y,
        }

        # TODO: handle selection with lasso
        # mask = np.isin(self.random_spikes_indices, self.controller.get_indices_spike_selected())
        # selected_indices = np.flatnonzero(mask)
        # self.scatter_source.selected.indices = selected_indices.tolist()

        self.scatter_fig.x_range.start = -self.limit
        self.scatter_fig.x_range.end = self.limit
        self.scatter_fig.y_range.start = -self.limit
        self.scatter_fig.y_range.end = self.limit

    def _panel_gain_zoom(self, event):
        from bokeh.models import Range1d

        factor = 1.3 if event.delta > 0 else 1 / 1.3
        self.limit /= factor
        self.scatter_fig.x_range.start = -self.limit
        self.scatter_fig.x_range.end = self.limit
        self.scatter_fig.y_range.start = -self.limit
        self.scatter_fig.y_range.end = self.limit

    def _panel_next_face(self, event):
        self.next_face()

    def _panel_random_projection(self, event):
        self.random_projection()

    def _panel_start_stop_tour(self, event):
        import panel as pn
        if event.new:
            self.tour_step = 0
            self.tour_timer = pn.state.add_periodic_callback(self.new_tour_step, period=self.settings['refresh_interval'])
            self.auto_update_limit = False
        else:
            if self.tour_timer is not None:
                self.tour_timer.stop()
                self.tour_timer = None
                self.auto_update_limit = True

    def _panel_on_select_button(self, event):
        if self.select_toggle_button.value:
            self.scatter_fig.toolbar.active_drag = self.lasso_tool
        else:
            self.scatter_fig.toolbar.active_drag = None
            self.scatter_source.selected.indices = []
            # self._on_panel_lasso_selected(None, None, None)


    # TODO: Handle lasso selection and updates
    # def _on_panel_lasso_selected(self, attr, old, new):
    #     if len(self.scatter_source.selected.indices) == 0:
    #         self.notify_spike_selection_changed()
    #         self.refresh()
    #         return

    #     # inside lasso and visibles
    #     inside = self.scatter_source.selected.indices

    #     inds = self.random_spikes_indices[inside]
    #     self.controller.set_indices_spike_selected(inds)

    #     self.refresh()
    #     self.notify_spike_selection_changed()


def inside_poly(data, vertices):
    return mpl_path(vertices).contains_points(data)


NDScatterView._gui_help_txt = """
## N-dimensional Scatter View

This view projects n-dimensional principal components (num channels x num components) of the selected units
in a 2D sub-space.

### Controls
- **next face** : rotates the projection
- **random** : randomly choose a projection
- **random tour** : runs dynamic "tour" of the pcs
"""
# - **select** : activates lasso selection
