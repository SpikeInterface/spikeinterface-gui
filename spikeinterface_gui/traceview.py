import numpy as np
import time
from contextlib import nullcontext

from .view_base import ViewBase


# This MixinViewTrace is used both in TraceView and TraceMapView) handling:
#   * toolbar
#   * time slider
#   * xsize
#   * zoom
#   * segment change
#   * 

class MixinViewTrace:

    MAX_RETRIEVE_TIME_FOR_BUSY_CURSOR = 0.5  # seconds

    def get_data_in_chunk(self, t1, t2, segment_index):
        with self.trace_context():
            ind1, ind2 = self.controller.get_chunk_indices(t1, t2, segment_index)

            t_traces_start = time.perf_counter()
            traces_chunk = self.controller.get_traces(segment_index=segment_index, start_frame=ind1, end_frame=ind2)
            times_chunk = self.controller.get_times_chunk(segment_index=segment_index, t1=t1, t2=t2)
            t_traces_end = time.perf_counter()
            elapsed = t_traces_end - t_traces_start
            if elapsed > self.MAX_RETRIEVE_TIME_FOR_BUSY_CURSOR:
                self.trace_context = self.busy_cursor
            else:
                self.trace_context = nullcontext

            sl = self.controller.segment_slices[segment_index]
            spikes_seg = self.controller.spikes[sl]
            i1, i2 = np.searchsorted(spikes_seg["sample_index"], [ind1, ind2])
            spikes_chunk = spikes_seg[i1:i2].copy()
            spikes_chunk["sample_index"] -= ind1

            # for trace map view, this returns the channels ordered by depth
            visible_channel_inds = self.get_visible_channel_inds()

            data_curves = traces_chunk[:, visible_channel_inds].copy()
            data_curves = data_curves.T  # channels x time

            if data_curves.dtype != "float32":
                data_curves = data_curves.astype("float32")
            self.last_data_curves = data_curves.copy()

            if self.factor is not None:
                n = visible_channel_inds.size
                gains = np.ones(n, dtype=float) * 1.0 / (self.factor * max(self.mad[visible_channel_inds]))
                offsets = np.arange(n)[::-1] - self.med[visible_channel_inds] * gains

                data_curves *= gains[:, None]
                data_curves += offsets[:, None]

            scatter_x = []
            scatter_y = []
            scatter_colors = []

            global_to_local_chan_inds = np.zeros(self.controller.channel_ids.size, dtype='int64')
            global_to_local_chan_inds[visible_channel_inds] = np.arange(visible_channel_inds.size, dtype='int64')

            for unit_index, unit_id in self.controller.iter_visible_units():

                inds = np.flatnonzero(spikes_chunk["unit_index"] == unit_index)
                if inds.size == 0:
                    continue

                # Get spikes for this unit
                unit_spikes = spikes_chunk[inds]
                channel_inds = unit_spikes["channel_index"]
                sample_inds = unit_spikes["sample_index"]

                chan_mask = np.isin(channel_inds, visible_channel_inds)
                if not np.any(chan_mask):
                    continue

                sample_inds = sample_inds[chan_mask]
                channel_inds = channel_inds[chan_mask]
                # Map channel indices to their positions in visible_channel_inds
                local_channel_inds = global_to_local_chan_inds[channel_inds]

                # Calculate y values using signal values
                x = times_chunk[sample_inds]
                # Handle depth ordering for TraceMapView
                if self.channel_order_reverse is not None:
                    y = self.channel_order_reverse[channel_inds] + 0.5
                else:
                    y = data_curves[local_channel_inds, sample_inds]

                # This should both for qt (QTColor) and panel (html color)
                color = self.get_unit_color(unit_id)

                scatter_x.extend(x)
                scatter_y.extend(y)
                scatter_colors.extend([color] * len(x))

        return times_chunk, data_curves, scatter_x, scatter_y, scatter_colors

    ## Qt ##
    def _qt_create_toolbars(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import TimeSeeker, add_stretch_to_qtoolbar

        tb = self.qt_widget.view_toolbar

        #Segment selection
        self.combo_seg = QT.QComboBox()
        tb.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {segment_index}' for segment_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self._qt_on_combo_seg_changed)
        add_stretch_to_qtoolbar(tb)
        
        # time slider
        self.timeseeker = TimeSeeker(show_slider=False)
        tb.addWidget(self.timeseeker)
        self.timeseeker.time_changed.connect(self._qt_on_time_changed)
        
        # winsize
        xsize_s = self.xsize
        tb.addWidget(QT.QLabel(u'X size (s)'))
        self.spinbox_xsize = pg.SpinBox(value = xsize_s, bounds = [0.001, self.settings['xsize_max']],
                                        suffix = 's', siPrefix = True, step = 0.1, dec = True)
        self.spinbox_xsize.sigValueChanged.connect(self._qt_on_xsize_changed)
        tb.addWidget(self.spinbox_xsize)
        add_stretch_to_qtoolbar(tb)
        self.spinbox_xsize.sigValueChanged.connect(self.refresh)
        
        but = QT.QPushButton('auto scale')
        but.clicked.connect(self.auto_scale)

        tb.addWidget(but)

        self.scroll_time = QT.QScrollBar(orientation=QT.Qt.Horizontal)
        self.scroll_time.valueChanged.connect(self._qt_on_scroll_time)
        if self.controller.has_extension("events"):
            bottom_layout = QT.QHBoxLayout()
            bottom_layout.addWidget(self.scroll_time, stretch=8)
            bottom_layout.addStretch()  # Push button to the right

            event_layout = QT.QHBoxLayout()
            event_keys = list(self.controller.events.keys())
            if len(event_keys) > 1:
                self.event_type_combo = QT.QComboBox()
                self.event_type_combo.addItems(event_keys)
                self.event_type_combo.currentIndexChanged.connect(self._qt_on_event_type_changed)
                event_layout.addWidget(QT.QLabel("Event:"), stretch=2)
                event_layout.addWidget(self.event_type_combo, stretch=3)
            else:
                self.event_key = event_keys[0]

            self.prev_event_button = QT.QPushButton("◀")
            self.next_event_button = QT.QPushButton("▶")
            self.prev_event_button.setMaximumWidth(30)
            self.next_event_button.setMaximumWidth(30)
            self.next_event_button.clicked.connect(self._qt_on_next_event)
            self.prev_event_button.clicked.connect(self._qt_on_prev_event)
            event_layout.addWidget(self.prev_event_button, stretch=1)
            event_layout.addWidget(self.next_event_button, stretch=1)

            # Wrap event_layout in a QWidget
            event_widget = QT.QWidget()
            event_widget.setLayout(event_layout)
            bottom_layout.addWidget(event_widget)
            bottom_widget = QT.QWidget()
            bottom_widget.setLayout(bottom_layout)
        else:
            bottom_widget = self.scroll_time

        self.bottom_toolbar = bottom_widget
        
    def _qt_initialize_plot(self):
        from .myqt import QT
        import pyqtgraph as pg
        from .utils_qt import ViewBoxForTrace


        self.viewBox = ViewBoxForTrace()
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
        self.plot.showAxis('left', False)
        self.viewBox.doubleclicked.connect(self._qt_scatter_item_clicked)
        
        self.viewBox.gain_zoom.connect(self.apply_gain_zoom)
        self.viewBox.xsize_zoom.connect(self._qt_xsize_zoom)
        
        self.signals_curve = pg.PlotCurveItem(pen='#7FFF00', connect='finite')
        self.plot.addItem(self.signals_curve)

        self.channel_labels = []
        self.threshold_lines =[]
        for i, channel_id in enumerate(self.controller.channel_ids):
            label = pg.TextItem(f'{i}: {channel_id}', color='#FFFFFF', anchor=(0, 0.5), border=None, fill=pg.mkColor((128,128,128, 180)))
            self.plot.addItem(label)
            self.channel_labels.append(label)
        
        pen = pg.mkPen(color=(128,0,128, 120), width=3, style=QT.Qt.DashLine)
        self.selection_line = pg.InfiniteLine(pos = 0., angle=90, movable=False, pen = pen)
        self.plot.addItem(self.selection_line)
        self.selection_line.hide()
        
        self.gains = None
        self.offsets = None

    def _qt_update_scroll_limits(self):
        segment_index = self.controller.get_time()[1]
        length = self.controller.get_num_samples(segment_index)
        t_start, t_stop = self.controller.get_t_start_t_stop()
        self.timeseeker.set_start_stop(t_start, t_stop, seek=False)
        self.scroll_time.setMinimum(0)
        self.scroll_time.setMaximum(length - 1)

    def _qt_change_segment(self, segment_index):
        #TODO: dirty because now seg_pos IS segment_index
        self.controller.set_time(segment_index=segment_index)

        if segment_index != self.combo_seg.currentIndex():
            self.combo_seg.setCurrentIndex(segment_index)

        self._qt_update_scroll_limits()
        if not self._block_auto_refresh_and_notify:
            self.refresh()
            self.notify_time_info_updated()

    def _qt_on_time_changed(self, t):
        self.controller.set_time(time=t)
        if not self._block_auto_refresh_and_notify:
            self._qt_seek(t)
            self.notify_time_info_updated()

    def _qt_on_combo_seg_changed(self):
        s = self.combo_seg.currentIndex()
        if not self._block_auto_refresh_and_notify:
            self._qt_change_segment(s)
    
    def _qt_on_xsize_changed(self):
        xsize = self.spinbox_xsize.value()
        self.xsize = xsize
        if not self._block_auto_refresh_and_notify:
            self.refresh()
            self.notify_time_info_updated()

    def _qt_xsize_zoom(self, xmove):
        factor = xmove/100.
        newsize = self.xsize*(factor+1.)
        limits = self.spinbox_xsize.opts['bounds']
        if newsize > 0. and newsize < limits[1]:
            self.spinbox_xsize.setValue(newsize)

    def _qt_on_scroll_time(self, val):
        time = self.controller.sample_index_to_time(val)
        self.timeseeker.seek(time)

    def _qt_seek_with_selected_spike(self):
        ind_selected = self.controller.get_indices_spike_selected()
        n_selected = ind_selected.size
        
        if self.settings['auto_zoom_on_select'] and n_selected == 1:
            ind = ind_selected[0]
            peak_ind = self.controller.spikes[ind]['sample_index']
            segment_index = self.controller.spikes[ind]['segment_index']
            peak_time = self.controller.sample_index_to_time(peak_ind)

            if segment_index != self.controller.get_time()[1]:
                self._qt_change_segment(segment_index)

            self.spinbox_xsize.sigValueChanged.disconnect(self._qt_on_xsize_changed)
            self.xsize = self.settings['spike_selection_xsize']
            self.spinbox_xsize.setValue(self.xsize)
            self.spinbox_xsize.sigValueChanged.connect(self._qt_on_xsize_changed)

            self.controller.set_time(time=peak_time)
        self.refresh()

    def _qt_scatter_item_clicked(self, x, y):
        ind_spike_nearest = find_nearest_spike(self.controller, x, segment_index=self.controller.get_time()[1])
        if ind_spike_nearest is not None:
            self.controller.set_indices_spike_selected([ind_spike_nearest])

            self.notify_spike_selection_changed()
            self._qt_seek_with_selected_spike()
            # change selected unit
            unit_id = self.controller.unit_ids[self.controller.spikes[ind_spike_nearest]["unit_index"]]
            self.controller.set_visible_unit_ids([unit_id])
            self.notify_unit_visibility_changed()

    def _qt_on_event_type_changed(self):
        self.event_key = self.event_type_combo.currentText()
        self.refresh()

    def _qt_add_event_line(self):
        import pyqtgraph as pg
        from .myqt import QT

        # Add vertical line at event time
        evt_time = self.controller.get_time()[0]
        if hasattr(self, 'event_line'):
            self.event_line.setValue(evt_time)
            self.event_line.show()
        else:
            pen = pg.mkPen(color=(255, 255, 0, 180), width=2, style=QT.Qt.DotLine)
            self.event_line = pg.InfiniteLine(pos=evt_time, angle=90, movable=False, pen=pen)
            self.plot.addItem(self.event_line)

    def _qt_remove_event_line(self):
        if hasattr(self, 'event_line'):
            self.plot.removeItem(self.event_line)
            del self.event_line

    def _qt_on_next_event(self):

        current_sample = self.controller.time_to_sample_index(self.controller.get_time()[0])
        event_samples = self.controller.get_events(self.event_key)
        next_events = event_samples[event_samples > current_sample]
        if next_events.size > 0:
            next_evt_sample = next_events[0]
            evt_time = self.controller.sample_index_to_time(next_evt_sample)
            self.controller.set_time(time=evt_time)
            self.timeseeker.seek(evt_time)
            self._qt_add_event_line()

    def _qt_on_prev_event(self):
        current_sample = self.controller.time_to_sample_index(self.controller.get_time()[0])
        event_samples = self.controller.get_events(self.event_key)
        prev_events = event_samples[event_samples < current_sample]
        if prev_events.size > 0:
            prev_evt_sample = prev_events[-1]
            evt_time = self.controller.sample_index_to_time(prev_evt_sample)
            self.controller.set_time(time=evt_time)
            self.timeseeker.seek(evt_time)
            self._qt_add_event_line()

    ## panel ##
    def _panel_create_toolbars(self):
        import panel as pn

        segment_index = self.controller.get_time()[1]
        self.segment_selector = pn.widgets.Select(
            name="",
            options=[f"Segment {i}" for i in range(self.controller.num_segments)],
            value=f"Segment {segment_index}",
        )

        # Window size control
        self.xsize_spinner = pn.widgets.FloatInput(
            name="", value=self.xsize, start=0.001, end=self.settings['xsize_max'], step=0.1
        )
        xsize_label = pn.widgets.StaticText(name="", value="Window Size (s)")
        xsize = pn.Row(xsize_label, self.xsize_spinner)

        # Auto scale button
        self.auto_scale_button = pn.widgets.Button(name="Auto Scale", button_type="default")

        # Connect events
        self.segment_selector.param.watch(self._panel_on_segment_changed, "value")
        self.xsize_spinner.param.watch(self._panel_on_xsize_changed, "value")
        self.auto_scale_button.on_click(self._panel_auto_scale)

        self.toolbar = pn.Row(
            self.segment_selector,
            xsize,
            self.auto_scale_button,
            sizing_mode="stretch_width",
        )

        # Time slider
        segment_index = self.controller.get_time()[1]
        # update with controller.get_t_start/get_t_end
        t_start, t_stop = self.controller.get_t_start_t_stop()
        self.time_slider = pn.widgets.FloatSlider(name="Time (s)", start=t_start, end=t_stop, value=0, step=0.1, 
                                                  value_throttled=0, sizing_mode="stretch_width")
        self.time_slider.param.watch(self._panel_on_time_slider_changed, "value_throttled")

        bottom_toolbar_items = [self.time_slider]
        if self.controller.has_extension("events"):
            event_keys = list(self.controller.events.keys())
            if len(event_keys) > 1:
                self.event_type_selector = pn.widgets.Select(name="Event", options=event_keys, value=event_keys[0])
                self.event_type_selector.param.watch(self._panel_on_event_type_changed, "value")
                bottom_toolbar_items.append(self.event_type_selector)
            else:
                self.event_key = event_keys[0]

            self.prev_event_button = pn.widgets.Button(name="◀", button_type="default", width=40)
            self.next_event_button = pn.widgets.Button(name="▶", button_type="default", width=40)
            self.prev_event_button.on_click(self._panel_on_prev_event)
            self.next_event_button.on_click(self._panel_on_next_event)

            bottom_toolbar_items.append(self.prev_event_button)
            bottom_toolbar_items.append(self.next_event_button)
        self.bottom_toolbar = pn.Row(*bottom_toolbar_items, sizing_mode="stretch_width")

    def _panel_on_segment_changed(self, event):
        segment_index = int(event.new.split()[-1])
        self._panel_change_segment(segment_index)

    def _panel_change_segment(self, segment_index):
        self.segment_selector.value = f"Segment {segment_index}"

        # Update time slider range
        self.controller.set_time(segment_index=segment_index)
        t_start, t_stop = self.controller.get_t_start_t_stop()
        self.time_slider.start = t_start
        self.time_slider.end = t_stop
        if not self._block_auto_refresh_and_notify:
            self.refresh()
            self.notify_time_info_updated()

    def _panel_on_xsize_changed(self, event):
        self.xsize = event.new
        if not self._block_auto_refresh_and_notify:
            self.refresh()
            self.notify_time_info_updated()

    def _panel_on_time_slider_changed(self, event):
        self.controller.set_time(time=event.new)
        if not self._block_auto_refresh_and_notify:
            self.refresh()
            self.notify_time_info_updated()

    def _panel_seek_with_selected_spike(self):
        ind_selected = self.controller.get_indices_spike_selected()
        n_selected = ind_selected.size

        if self.settings['auto_zoom_on_select'] and n_selected == 1:
            ind = ind_selected[0]
            peak_ind = self.controller.spikes[ind]["sample_index"]
            segment_index = self.controller.spikes[ind]["segment_index"]
            peak_time = self.controller.sample_index_to_time(peak_ind)

            if segment_index != self.controller.get_time()[1]:
                self._panel_change_segment(segment_index)

            # block callbacks
            self._block_auto_refresh_and_notify = True

            self.xsize = self.settings['spike_selection_xsize']
            self.xsize_spinner.value = self.xsize

            # Update time slider
            self.time_slider.value = peak_time
            self.controller.set_time(peak_time)

            # Center view on spike
            margin = self.xsize / 3
            self.figure.x_range.start = peak_time - margin
            self.figure.x_range.end = peak_time + 2 * margin

            self._block_auto_refresh_and_notify = False
            self.refresh()
            self.notify_time_info_updated()

    def _panel_on_double_tap(self, event):
        time = event.x
        ind_spike_nearest = find_nearest_spike(self.controller, time, self.controller.get_time()[1])
        if ind_spike_nearest is not None:
            self.controller.set_indices_spike_selected([ind_spike_nearest])
            self._panel_seek_with_selected_spike()
            self.notify_spike_selection_changed()
            # change selected unit
            unit_id = self.controller.unit_ids[self.controller.spikes[ind_spike_nearest]["unit_index"]]
            self.controller.set_visible_unit_ids([unit_id])
            self.notify_unit_visibility_changed()

    def _panel_on_event_type_changed(self, event):
        self.event_key = event.new
        self.refresh()

    def _panel_on_next_event(self, event):
        current_sample = self.controller.time_to_sample_index(self.controller.get_time()[0])
        event_samples = self.controller.get_events(self.event_key)
        next_events = event_samples[event_samples > current_sample]
        if next_events.size > 0:
            next_evt_sample = next_events[0]
            evt_time = self.controller.sample_index_to_time(next_evt_sample)
            self.controller.set_time(time=evt_time)
            self.time_slider.value = evt_time
            self._panel_refresh()
            self._panel_add_event_line()

    def _panel_on_prev_event(self, event):
        current_sample = self.controller.time_to_sample_index(self.controller.get_time()[0])
        event_samples = self.controller.get_events(self.event_key)
        prev_events = event_samples[event_samples < current_sample]
        if prev_events.size > 0:
            prev_evt_sample = prev_events[-1]
            evt_time = self.controller.sample_index_to_time(prev_evt_sample)
            self.controller.set_time(time=evt_time)
            self.time_slider.value = evt_time
            self._panel_refresh()
            self._panel_add_event_line()

    def _panel_add_event_line(self):
        # Add vertical line at event time
        evt_time = self.controller.get_time()[0]
        # get yspan from self.figure
        fig = self.figure
        yspan = [fig.y_range.start, fig.y_range.end]
        self.event_source.data = dict(x=[evt_time, evt_time], y=yspan)

    def _panel_remove_event_line(self):
        self.event_source.data = dict(x=[], y=[])

    # TODO: pan behavior like Qt?
    # def _panel_on_pan_start(self, event):
    #     self.drag_state["x_start"] = event.x

    # def _panel_on_pan(self, event):
    #     print("Panning...")
    #     if self.drag_state["x_start"] is None:
    #         return
    #     delta = event.x - self.drag_state["x_start"]
    #     print(f"Delta: {delta}")
    #     factor = 1.0 - (delta * 10)  # adjust sensitivity
    #     factor = max(0.5, min(factor, 2.0))  # limit zoom factor
    #     print(f"Change xsize by factor: {factor}. From {self.xsize} to {self.xsize * factor}")

    #     self.xsize_spinner.value = self.xsize * factor

    # def _panel_on_pan_end(self, event):
    #     self.drag_state["x_start"] = None


class TraceView(ViewBase, MixinViewTrace):
    _supported_backend = ['qt', 'panel']

    _depend_on = ['recording', 'noise_levels']
    _settings = [
        {'name': 'auto_zoom_on_select', 'type': 'bool', 'value': True},
        {'name': 'spike_selection_xsize', 'type': 'float', 'value':  0.03, 'step' : 0.001},
        {'name': 'plot_threshold', 'type': 'bool', 'value':  True},
        {'name': 'alpha', 'type': 'float', 'value' : 0.8, 'limits':(0, 1.), 'step':0.05},
        {'name': 'xsize_max', 'type': 'float', 'value': 4.0, 'step': 1.0, 'limits':(1.0, np.inf)},
        {'name': 'max_visible_channel', 'type': 'int', 'value':  16},
    ]


    def __init__(self, controller=None, parent=None, backend="qt"):

        self.mad = controller.noise_levels.astype("float32").copy()
        # we make the assumption that the signal is center on zero (HP filtered)
        self.med = np.zeros(self.mad.shape, dtype="float32")
        self.factor = 15.0
        self.xsize = 0.5
        self._block_auto_refresh_and_notify = False
        self.trace_context = nullcontext

        self.channel_order, self.channel_order_reverse = None, None
        self.last_data_curves, self.last_scatter = None, None

        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        MixinViewTrace.__init__(self)

    
    def on_channel_visibility_changed(self):
        self.refresh()

    def get_visible_channel_inds(self):
        # TODO add option to order by depth
        inds = self.controller.visible_channel_inds
        n_max = self.settings['max_visible_channel']
        if inds.size > n_max:
            inds = inds[:n_max]
        return inds

    def auto_scale(self):
        self.factor = 15.
        trace_context = self.trace_context
        self.trace_context = nullcontext
        self.refresh()
        self.trace_context = trace_context

    def apply_gain_zoom(self, factor_ratio):
        self.factor *= factor_ratio
        trace_context = self.trace_context
        self.trace_context = nullcontext
        self.refresh()
        self.trace_context = trace_context

    ## qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg


        self.layout = QT.QVBoxLayout()
        # self.setLayout(self.layout)
        
        self._qt_create_toolbars()

        # create graphic view and 2 scroll bar
        # g = QT.QGridLayout()
        # self.layout.addLayout(g)
        self.graphicsview = pg.GraphicsView()
        # g.addWidget(self.graphicsview, 0, 1)
        self.layout.addWidget(self.graphicsview)

        MixinViewTrace._qt_initialize_plot(self)
        self.scatter = pg.ScatterPlotItem(size=10, pxMode = True)
        self.plot.addItem(self.scatter)

        self.layout.addWidget(self.bottom_toolbar)
        self._qt_update_scroll_limits()

    def _qt_on_settings_changed(self):
        # adjust xsize spinbox bounds, and adjust xsize if out of bounds
        self.spinbox_xsize.opts['bounds'] = [0.001, self.settings['xsize_max']]
        if self.xsize > self.settings['xsize_max']:
            self.spinbox_xsize.sigValueChanged.disconnect(self._qt_on_xsize_changed)
            self.spinbox_xsize.setValue(self.settings['xsize_max'])
            self.controller.set_time_info(dict(xsize_s=self.settings['xsize_max']))
            self.spinbox_xsize.sigValueChanged.connect(self._qt_on_xsize_changed)
            self.notify_time_info_updated()
        # self.reset_gain_and_offset()
        self.refresh()

    def _qt_on_spike_selection_changed(self):
        MixinViewTrace._qt_seek_with_selected_spike(self)

    def _qt_refresh(self):
        self._qt_remove_event_line()
        t, _ = self.controller.get_time()
        self._qt_seek(t)

    def _qt_seek(self, t):
        from .myqt import QT
        import pyqtgraph as pg

        if self.qt_widget.sender() is not self.timeseeker:
            self.timeseeker.seek(t, emit=False)

        xsize = self.xsize
        t1, t2 = t - xsize/3., t + xsize * 2/3.
        sr = self.controller.sampling_frequency

        self.scroll_time.valueChanged.disconnect(self._qt_on_scroll_time)
        value = self.controller.time_to_sample_index(t)
        self.scroll_time.setValue(value)
        self.scroll_time.setPageStep(int(sr*xsize))
        self.scroll_time.valueChanged.connect(self._qt_on_scroll_time)

        visible_channel_inds = self.get_visible_channel_inds()
        if len(visible_channel_inds) == 0:
            self.signals_curve.setData([], [])
            self.scatter.setData(x=[], y=[], brush=[])
            for chan_ind, chan_id in enumerate(self.controller.channel_ids):
                self.channel_labels[chan_ind].hide()
            return

        times_chunk, data_curves, scatter_x, scatter_y, scatter_colors = \
            self.get_data_in_chunk(t1, t2,  self.controller.get_time()[1])

        if times_chunk.size == 0:
            self.signals_curve.setData([], [])
            self.scatter.setData(x=[], y=[], brush=[])
            return

        connect = np.ones(data_curves.shape, dtype='bool')
        connect[:, -1] = 0

        times_chunk_tile = np.tile(times_chunk, visible_channel_inds.size)
        self.signals_curve.setData(times_chunk_tile, data_curves.flatten(), connect=connect.flatten())

        self.scatter.setData(x=scatter_x, y=scatter_y, brush=scatter_colors)

        # TODO sam : scatter selection
        
        # channel labels
        for chan_ind, chan_id in enumerate(self.controller.channel_ids):
            self.channel_labels[chan_ind].hide()
        
        for i, chan_ind in enumerate(visible_channel_inds):
            self.channel_labels[chan_ind].setPos(t1, visible_channel_inds.size - 1 - i)
            self.channel_labels[chan_ind].show()

        # ranges
        self.plot.setXRange(t1, t2, padding=0.0)
        self.plot.setYRange(-.5, visible_channel_inds.size - .5, padding=0.0)

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
        # Update time seeker
        self._block_auto_refresh_and_notify = True
        t_start, t_stop = self.controller.get_t_start_t_stop()
        self.timeseeker.set_start_stop(t_start, t_stop)
        self.timeseeker.seek(self.controller.get_time()[0])
        self.refresh()
        self._block_auto_refresh_and_notify = False

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from .utils_panel import _bg_color
        from bokeh.models import ColumnDataSource, Range1d
        from bokeh.events import DoubleTap, MouseWheel

        self.figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="reset",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.figure.toolbar.logo = None
        self.figure.x_range = Range1d(start=0, end=1)
        self.figure.y_range = Range1d(start=-0.5, end=len(self.controller.channel_ids) - 0.5)

        self.figure.grid.visible = False
        self.figure.toolbar.logo = None
        self.figure.on_event(MouseWheel, self._panel_gain_zoom)

        # Configure axes
        self.figure.xaxis.axis_label_text_color = "white"
        self.figure.xaxis.axis_line_color = "white"
        self.figure.xaxis.major_label_text_color = "white"
        self.figure.xaxis.major_tick_line_color = "white"
        self.figure.yaxis.visible = False

        # Add data sources
        self.signal_source = ColumnDataSource({"xs": [], "ys": []})

        self.spike_source = ColumnDataSource({"x": [], "y": [], "color": []})

        # Plot signals
        self.signal_renderer = self.figure.multi_line(
            xs="xs", ys="ys", source=self.signal_source, line_color="#7FFF00", line_width=1, line_alpha=0.8
        )

        # Plot spikes
        self.spike_renderer = self.figure.scatter(
            x="x", y="y", size=10, fill_color="color", fill_alpha=self.settings['alpha'], source=self.spike_source
        )

        self.event_source = ColumnDataSource({"x": [], "y": []})
        self.event_renderer = self.figure.line(
            x="x", y="y", source=self.event_source, line_color="yellow", line_width=2, line_dash='dashed'
        )

        self.figure.on_event(DoubleTap, self._panel_on_double_tap)

        self._panel_create_toolbars()
        
        self.layout = pn.Column(
            self.toolbar,
            self.figure,
            self.bottom_toolbar,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both"
        )


    def _panel_refresh(self):
        self._panel_remove_event_line()
        t, segment_index = self.controller.get_time()
        xsize = self.xsize
        t1, t2 = t - xsize / 3.0, t + xsize * 2 / 3.0

        visible_channel_inds = self.get_visible_channel_inds()
        n = visible_channel_inds.size

        if n == 0:
            self.signal_source.data.update({
                "xs": [[]],
                "ys": [[]],
            })
            self.spike_source.data.update({
                "x": [],
                "y": [],
                "color": [],
            })
            self.figure.x_range.start = t1
            self.figure.x_range.end = t2
        else:
            times_chunk, data_curves, scatter_x, scatter_y, scatter_colors = \
                self.get_data_in_chunk(t1, t2, segment_index)

            self.signal_source.data.update(
                {
                    "xs": [times_chunk]*n,
                    "ys": [data_curves[i, :] for i in range(n)],
                }
            )

            self.spike_source.data.update(
                {
                    "x": scatter_x,
                    "y": scatter_y,
                    "color": scatter_colors,
                }
            )

            # Update plot ranges for x-axis too
            self.figure.x_range.start = t1
            self.figure.x_range.end = t2
            self.figure.y_range.end = n - 0.5

    # TODO: if from a different unit, change unit visibility

    def _panel_on_spike_selection_changed(self):
        self._panel_seek_with_selected_spike()

    def _panel_gain_zoom(self, event):
        if event is not None:
            factor_ratio = 1.3 if event.delta > 0 else 1 / 1.3
        else:
            factor_ratio = 1.0
        self.apply_gain_zoom(factor_ratio)

    def _panel_auto_scale(self, event):
        self.auto_scale()

    def _panel_on_time_info_updated(self):
        # Update segment and time slider range
        time, segment_index = self.controller.get_time()
        self._block_auto_refresh_and_notify = True
        self._panel_change_segment(segment_index)
        # Update time slider value
        self.time_slider.value = time
        self.refresh()
        self._block_auto_refresh_and_notify = False

    def _panel_on_use_times_updated(self):
        # Update time seeker
        t_start, t_stop = self.controller.get_t_start_t_stop()
        self._block_auto_refresh_and_notify = True
        self.time_slider.start = t_start
        self.time_slider.end = t_stop
        self.time_slider.value = self.controller.get_time()[0]
        self.refresh()
        self._block_auto_refresh_and_notify = False



def find_nearest_spike(controller, x, segment_index, max_distance_samples=None):
    if max_distance_samples is None:
        max_distance_samples = controller.sampling_frequency // 30

    ind_click = controller.time_to_sample_index(x)
    (in_seg,) = np.nonzero(controller.spikes["segment_index"] == segment_index)

    if len(in_seg) == 0:
        return None

    nearest = np.argmin(np.abs(controller.spikes[in_seg]["sample_index"] - ind_click))
    ind_spike_nearest = in_seg[nearest]
    sample_index = controller.spikes[ind_spike_nearest]["sample_index"]

    if np.abs(ind_click - sample_index) > max_distance_samples:
        return None

    return ind_spike_nearest

    
TraceView._gui_help_txt = """
## Trace View

This view shows the traces of the selected visible channels from the Probe View.

### Controls
* **x size (s)**: Set the time window size for the traces.
* **auto scale**: Automatically adjust the scale of the traces.
* **time (s)**: Set the time point to display traces.
* **mouse wheel**: change the scale of the traces.
* **double click**: select the nearest spike and center the view on it.
"""
