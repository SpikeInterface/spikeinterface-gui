import numpy as np
from contextlib import nullcontext
import matplotlib.colors

from .view_base import ViewBase

from .traceview import MixinViewTrace, find_nearest_spike


class TraceMapView(ViewBase, MixinViewTrace):

    _supported_backend = ['qt', 'panel']
    _depend_on = ['recording']
    _settings = [
        {'name': 'auto_zoom_on_select', 'type': 'bool', 'value': True},
        {'name': 'spike_selection_xsize', 'type': 'float', 'value':  0.03, 'step' : 0.001},
        {'name': 'alpha', 'type': 'float', 'value' : 0.8, 'limits':(0, 1.), 'step':0.05},
        {'name': 'xsize_max', 'type': 'float', 'value': 4.0, 'step': 1.0, 'limits':(1.0, np.inf)},
        {'name': 'colormap', 'type': 'list', 'limits' : ['gray', 'bwr',  'PiYG', 'jet', 'hot', ]},
        {'name': 'reverse_colormap', 'type': 'bool', 'value': True},
        {'name': 'show_on_selected_units', 'type': 'bool', 'value': True},
    ]


    def __init__(self, controller=None, parent=None, backend="qt"):
        pos = controller.get_contact_location()
        self.channel_order = np.lexsort((-pos[:, 0], pos[:, 1], ))
        self.channel_order_reverse = np.argsort(self.channel_order, kind="stable")
        self.color_limit = None
        self.last_data_curves = None
        self.factor = None

        self.xsize = 0.5
        self._block_auto_refresh_and_notify = False
        self.trace_context = nullcontext

        ViewBase.__init__(self, controller=controller, parent=parent, backend=backend)
        MixinViewTrace.__init__(self)

        self.make_color_lut()

    def apply_gain_zoom(self, factor_ratio):
        if self.color_limit is None:
            return
        self.color_limit = self.color_limit * factor_ratio
        self.refresh()

    def auto_scale(self):
        if self.last_data_curves is not None:
            self.color_limit = np.max(np.abs(self.last_data_curves))
        self.refresh()

    def make_color_lut(self):
        N = 512
        cmap_name = self.settings['colormap']
        cmap = matplotlib.colormaps[cmap_name].resampled(N)
        lut = []
        for i in range(N):
            r,g,b,_ =  matplotlib.colors.ColorConverter().to_rgba(cmap(i))
            lut.append([r*255,g*255,b*255])
        self.lut = np.array(lut, dtype='uint8')
        if self.settings['reverse_colormap']:
            self.lut = self.lut[::-1]

    def get_visible_channel_inds(self):
        return self.channel_order

    ## Qt ##
    def _qt_make_layout(self, **kargs):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()
        
        self._qt_create_toolbars()
        
        
        # create graphic view and 2 scroll bar
        g = QT.QGridLayout()
        self.layout.addLayout(g)
        self.graphicsview = pg.GraphicsView()
        g.addWidget(self.graphicsview, 0,1)

        MixinViewTrace._qt_initialize_plot(self)
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        self.scatter = pg.ScatterPlotItem(size=10, pxMode = True)
        self.plot.addItem(self.scatter)

        self.layout.addWidget(self.bottom_toolbar)
        self._qt_change_segment(0)

    def _qt_on_settings_changed(self, do_refresh=True):

        self.spinbox_xsize.opts['bounds'] = [0.001, self.settings['xsize_max']]
        if self.xsize > self.settings['xsize_max']:
            self.spinbox_xsize.sigValueChanged.disconnect(self.on_xsize_changed)
            self.spinbox_xsize.setValue(self.settings['xsize_max'])
            self.xsize = self.settings['xsize_max']
            self.spinbox_xsize.sigValueChanged.connect(self.on_xsize_changed)
            self.notify_time_info_updated()

        self.make_color_lut()

        if do_refresh:
            self.refresh()

    def _qt_on_spike_selection_changed(self):
        self._qt_seek_with_selected_spike()

    def _qt_refresh(self):
        self._qt_remove_event_line()
        t, _ = self.controller.get_time()
        self._qt_seek(t)

    def _qt_seek(self, t):
        from .myqt import QT
        import pyqtgraph as pg

        if self.qt_widget.sender() is not self.timeseeker:
            self.timeseeker.seek(t, emit=False)

        self.controller.set_time(time=t)
        xsize = self.xsize
        t1, t2 = t - xsize / 3. , t + xsize * 2/3.

        sr = self.controller.sampling_frequency

        self.scroll_time.valueChanged.disconnect(self._qt_on_scroll_time)
        value = self.controller.time_to_sample_index(t)
        self.scroll_time.setValue(value)
        self.scroll_time.setPageStep(int(sr*xsize))
        self.scroll_time.valueChanged.connect(self._qt_on_scroll_time)

        segment_index = self.controller.get_time()[1]
        times_chunk, data_curves, scatter_x, scatter_y, scatter_colors = \
            self.get_data_in_chunk(t1, t2, segment_index)
        data_curves = data_curves.T

        if times_chunk.size == 0:
            self.image.hide()
            self.scatter.clear()
            return

        if self.color_limit is None:
            self.color_limit = np.max(np.abs(data_curves))

        num_chans = data_curves.shape[1]

        self.image.setImage(data_curves, lut=self.lut, levels=[-self.color_limit, self.color_limit])
        self.image.setRect(QT.QRectF(times_chunk[0], 0, times_chunk[-1] - times_chunk[0], num_chans))
        self.image.show()

        # self.scatter.clear()
        self.scatter.setData(x=scatter_x, y=scatter_y, brush=scatter_colors)

        self.plot.setXRange(t1, t2, padding=0.0)
        self.plot.setYRange(0, num_chans, padding=0.0)

    def _qt_on_time_info_updated(self):
        # Update segment and time slider range
        time, segment_index = self.controller.get_time()
        # Block auto refresh to avoid recursive calls
        self._block_auto_refresh_and_notify = True
        self._qt_change_segment(segment_index)
        self.timeseeker.seek(time)
        self.refresh()
        self._block_auto_refresh_and_notify = False

    def _qt_on_use_times_updated(self):
        # Block auto refresh to avoid recursive calls
        self._block_auto_refresh_and_notify = True
        t_start, t_stop = self.controller.get_t_start_t_stop()
        self.timeseeker.set_start_stop(t_start, t_stop)
        self.timeseeker.seek(self.controller.get_time()[0])
        self.refresh()
        self._block_auto_refresh_and_notify = False

    ## Panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from .utils_panel import _bg_color
        from bokeh.models import ColumnDataSource, LinearColorMapper, Range1d
        from bokeh.events import MouseWheel, DoubleTap


        # Create figure
        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="box_zoom,pan,reset",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.figure.toolbar.logo = None

        self.figure.on_event(MouseWheel, self._panel_gain_zoom)
        self.figure.on_event(DoubleTap, self._panel_on_double_tap)

        # Add selection line
        self.selection_line = self.figure.line(
            x=[], y=[], line_color="purple", line_width=2, line_dash="dashed", visible=False
        )


        # Add grid
        self.figure.grid.visible = False
        self.figure.xgrid.grid_line_color = None
        self.figure.ygrid.grid_line_color = None

        # Configure axes
        self.figure.xaxis.axis_label = "Time (s)"
        self.figure.xaxis.axis_label_text_color = "white"
        self.figure.xaxis.axis_line_color = "white"
        self.figure.xaxis.major_label_text_color = "white"
        self.figure.xaxis.major_tick_line_color = "white"
        self.figure.yaxis.visible = False
        self.figure.x_range = Range1d(start=0, end=0.5)
        self.figure.y_range = Range1d(start=0, end=1)


        # Add data sources
        self.image_source = ColumnDataSource({"image": [], "x": [], "y": [], "dw": [], "dh": []})

        self.spike_source = ColumnDataSource({"x": [], "y": [], "color": []})

        # Create color mapper
        self.color_mapper = LinearColorMapper(palette="Greys256", low=-1, high=1)

        # Plot heatmap
        self.image_renderer = self.figure.image(
            image="image", x="x", y="y", dw="dw", dh="dh", color_mapper=self.color_mapper, source=self.image_source
        )

        # Plot spikes
        self.spike_renderer = self.figure.scatter(
            x="x", y="y", size=10, fill_color="color", fill_alpha=self.settings['alpha'], source=self.spike_source
        )

        # # Add hover tool for spikes
        # hover_spikes = HoverTool(renderers=[self.spike_renderer], tooltips=[("Unit", "@unit_id")])
        # self.figure.add_tools(hover_spikes)
        self._panel_create_toolbars()

        self.layout = pn.Column(
            pn.Column(  # Main content area
                self.toolbar,
                self.figure,
                self.bottom_toolbar,
                styles={"flex": "1"},
                sizing_mode="stretch_both"
            ),
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both"
        )

    def _panel_refresh(self):
        t, segment_index = self.controller.get_time()
        xsize = self.xsize
        t1, t2 = t - xsize / 3.0, t + xsize * 2 / 3.0

        if self.last_data_curves is None:
            auto_scale = True
        else:
            auto_scale = False

        times_chunk, data_curves, scatter_x, scatter_y, scatter_colors = \
            self.get_data_in_chunk(t1, t2, segment_index)
        data_curves = data_curves.T

        if self.color_limit is None:
            self.color_limit = np.max(np.abs(data_curves))

        self.image_source.data.update({
            "image": [data_curves.T],
            "x": [times_chunk[0]],
            "y": [0],
            "dw": [times_chunk[-1] - times_chunk[0]],
            "dh": [data_curves.shape[1]]
        })

        self.spike_source.data.update({
            "x": scatter_x,
            "y": scatter_y,
            "color": scatter_colors,
        })

        if auto_scale:
            self.color_limit = np.max(np.abs(self.last_data_curves))
            self.color_mapper.high = self.color_limit
            self.color_mapper.low = -self.color_limit

        self.figure.x_range.start = t1
        self.figure.x_range.end = t2
        self.figure.y_range.end = data_curves.shape[1]

    def _panel_on_settings_changed(self):
        self.make_color_lut()
        self.refresh()

    def _panel_on_spike_selection_changed(self):
        self._panel_seek_with_selected_spike()

    def _panel_gain_zoom(self, event):
        factor_ratio = 1.3 if event.delta > 0 else 1 / 1.3
        self.color_mapper.high = self.color_mapper.high * factor_ratio
        self.color_mapper.low = -self.color_mapper.high

    def _panel_auto_scale(self, event):
        if self.last_data_curves is not None:
            self.color_limit = np.max(np.abs(self.last_data_curves))
            self.color_mapper.high = self.color_limit
            self.color_mapper.low = -self.color_limit

    def _panel_on_time_info_updated(self):
        # Update segment and time slider range
        time, segment_index = self.controller.get_time()

        self._block_auto_refresh_and_notify = True
        self._panel_change_segment(segment_index)

        # Update time slider value
        self.time_slider.value = time

        self._block_auto_refresh_and_notify = False
        # we don't need a refresh in panel because changing tab triggers a refresh

    def _panel_on_use_times_updated(self):
        # Update time seeker
        t_start, t_stop = self.controller.get_t_start_t_stop()
        self.time_slider.start = t_start
        self.time_slider.end = t_stop

        # Optionally clamp the current value if out of range
        self.time_slider.value = self.controller.get_time()[0]

        self.refresh()


TraceMapView._gui_help_txt = """
## Trace Map View

This view shows the trace map of all the channels.

### Controls
* **x size (s)**: Set the time window size for the traces.
* **auto scale**: Automatically adjust the scale of the traces.
* **time (s)**: Set the time point to display traces.
* **mouse wheel**: change the scale of the traces.
* **double click**: select the nearest spike and center the view on it.
"""