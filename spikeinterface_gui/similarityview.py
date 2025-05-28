import numpy as np
import matplotlib.cm
import matplotlib.colors

from .view_base import ViewBase




class SimilarityView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _depend_on = ["template_similarity"]
    _settings = [
            {'name': 'method', 'type': 'list', 'limits' : ['l1', 'l2', 'cosine'] },
            {'name': 'colormap', 'type': 'list', 'limits' : ['viridis', 'jet', 'gray', 'hot', ] },
            {'name': 'show_all', 'type': 'bool', 'value' : True },
        ]
    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        self.similarity = self.controller.get_similarity(method=None)

    def get_similarity_data(self):
        unit_ids = self.controller.unit_ids

        if self.similarity is None:
            return None, None

        if self.settings["show_all"]:
            visible_mask = np.ones(len(unit_ids), dtype="bool")
            s = self.similarity
        else:
            visible_mask = self.controller.get_units_visibility_mask()
            s = self.similarity[visible_mask, :][:, visible_mask]

        if not np.any(visible_mask):
            return None, None

        return s, visible_mask

    def select_unit_pair_on_click(self, x, y, reset=True):
        unit_ids = self.controller.unit_ids

        if self.settings['show_all']:
            visible_ids = unit_ids
        else:
            visible_ids = self.get_visible_unit_ids()
        
        n = len(visible_ids)
        
        inside = (0 <= x  <= n) and (0 <= y  <= n)

        if not inside:
            return
        
        unit_id0 = unit_ids[int(np.floor(x))]
        unit_id1 = unit_ids[int(np.floor(y))]
        
        if reset:
            self.controller.set_all_unit_visibility_off()
        self.controller.set_unit_visibility(unit_id0, True)
        self.controller.set_unit_visibility(unit_id1, True)

        self.notify_unit_visibility_changed()
        self.refresh()


    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingClickToPositionWithCtrl

        self.layout = QT.QVBoxLayout()
        
        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
        
        self.viewBox = ViewBoxHandlingClickToPositionWithCtrl()
        self.viewBox.clicked.connect(self._qt_select_pair)
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
        self.on_settings_changed()#this do refresh

    def _on_settings_changed(self):
        
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

    def _compute(self):
        self.similarity = self.controller.compute_similarity(method=self.settings['method'])

    def _qt_refresh(self):
        import pyqtgraph as pg
        
        unit_ids = self.controller.unit_ids
        
        if self.similarity is None:
            self.image.hide()
            return 
                
        similarity, visible_mask = self.get_similarity_data()
        
        if not np.any(visible_mask):
            self.image.hide()
            return
        
        _max = np.max(self.similarity)
        self.image.setImage(similarity, lut=self.lut, levels=[0, _max])
        self.image.show()
        self.plot.setXRange(0, similarity.shape[0])
        self.plot.setYRange(0, similarity.shape[1])

        pos = 0

        for item in self._text_items:
            self.plot.removeItem(item)
        
        if np.sum(visible_mask) < 10:
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


    
    def _qt_select_pair(self, x, y, reset):
        
        self.select_unit_pair_on_click(x, y, reset=reset)


    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from .utils_panel import _bg_color
        from bokeh.models import ColumnDataSource, LinearColorMapper
        from bokeh.events import Tap


        # Create Bokeh figure
        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset,wheel_zoom,tap",
            title="Similarity Matrix",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.figure.toolbar.logo = None

        # Create initial color mapper
        N = 512
        cmap = matplotlib.colormaps[self.settings['colormap']]
        self.color_mapper = LinearColorMapper(
            palette=[matplotlib.colors.rgb2hex(cmap(i)[:3]) for i in np.linspace(0, 1, N)], low=0, high=1
        )

        self.image_source = ColumnDataSource({"image": [np.zeros((1, 1))], "dw": [1], "dh": [1]})
        self.image_glyph = self.figure.image(
            image="image", x=0, y=0, dw="dw", dh="dh", color_mapper=self.color_mapper, source=self.image_source
        )

        self.text_source = ColumnDataSource({"x": [], "y": [], "text": []})
        self.text_glyphs = self.figure.text(
            x="x",
            y="y",
            text="text",
            source=self.text_source,
            text_color="white",
            text_align="center",
            text_baseline="middle",
        )

        self.figure.on_event(Tap, self._panel_on_tap)

        self.layout = pn.Column(
            self.figure,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both"
        )

    def _panel_refresh(self):
        similarity, visible_mask = self.get_similarity_data()
        

        if similarity is None:
            return

        self.color_mapper.low = 0
        self.color_mapper.high = np.max(self.similarity)

        self.image_source.data.update({"image": [similarity], "dw": [similarity.shape[1]], "dh": [similarity.shape[0]]})

        # Update text labels
        x_positions = []
        y_positions = []
        texts = []
        pos = 0

        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not visible_mask[unit_index]:
                continue
            # Add labels on both axes
            x_positions.extend([pos + 0.5, 0])
            y_positions.extend([0, pos + 0.5])
            texts.extend([str(unit_id), str(unit_id)])
            pos += 1

        self.text_source.data.update({"x": x_positions, "y": y_positions, "text": texts})

        # Update plot ranges
        self.figure.x_range.start = 0
        self.figure.x_range.end = similarity.shape[1]
        self.figure.y_range.start = 0
        self.figure.y_range.end = similarity.shape[0]

    def _panel_on_tap(self, event):
        if event.x is None or event.y is None:
            return

        self.select_unit_pair_on_click(event.x, event.y, reset=True)



SimilarityView._gui_help_txt = """
## Similarity View

This view displays the template similarity matrix between units.

### Controls
- **left click** : select a pair of units to show in the unit view.
"""
