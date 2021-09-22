from .myqt import QT
import pyqtgraph as pg

import numpy as np
import matplotlib.cm
import matplotlib.colors

from .base import WidgetBase
from .tools import ParamDialog


class MyViewBox(pg.ViewBox):
    clicked = QT.pyqtSignal(float, float)
    doubleclicked = QT.pyqtSignal()
    def mouseClickEvent(self, ev):
        pos = self.mapToView(ev.pos())
        x, y = pos.x(), pos.y()
        self.clicked.emit(x, y)
        ev.accept()
        
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass



class SimilarityView(WidgetBase):
    _params = [
      {'name': 'method', 'type': 'list', 'values' : ['cosine_similarity',] },
      {'name': 'colormap', 'type': 'list', 'values' : ['viridis', 'jet', 'gray', 'hot', ] },
      {'name': 'show_all', 'type': 'bool', 'value' : True },
                      
        ]
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        #~ h = QT.QHBoxLayout()
        #~ self.layout.addLayout(h)
        #~ h.addWidget(QT.QLabel('<b>Similarity</b>') )

        #~ but = QT.QPushButton('settings')
        #~ but.clicked.connect(self.open_settings)
        #~ h.addWidget(but)
        
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.initialize_plot()
        
        self.on_params_changed()#this do refresh

    def on_params_changed(self):
        N = 512
        cmap_name = self.params['colormap']
        cmap = matplotlib.cm.get_cmap(cmap_name , N)
        
        lut = []
        for i in range(N):
            r,g,b,_ =  matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r*255,g*255,b*255])
        self.lut = np.array(lut, dtype='uint8')
        
        self.refresh()
    
    def initialize_plot(self):
        self.viewBox = MyViewBox()
        self.viewBox.clicked.connect(self.select_pair)
        self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.disableAutoRange()
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        
        self._text_items = []


    def on_spike_selection_changed(self):
        pass
    
    def on_spike_label_changed(self):
        self.refresh()
    
    def on_colors_changed(self):
        pass
    
    def on_unit_visibility_changed(self):
        self.refresh()

    def refresh(self):
        
        unit_ids = self.controller.unit_ids
        
        similarity = self.controller.get_similarity(method=self.params['method'])
        
        #~ if self.similarity is None:
            #~ self.image.hide()
            #~ return
        
        _max = np.max(similarity)
        
        if self.params['show_all']:
            visible_mask = np.ones(len(unit_ids), dtype='bool')
            s = similarity
        else:
            visible_mask = np.array([self.controller.unit_visible_dict[u] for u in self.controller.unit_ids], dtype='bool')
            s = similarity[visible_mask, :][:, visible_mask]
        
        
        if not np.any(visible_mask):
            self.image.hide()
            return
        
        self.image.setImage(s, lut=self.lut, levels=[0, _max])
        self.image.show()
        self.plot.setXRange(0, s.shape[0])
        self.plot.setYRange(0, s.shape[1])

        pos = 0

        for item in self._text_items:
            self.plot.removeItem(item)
        
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not visible_mask[unit_index]:
                continue
            for i in range(2):
                item = pg.TextItem(text=f'{unit_id}', color='#FFFFFF', anchor=(0.5, 0.5), border=None)
                self.plot.addItem(item)
                if i==0:
                    item.setPos(pos + 0.5, 0)
                else:
                    item.setPos(0, pos + 0.5)
                self._text_items.append(item)
            pos += 1
    
    def select_pair(self, x, y):
        unit_ids = self.controller.unit_ids
        
        if self.params['show_all']:
            visible_ids = unit_ids
        else:
            visible_ids = [u for u, v in self.controller.unit_visible_dict.items() if v]
        
        n = len(visible_ids)
        
        inside = (0 <= x  <= n) and (0 <= y  <= n)

        if not inside:
            return
        
        
        
        unti_id0 = unit_ids[int(np.floor(x))]
        unti_id1 = unit_ids[int(np.floor(y))]
        
        for unit_id in unit_ids:
            self.controller.unit_visible_dict[unit_id] = unit_id in (unti_id0, unti_id1)
        self.unit_visibility_changed.emit()
        
        self.refresh()

