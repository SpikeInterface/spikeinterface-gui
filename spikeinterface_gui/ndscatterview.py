"""
This should be rewritte with vispy but I don't have time now...
"""
from .myqt import QT
import pyqtgraph as pg

from matplotlib.path import Path as mpl_path

import numpy as np
import pandas as pd

import itertools

from .base import WidgetBase
from .tools import ParamDialog

#~ from ..tools import median_mad, get_neighborhood


class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    gain_zoom = QT.pyqtSignal(float)
    #~ xsize_zoom = QT.pyqtSignal(float)
    #~ lasso_started = QT.pyqtSignal()
    lasso_drawing = QT.pyqtSignal(object)
    lasso_finished = QT.pyqtSignal(object)
    
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.disableAutoRange()
        self.drag_points = []
        
    def mouseClickEvent(self, ev):
        ev.accept()
        
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
        
    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() == QT.Qt.ControlModifier:
            z = 10 if ev.delta()>0 else 1/10.
        else:
            z = 1.3 if ev.delta()>0 else 1/1.3
        self.gain_zoom.emit(z)
        ev.accept()
        
    def mouseDragEvent(self, ev):
        ev.accept()
        if ev.button()!=1: return
        
        if ev.isStart():
            self.drag_points = []
        
        pos = self.mapToView(ev.pos())
        self.drag_points.append([pos.x(), pos.y()])
        
        if ev.isFinish():
            self.lasso_finished.emit(self.drag_points)
        else:
            self.lasso_drawing.emit(self.drag_points)
        

class NDScatterView(WidgetBase):
    """
    This try to mimic `RGGobi viewer package <http://www.ggobi.org/rggobi/>`_.
    """
    _params = [
           {'name': 'refresh_interval', 'type': 'float', 'value': 100 },
           {'name': 'nb_step', 'type': 'int', 'value':  10, 'limits' : [5, 100] },
           {'name': 'max_visible_by_cluster', 'type': 'int', 'value':  1000, 'limits' : [10, 10000], 'step':50 },
           {'name': 'auto_select_component', 'type': 'bool', 'value': True},
           {'name': 'radius_um', 'type': 'float', 'value': 300.},
        ]
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        assert self.controller.handle_principal_components()
        
        self.pc_unit_index, self.pc_data = self.controller.get_all_pcs()
        self.data = self.pc_data.swapaxes(1,2).reshape(self.pc_data.shape[0], -1)
        
        if self.data.shape[1] == 1:
            # corner case one PC and one channel only
            data = np.zeros((feat.shape[0], 2), dtype=self.data.dtype)
            data[:, 0] = self.data[:, 0]
            data[:, 0] = self.data[:, 0]
            self.data = data

        
        
        self.layout = QT.QHBoxLayout()
        self.setLayout(self.layout)
        
        self.create_toolbar()
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)

        self.toolbar.addStretch()
        self.graphicsview2 = pg.GraphicsView()
        self.toolbar.addWidget(self.graphicsview2)

        #~ _params = [{'name': 'refresh_interval', 'type': 'float', 'value': 100 },
                           #~ {'name': 'nb_step', 'type': 'int', 'value':  10, 'limits' : [5, 100] },
                           #~ {'name': 'max_visible_by_cluster', 'type': 'int', 'value':  1000, 'limits' : [10, 10000], 'step':50 },
                           #~ ]
        #~ self.params = pg.parametertree.Parameter.create( name='Global options', type='group', children = _params)
        #~ self.tree_params = pg.parametertree.ParameterTree(parent  = self)
        #~ self.tree_params.header().hide()
        #~ self.tree_params.setParameters(self.params, showTop=True)
        #~ self.tree_params.setWindowTitle(u'Options for NDScatter')
        #~ self.tree_params.setWindowFlags(QT.Qt.Window)

        
        self.timer_tour = QT.QTimer(interval=100)
        self.timer_tour.timeout.connect(self.new_tour_step)
        
        #~ if self.data is not None:
        self.initialize()
        self.refresh()
    
    def create_toolbar(self):
        
        tb = self.toolbar = QT.QVBoxLayout()
        self.layout.addLayout(tb)
        but = QT.QPushButton('next face')
        tb.addWidget(but)
        but.clicked.connect(self.next_face)
        but = QT.QPushButton('Random')
        tb.addWidget(but)
        but.clicked.connect(self.random_projection)
        but = QT.QPushButton('Random tour', checkable = True)
        tb.addWidget(but)
        but.clicked.connect(self.start_stop_tour)
        but = QT.QPushButton('settings')
        but.clicked.connect(self.open_settings)
        tb.addWidget(but)
        #~ but = QT.QPushButton('random decimate', icon=QT.QIcon.fromTheme("roll"))
        #~ but.clicked.connect(self.by_cluster_random_decimate)
        #~ tb.addWidget(but)
        #~ but = QT.QPushButton('select component')
        #~ but.clicked.connect(self.open_select_component)
        #~ tb.addWidget(but)
        
    #~ def open_select_component(self):
        
        #~ ndim = self.data.shape[1]
        #~ params = [{'name' : 'comp {}'.format(i), 'type':'bool', 'value' : self.selected_comp[i]} for i in range(ndim)]
        
        #~ dialog = ParamDialog(params, title = 'Select component')
        #~ if dialog.exec_():
            #~ p = dialog.get()
            #~ for i in range(ndim):
                #~ self.selected_comp[i] = p['comp {}'.format(i)]
            #~ self.refresh()
    
    # this handle data with propties so model change shoudl not affect so much teh code
    #~ @property
    #~ def data(self):
        
        #~ feat = self.controller.some_features
        #~ data = ensure_2d(feat)
        #~ return data
    
    #~ def data_by_label(self, k):
        #~ if len(self.point_visible) != self.data.shape[0]:
            #~ self.point_visible = np.zeros(self.data.shape[0], dtype=bool)
            #~ self.by_cluster_random_decimate()
        
        #~ if k=='sel':
            #~ data = self.data[self.controller.spike_selection[self.controller.some_peaks_index]]
        #~ elif k==labelcodes.LABEL_NOISE:
            #~ feat_noise = self.controller.some_noise_features
            #~ data = ensure_2d(feat_noise)
        #~ else:
            #~ data = self.data[(self.controller.spike_label[self.controller.some_peaks_index]==k) & self.point_visible]
        
        #~ return data
    
    #~ def by_cluster_random_decimate(self, clicked=None, refresh=True):
        #~ m = self.params['max_visible_by_cluster']
        #~ for k in self.controller.cluster_labels:
            #~ mask = self.controller.spike_label[self.controller.some_peaks_index]==k
            #~ if self.controller.cluster_count[k]>m:
                #~ self.point_visible[mask] = False
                #~ visible, = np.nonzero(mask)
                #~ if visible.size>0:
                    #~ visible = np.random.choice(visible, size=m)
                    #~ self.point_visible[visible] = True
            #~ else:
                #~ self.point_visible[mask] = True
        
        #~ if refresh:
            #~ self.refresh()
        
    #~ def get_color(self, k):
        #~ color = self.controller.qcolors.get(k, QT.QColor( 'white'))
        #~ return color
    
    #~ def is_cluster_visible(self, k):
        #~ return self.controller.cluster_visible[k]

    
    def initialize(self):
        #~ if self.data is None:
        #~ if self.controller.some_features is None:
            #~ return
        self.viewBox = MyViewBox()
        self.viewBox.gain_zoom.connect(self.gain_zoom)
        #~ self.viewBox.lasso_started.connect(self.on_lasso_started)
        self.viewBox.lasso_drawing.connect(self.on_lasso_drawing)
        self.viewBox.lasso_finished.connect(self.on_lasso_finished)
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        self.scatter = pg.ScatterPlotItem(size=3, pxMode = True)
        self.plot.addItem(self.scatter)
        self.scatter.sigClicked.connect(self.on_scatter_clicked)
        
        
        brush = QT.QColor( 'magenta')
        brush.setAlpha(180)
        self.scatter_select = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=brush, size=11, pxMode = True)
        self.plot.addItem(self.scatter_select)
        self.scatter_select.setZValue(1000)
        
        
        #~ color = self.controller.qcolors.get(labelcodes.LABEL_NOISE)
        #~ self.scatter_noise = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=color, size=3, pxMode = True)
        #~ self.plot.addItem(self.scatter_noise)
        
        self.lasso = pg.PlotCurveItem(pen='#7FFF00')
        self.plot.addItem(self.lasso)
        
        #estimate limts
        #  VERY SLOW
        #~ med, mad = median_mad(self.data)
        #~ m = 4.*np.max(mad)
        #~ self.limit = m
        #~ self.plot.setXRange(-m, m)
        #~ self.plot.setYRange(-m, m)
        
        #estimate limts
        data = self.data.flatten()
        if data.size > 5000:
            data = data.take(np.random.choice(data.size, 5000, replace=False))
        min_ = np.min(data)
        max_ = np.max(data)
        m = max(np.abs(min_), np.abs(max_)) * 2.5
        self.limit = m
        
        ndim = self.data.shape[1]
        self.selected_comp = np.ones( (ndim), dtype='bool')
        self.projection = np.zeros( (ndim, 2))
        self.projection[0,0] = 1.
        self.projection[1,1] = 1.
        
        self.point_visible = np.zeros(self.data.shape[0], dtype=bool)
        #~ self.by_cluster_random_decimate(refresh=False)
        
        self.plot2 = pg.PlotItem(viewBox=MyViewBox(lockAspect=True))
        self.graphicsview2.setCentralItem(self.plot2)
        self.plot2.hideButtons()
        angles = np.arange(0,360, .1)
        self.circle = pg.PlotCurveItem(x=np.cos(angles), y=np.sin(angles), pen=(255,255,255))
        self.plot2.addItem(self.circle)
        self.direction_lines = pg.PlotCurveItem(x=[], y=[], pen=(255,255,255))
        self.direction_data = np.zeros( (ndim*2, 2))
        self.plot2.addItem(self.direction_lines)
        self.plot2.setXRange(-1, 1)
        self.plot2.setYRange(-1, 1)
        self.proj_labels = []
        for i in range(ndim):
            text = 'PC{}'.format(i)
            label = pg.TextItem(text, color=(1,1,1), anchor=(0.5, 0.5), border=None, fill=pg.mkColor((128,128,128, 180)))
            self.proj_labels.append(label)
            self.plot2.addItem(label)
        
        self.graphicsview2.setMaximumSize(200, 200)
        
        #~ self.hyper_faces = list(itertools.product(range(ndim), range(ndim)))
        self.hyper_faces = list(itertools.permutations(range(ndim), 2))
        self.n_face = -1
    
    def next_face(self):
        self.n_face += 1
        self.n_face = self.n_face%len(self.hyper_faces)
        ndim = self.data.shape[1]
        self.projection = np.zeros( (ndim, 2))
        i, j = self.hyper_faces[self.n_face]
        self.projection[i,0] = 1.
        self.projection[j,1] = 1.
        if self.timer_tour.isActive():
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
        if self.timer_tour.isActive():
            self.tour_step == 0
        self.refresh()
    
    def apply_dot(self, data):
        #~ print(data.shape, self.projection.shape)
        projected = np.dot(data[:, self.selected_comp ], self.projection[self.selected_comp, :])
        return projected
    
    def refresh(self):
        #~ if self.data is None:
        #~ if self.controller.some_features is None:
            #~ if hasattr(self, 'plot'):
                #~ self.plot.clear()
            #~ return

        #~ if not hasattr(self, 'viewBox'):
            #~ self.initialize()
        
        #~ if self.data.shape[1] != self.projection.shape[0]:
            #~ self.initialize()
        
        # update visible channel
        n_pc_per_chan = self.pc_data.shape[1]
        self.selected_comp[:] = False
        for i in range(n_pc_per_chan):
            self.selected_comp[self.controller.visible_channel_inds*n_pc_per_chan+i] = True
        
        
        #ndscatter
        self.scatter.clear()

        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                continue
            #~ data = self.data_by_label(k)
            # TODO make slice!!!!!!
            mask = self.pc_unit_index == unit_index
            data = self.data[mask, :]
            #~ projected = np.dot(data, self.projection )
            projected = self.apply_dot(data)
            #~ color = self.get_color(k)
            color = self.controller.qcolors[unit_id]
            self.scatter.addPoints(x=projected[:,0], y=projected[:,1],  pen=pg.mkPen(None), brush=color)
        
        #selection scatter
        # TODO : selection
        #~ data_sel = self.data_by_label('sel')
        #~ projected = np.dot(data_sel, self.projection )
        #~ projected = self.apply_dot(data_sel)
        #~ self.scatter_select.setData(projected[:,0], projected[:,1])
        
        #noise
        #~ if self.is_cluster_visible(labelcodes.LABEL_NOISE):
            #~ data_noise = self.data_by_label(labelcodes.LABEL_NOISE)
            #~ if data_noise is not None:
                #~ projected = self.apply_dot(data_noise)
                #~ self.scatter_noise.setData(projected[:,0], projected[:,1])
                #~ self.scatter_noise.show()
        #~ else:
            #~ self.scatter_noise.hide()
        
        #projection axes
        proj = self.projection.copy()
        proj[~self.selected_comp, :] = 0
        self.direction_data[::, :] =0
        #~ self.direction_data[::2, :] = self.projection
        self.direction_data[::2, :] = proj
        self.direction_lines.setData(self.direction_data[:,0], self.direction_data[:,1])
        
        for i, label in enumerate(self.proj_labels):
            if self.selected_comp[i]:
                label.setPos(self.projection[i,0], self.projection[i,1])
                label.show()
            else:
                label.hide()
        
        self.graphicsview.repaint()
            
    
    def start_stop_tour(self, checked):
        if checked:
            self.tour_step = 0
            self.timer_tour.setInterval(self.params['refresh_interval'])
            self.timer_tour.start()
        else:
            self.timer_tour.stop()
    
    def new_tour_step(self):
        #~ if self.data is None:
        #~ if self.controller.some_features is None:
            #~ return
        nb_step = self.params['nb_step']
        ndim = self.data.shape[1]
        
        if self.tour_step == 0:
            self.tour_steps = np.empty( (ndim , 2 ,  nb_step))
            arrival = self.get_one_random_projection()
            for i in range(ndim):
                for j in range(2):
                    self.tour_steps[i,j , : ] = np.linspace(self.projection[i,j] , arrival[i,j] , nb_step)
            m = np.sqrt(np.sum(self.tour_steps**2, axis=0))
            m = m[np.newaxis, : ,  :]
            self.tour_steps /= m
        
        self.projection = self.tour_steps[:,:,self.tour_step]
        
        self.tour_step+=1
        if self.tour_step>=nb_step:
            self.tour_step = 0
            
        self.refresh()

    def gain_zoom(self, factor):
        self.limit /= factor
        l = float(self.limit)
        self.plot.setXRange(-l, l)
        self.plot.setYRange(-l, l)
    
    def on_scatter_clicked(self,plots, points):
        self.controller.spike_selection[:] = False
        if len(points)==1:
            #~ projected = np.dot(self.data, self.projection )
            projected = self.apply_dot(self.data)
            pos = points[0].pos()
            pos = [pos.x(), pos.y()]
            ind = np.argmin(np.sum((projected-pos)**2, axis=1))
            self.controller.spike_selection[self.controller.some_peaks_index[ind]] = True
            
        self.refresh()
        self.spike_selection_changed.emit()
    
    def on_lasso_drawing(self, points):
        points = np.array(points)
        self.lasso.setData(points[:, 0], points[:, 1])
    
    def on_lasso_finished(self, points):
        self.lasso.setData([], [])
        vertices = np.array(points)
        
        visible = self.controller.spike['visible']
        selected = self.controller.spike['selected']
        
        self.controller.spike['selected'][:] = False
        
        #~ ('visible', 'bool'), ('selected', 'bool')]
        
        self.controller.spike_selection[:] = False
        #~ projected = np.dot(self.data, self.projection )
        projected = self.apply_dot(self.data)
        inside = inside_poly(projected, vertices)
        visibles = self.controller.spike_visible[self.controller.some_peaks_index]
        self.controller.spike_selection[self.controller.some_peaks_index[inside&visibles]] = True
        self.refresh()
        
        self.spike_selection_changed.emit()
    
    def auto_select_component(self):
        #~ if self.data is None:
        if self.controller.some_features is None:
            return
        
        # take all component that corespon to a channel max and neighborhood
        neighborhood = get_neighborhood(self.controller.geometry, self.params['radius_um'])
        
        ndim = self.data.shape[1]
        self.selected_comp = np.zeros( (ndim), dtype='bool')
        for k, v in self.controller.cluster_visible.items():
            if not v: continue
            c = self.controller.get_extremum_channel(k)
            if c is not None:
                chan_mask = neighborhood[c,:]
                #~ print('c', c, chan_mask)
                feat_mask = np.sum(self.controller.channel_to_features[chan_mask, :], axis=0).astype('bool')
                #~ print(feat_mask)
                
                self.selected_comp |= feat_mask
        
        #~ print('auto_select_component', self.selected_comp)

    def on_spike_selection_changed(self):
        self.refresh()

    def on_unit_visibility_changed(self):
        self.refresh()
    
    def on_channel_visibility_changed(self):
        self.refresh()


def inside_poly(data, vertices):
    return mpl_path(vertices).contains_points(data)


