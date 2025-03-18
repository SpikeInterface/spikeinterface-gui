import numpy as np
import matplotlib.cm
import matplotlib.colors

from .view_base import ViewBase




class SimilarityView(ViewBase):
    _supported_backend = ['qt']
    _settings = [
            {'name': 'method', 'type': 'list', 'limits' : ['l1', 'l2', 'cosine'] },
            {'name': 'colormap', 'type': 'list', 'limits' : ['viridis', 'jet', 'gray', 'hot', ] },
            {'name': 'show_all', 'type': 'bool', 'value' : True },
        ]
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)


    def _make_layout_qt(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingClickToPositionWithCtrl

        self.layout = QT.QVBoxLayout()
        # self.setLayout(self.layout)
        
        #~ h = QT.QHBoxLayout()
        #~ self.layout.addLayout(h)
        #~ h.addWidget(QT.QLabel('<b>Similarity</b>') )

        #~ but = QT.QPushButton('settings')
        #~ but.clicked.connect(self.open_settings)
        #~ h.addWidget(but)
        
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.viewBox = ViewBoxHandlingClickToPositionWithCtrl()
        self.viewBox.clicked.connect(self.select_pair)
        # self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.disableAutoRange()
        
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        
        self._text_items = []

        
        self.similarity = self.controller.get_similarity(method=self.settings['method'])
        self.on_params_changed()#this do refresh

    def on_params_changed(self):
        
        # TODO : check if method have changed or not
        # self.similarity = None
        
        N = 512
        cmap_name = self.settings['colormap']
        cmap = matplotlib.colormaps[cmap_name].resampled(N)
        
        lut = []
        for i in range(N):
            r,g,b,_ =  matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r*255,g*255,b*255])
        self.lut = np.array(lut, dtype='uint8')
        
        
        self.refresh()

    # def on_similarity_method_changed(self):
    #     self.refresh()

    def compute(self):
        self.similarity = self.controller.compute_similarity(method=self.settings['method'])
        self.refresh()

    def _refresh_qt(self):
        import pyqtgraph as pg
        
        unit_ids = self.controller.unit_ids
        
        if self.similarity is None:
            self.image.hide()
            return 
        
        _max = np.max(self.similarity)
        
        if self.settings['show_all']:
            visible_mask = np.ones(len(unit_ids), dtype='bool')
            s = self.similarity
        else:
            visible_mask = np.array([self.controller.unit_visible_dict[u] for u in self.controller.unit_ids], dtype='bool')
            s = self.similarity[visible_mask, :][:, visible_mask]
        
        
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
    
    def select_pair(self, x, y, reset):
        unit_ids = self.controller.unit_ids
        
        if self.settings['show_all']:
            visible_ids = unit_ids
        else:
            visible_ids = [u for u, v in self.controller.unit_visible_dict.items() if v]
        
        n = len(visible_ids)
        
        inside = (0 <= x  <= n) and (0 <= y  <= n)

        if not inside:
            return
        
        
        
        unti_id0 = unit_ids[int(np.floor(x))]
        unti_id1 = unit_ids[int(np.floor(y))]
        
        if reset:
            for unit_id in unit_ids:
                self.controller.unit_visible_dict[unit_id] = False
        self.controller.unit_visible_dict[unti_id0] = True
        self.controller.unit_visible_dict[unti_id1] = True

        self.controller.update_visible_spikes()
        self.notify_unit_visibility_changed()
        
        self.refresh()
    

SimilarityView._gui_help_txt = """Similarity view
Check similarity between units with user-selectable metrics
Mouse click : make one pair of units visible.
Mouse click + CTRL: append pair to visible units.
"""
