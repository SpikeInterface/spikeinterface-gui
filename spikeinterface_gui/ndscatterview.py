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
        self.projection = np.zeros( (ndim, 2))
        self.projection[0,0] = 1.
        self.projection[1,1] = 1.

        #estimate limts
        data = self.data
        if data.shape[0] > 1000:
            inds = np.random.choice(data.shape[0], 1000, replace=False)
            data = data[inds, :]
        projected = self.apply_dot(data)
        self.limit = float(np.percentile(np.abs(projected), 95) * 2.)

        self.hyper_faces = list(itertools.permutations(range(ndim), 2))
        self.n_face = -1

        self.tour_step = 0
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
            
        self.refresh()

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
        self.projection = self.get_one_random_projection()
        self.tour_step = 0
        self.refresh()


    def on_spike_selection_changed(self):
        self.refresh()

    def on_unit_visibility_changed(self):
        # this do refreh also
        self.random_projection()
    
    def on_channel_visibility_changed(self):
        # this do refreh also
        self.random_projection()

    def apply_dot(self, data):
        projected = np.dot(data[:, self.selected_comp], self.projection[self.selected_comp, :])
        return projected
    
    def get_plotting_data(self):

        visible_unit_indices = self.controller.get_visible_unit_indices()
        spike_indices = mask = np.flatnonzero(np.isin(self.pc_unit_index, visible_unit_indices))
        projected = self.apply_dot(self.data[spike_indices, :])
        scatter_x = projected[:, 0]
        scatter_y = projected[:, 1]


        mask = np.isin(self.random_spikes_indices, self.controller.get_indices_spike_selected())
        data_sel = self.data[mask, :]
        projected_select = self.apply_dot(data_sel)
        selected_scatter_x = projected_select[:, 0]
        selected_scatter_y = projected_select[:, 1]

        return scatter_x, scatter_y, spike_indices, selected_scatter_x, selected_scatter_y


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
        spike_colors = self.controller.get_spike_colors(self.pc_unit_index)
        self.spike_qtcolors = np.array([pg.mkBrush(c) for c in spike_colors])
        
    def _qt_refresh(self):
        import pyqtgraph as pg

        # update visible channel
        n_pc_per_chan = self.pc_data.shape[1]
        n = min(self.settings['num_pc_per_channel'], n_pc_per_chan)
        self.selected_comp[:] = False
        for i in range(n):
            self.selected_comp[self.controller.visible_channel_inds*n_pc_per_chan+i] = True

        #ndscatter
        # TODO sam: I have the feeling taht it is a bit slow
        self.scatter.clear()
        scatter_x, scatter_y, spike_indices, selected_scatter_x, selected_scatter_y = self.get_plotting_data()
        scatter_colors = self.spike_qtcolors[spike_indices].tolist()
        self.scatter.setData(x=scatter_x, y=scatter_y, brush=scatter_colors, pen=pg.mkPen(None))
        self.scatter_select.setData(selected_scatter_x, selected_scatter_y)


        # TODO sam : kepp the old implementation in mind
        # for unit_index, unit_id in enumerate(self.controller.unit_ids):
        #     if not self.controller.unit_visible_dict[unit_id]:
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
        else:
            self.timer_tour.stop()
    
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


    # TODO alessio : lasso
    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from .utils_panel import _bg_color
        from bokeh.models import ColumnDataSource, Range1d, HoverTool, LinearColorMapper
        from bokeh.events import MouseWheel

        self.scatter_fig = bpl.figure(
            sizing_mode="stretch_both",
            tools="",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.scatter_fig.toolbar.logo = None
        self.scatter_fig.grid.visible = False
        self.scatter_fig.xgrid.grid_line_color = None
        self.scatter_fig.ygrid.grid_line_color = None
        
        # TODO alessio : remove the bokeh mousewheel zoom and keep only this one
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

    def _panel_refresh(self):

        scatter_x, scatter_y, spike_indices, selected_scatter_x, selected_scatter_y = self.get_plotting_data()

        # format rgba
        spike_colors = self.controller.get_spike_colors(self.pc_unit_index[spike_indices])


        self.scatter_source.data = {
            "x": scatter_x,
            "y": scatter_y,
            "color": spike_colors,
        }
        self.scatter_select_source.data = {
            "x": selected_scatter_x,
            "y": selected_scatter_y,
        }

        self.scatter_fig.x_range.start = -self.limit
        self.scatter_fig.x_range.end = self.limit
        self.scatter_fig.y_range.start = -self.limit
        self.scatter_fig.y_range.end = self.limit


    def _panel_gain_zoom(self, event):
        factor = 1.3 if event.delta > 0 else 1 / 1.3
        self.limit /= factor
        self.scatter_fig.x_range.start = -self.limit
        self.scatter_fig.x_range.end = self.limit
        self.scatter_fig.y_range.start = -self.limit
        self.scatter_fig.y_range.end = self.limit

        # self.refresh()

    def _panel_next_face(self, event):
        self.next_face()

    def _panel_random_projection(self, event):
        self.random_projection()

    def _panel_start_stop_tour(self, event):
        import panel as pn
        if event.new:
            self.tour_step = 0
            self.tour_timer = pn.state.add_periodic_callback(self.new_tour_step, period=self.settings['refresh_interval'])
        else:
            if self.tour_timer is not None:
                self.tour_timer.stop()
                self.tour_timer = None





def inside_poly(data, vertices):
    return mpl_path(vertices).contains_points(data)


NDScatterView._gui_help_txt = """N-dimensional scatter for the principal components
Projects (num_chan x num_pc) into 2 dim.
Button randomtour runs dynamic "tour" of the pcs
mouse wheel : zoom
left click: draw a lasso for spike selection
settings controls : num_pc_per_channel displayed
"""
