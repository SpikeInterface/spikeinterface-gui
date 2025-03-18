import numpy as np
from matplotlib.path import Path as mpl_path

from .view_base import ViewBase

class SpikeAmplitudeView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _depend_on = ['spike_amplitudes']
    _settings = [
            {'name': 'alpha', 'type': 'float', 'value' : 0.7, 'limits':(0, 1.), 'step':0.05 },
            {'name': 'scatter_size', 'type': 'float', 'value' : 4., 'step':0.5 },
            {'name': 'num_bins', 'type': 'int', 'value' : 400, 'step': 1 },
            {'name': 'noise_level', 'type': 'bool', 'value' : True },
            {'name': 'noise_factor', 'type': 'int', 'value' : 5 },
        ]
    _need_compute = False
    
    def __init__(self, controller=None, parent=None, backend="qt"):
        
        # compute_amplitude_bounds
        self._amp_min = np.min(controller.spike_amplitudes)
        self._amp_max = np.max(controller.spike_amplitudes)
        eps = (self._amp_max - self._amp_min) / 100.0
        self._amp_max += eps

        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)


    def prepare_plotting_data(self):
        
        d = dict()

        # TODO handle combobox
        # seg_index =  self.combo_seg.currentIndex()
        seg_index = 0
        sl = self.controller.segment_slices[seg_index]
        spikes_in_seg = self.controller.spikes[sl]
        fs = self.controller.sampling_frequency
        
        max_count = 0
        d['scatter'] = dict()
        d['hist'] = dict()
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                continue
            
            # TODO sam : use index instead of boolean masking
            spike_mask = (spikes_in_seg['unit_index'] == unit_index)
            spikes = spikes_in_seg[spike_mask]
            spike_times = spikes['sample_index'] / fs
            amps = self.controller.spike_amplitudes[sl][spike_mask]
            d['scatter'][unit_id] = (spike_times, amps)
            

            count, bins = np.histogram(amps, bins = np.linspace(self._amp_min, self._amp_max, self.settings['num_bins']))
            d['hist'][unit_id] = (count, bins)
            
            max_count = max(max_count, np.max(count))

        d['hist_max'] = max_count


        selected_indices = self.controller.get_indices_spike_selected()
        mask = np.isin(sl.start + np.arange(len(spikes_in_seg)), selected_indices)
        if np.any(mask):
            selected_spikes = spikes_in_seg[mask]
            spike_times = selected_spikes['sample_index'] / fs
            amps = self.controller.spike_amplitudes[sl][mask]
            d['selected'] = (spike_times, amps)
        
        d['time_lims'] = 0., self.controller.get_num_samples(seg_index) / self.controller.sampling_frequency

        return d



    # def get_segment_data(self, seg_index):
    #     sl = self.controller.segment_slices[seg_index]
    #     spikes_in_seg = self.controller.spikes[sl]
    #     fs = self.controller.sampling_frequency
    #     return spikes_in_seg, sl, fs

    # def get_unit_data(self, unit_index, spikes_in_seg):
    #     """Get spike times and amplitudes for a specific unit"""
    #     # Handle case when there are no spikes
    #     if len(spikes_in_seg) == 0:
    #         return np.array([]), np.array([])

    #     # Create mask for the current segment
    #     spike_mask = spikes_in_seg["unit_index"] == unit_index
    #     spikes = spikes_in_seg[spike_mask]

    #     # Handle case when no spikes for this unit
    #     if len(spikes) == 0:
    #         return np.array([]), np.array([])

    #     spike_times = spikes["sample_index"] / self.controller.sampling_frequency

    #     # Get the slice of spike amplitudes for this segment
    #     sl = self.controller.segment_slices[spikes[0]["segment_index"]]
    #     segment_amplitudes = self.controller.spike_amplitudes[sl]
    #     amps = segment_amplitudes[spike_mask]
    #     return spike_times, amps

    # def compute_amplitude_histogram(self, amplitudes, num_bins):
    #     """Compute histogram of spike amplitudes"""
    #     count, bins = np.histogram(amplitudes, bins=np.linspace(self._amp_min, self._amp_max, num_bins))
    #     return count, bins


    # def get_view_bounds(self, seg_index):
    #     """Get time range for the view"""
    #     t1 = 0.0
    #     t2 = self.controller.get_num_samples(seg_index) / self.controller.sampling_frequency
    #     return t1, t2


    ## QT zone ##

    def _make_layout_qt(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()
        # self.setLayout(self.layout)

        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        self.combo_seg = QT.QComboBox()
        h.addWidget(self.combo_seg)
        self.combo_seg.addItems([ f'Segment {seg_index}' for seg_index in range(self.controller.num_segments) ])
        self.combo_seg.currentIndexChanged.connect(self.refresh)
        self.lasso_but = but = QT.QPushButton("select", checkable = True)
        self.lasso_but.setMaximumWidth(50)
        h.addWidget(self.lasso_but)
        self.lasso_but.clicked.connect(self.enable_disable_lasso)

        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        self.graphicsview = pg.GraphicsView()
        #~ self.graphicsview.setHorizontalStretch(3)
        #~ self.layout.addWidget(self.graphicsview)
        h.addWidget(self.graphicsview, 3)

        self.graphicsview2 = pg.GraphicsView()
        #~ self.layout.addWidget(self.graphicsview2)
        h.addWidget(self.graphicsview2, 1)
        #~ self.graphicsview2.setHorizontalStretch(1)


        self.initialize_plot()
        
        # Add lasso curve
        self.lasso = pg.PlotCurveItem(pen='#7FFF00')
        self.plot.addItem(self.lasso)
        
        # Add selection scatter
        brush = QT.QColor('white')
        brush.setAlpha(200)
        self.scatter_select = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=brush, size=11, pxMode=True)
        self.plot.addItem(self.scatter_select)
        self.scatter_select.setZValue(1000)


    
    def initialize_plot(self):
        import pyqtgraph as pg
        from .utils_qt import ViewBoxHandlingLasso

        self.viewBox = ViewBoxHandlingLasso()
        # self.viewBox.doubleclicked.connect(self.open_settings)
        self.viewBox.lasso_drawing.connect(self.on_lasso_drawing)
        self.viewBox.lasso_finished.connect(self.on_lasso_finished)
        self.viewBox.disableAutoRange()
        self.plot = pg.PlotItem(viewBox=self.viewBox)
        self.graphicsview.setCentralItem(self.plot)
        self.plot.hideButtons()
    
        self.viewBox2 = ViewBoxHandlingLasso()
        # self.viewBox2.doubleclicked.connect(self.open_settings)
        self.viewBox2.disableAutoRange()
        self.plot2 = pg.PlotItem(viewBox=self.viewBox2)
        self.graphicsview2.setCentralItem(self.plot2)
        self.plot2.hideButtons()
        self.plot2.setYLink(self.plot)

        
        self.scatter = pg.ScatterPlotItem(size=self.settings['scatter_size'], pxMode = True)
        self.plot.addItem(self.scatter)
        
        self._text_items = []
        
        self.plot.setYRange(self._amp_min,self._amp_max, padding = 0.0)

    def on_spike_selection_changed(self):
        self.refresh()

    def _refresh_qt(self):
        from .myqt import QT
        import pyqtgraph as pg
        
        self.scatter.clear()
        self.plot2.clear()
        self.scatter_select.clear()
        
        if self.controller.spike_amplitudes is None:
            return

        d = self.prepare_plotting_data()



        for unit_id in d['scatter']:
            if not self.controller.unit_visible_dict[unit_id]:
                continue
            
            # make a copy of the color
            color = QT.QColor(self.get_unit_color(unit_id))
            color.setAlpha(int(self.settings['alpha']*255))
            spike_times, amps =d['scatter'][unit_id]
            self.scatter.addPoints(x=spike_times, y=amps,  pen=pg.mkPen(None), brush=color)

            color = self.get_unit_color(unit_id)
            count, bins = d['hist'][unit_id]
            curve = pg.PlotCurveItem(count, bins[:-1], fillLevel=None, fillOutline=True, brush=color, pen=color)
            self.plot2.addItem(curve)

        # average noise across channels
        if self.settings["noise_level"]:
            n = self.settings["noise_factor"]
            noise = np.mean(self.controller.noise_levels)
            alpha_factor = 50 / n
            for i in range(1, n + 1):
                self.plot2.addItem(
                    pg.LinearRegionItem(values=(-i * noise, i * noise), orientation="horizontal",
                                        brush=(255, 255, 255, int(i * alpha_factor)), pen=(0, 0, 0, 0))
                )
            
        t1, t2 = d['time_lims']
        self.plot.setXRange( t1, t2, padding = 0.0)
        self.plot2.setXRange(0, d['hist_max'], padding = 0.0)
        
        if 'selected' in d:
            spike_times, amps = d['selected']
            self.scatter_select.setData(spike_times, amps)

    def enable_disable_lasso(self, checked):
        self.viewBox.lasso_active = checked

    def on_lasso_drawing(self, points):
        points = np.array(points)
        self.lasso.setData(points[:, 0], points[:, 1])
    
    def on_lasso_finished(self, points):
        self.lasso.setData([], [])
        vertices = np.array(points)
        
        seg_index = self.combo_seg.currentIndex()
        sl = self.controller.segment_slices[seg_index]
        spikes_in_seg = self.controller.spikes[sl]
        fs = self.controller.sampling_frequency
        
        # Create mask for visible units
        visible_mask = np.zeros(len(spikes_in_seg), dtype=bool)
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if self.controller.unit_visible_dict[unit_id]:
                visible_mask |= (spikes_in_seg['unit_index'] == unit_index)
        
        # Only consider spikes from visible units
        visible_spikes = spikes_in_seg[visible_mask]
        if len(visible_spikes) == 0:
            # Clear selection if no visible spikes
            self.controller.set_indices_spike_selected([])
            self.refresh()
            self.notify_spike_selection_changed()
            return
            
        spike_times = visible_spikes['sample_index'] / fs
        amps = self.controller.spike_amplitudes[sl][visible_mask]
        
        points = np.column_stack((spike_times, amps))
        inside = mpl_path(vertices).contains_points(points)
        
        # Clear selection if no spikes inside lasso
        if not np.any(inside):
            self.controller.set_indices_spike_selected([])
            self.refresh()
            self.notify_spike_selection_changed()
            return
            
        # Map back to original indices
        visible_indices = np.nonzero(visible_mask)[0]
        selected_indices = sl.start + visible_indices[inside]
        self.controller.set_indices_spike_selected(selected_indices)
        self.refresh()
        self.notify_spike_selection_changed()



    ## Panel zone ##
    def _make_layout_panel(self):
        import panel as pn
        from .utils_panel import _bg_color
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, HoverTool

        # Create figures
        self.scatter_fig = bpl.figure(
            sizing_mode="stretch_both",
            tools="pan,box_zoom,reset,wheel_zoom,lasso_select",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}
        )
        self.scatter_fig.xaxis.axis_label = "Time (s)"
        self.scatter_fig.yaxis.axis_label = "Amplitude"

        self.hist_fig = bpl.figure(
            tools="pan,box_zoom,reset,wheel_zoom",
            sizing_mode="stretch_both",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            styles={"flex": "1"}  # Make histogram narrower than scatter plot
        )
        self.hist_fig.yaxis.axis_label = "Amplitude"
        self.hist_fig.xaxis.axis_label = "Count"

        # Initialize data sources
        self.scatter_source = ColumnDataSource({"x": [], "y": [], "color": []})
        self.hist_sources = {}
        self.noise_sources = {}

        # Add scatter plot with correct alpha parameter
        self.scatter = self.scatter_fig.scatter(
            "x",
            "y",
            source=self.scatter_source,
            size=self.settings['scatter_size'],
            color="color",
            fill_alpha=self.settings['alpha'],
        )

        # Add hover tool
        hover = HoverTool(renderers=[self.scatter], tooltips=[("Time", "@x{0.00}"), ("Amplitude", "@y{0.00}")])
        self.scatter_fig.add_tools(hover)

        # Set and link axis ranges
        self.scatter_fig.y_range.start = self._amp_min
        self.scatter_fig.y_range.end = self._amp_max
        self.hist_fig.y_range = self.scatter_fig.y_range
        self.hist_fig.x_range.start = 0
        self.hist_fig.x_range.end = 1  # Will be updated in _refresh

        # # Create Panel layout with improved styling and responsiveness
        # self.settings_panel = pn.Param(
        #     self.settings,
        #     widgets={
        #         "alpha": {"type": pn.widgets.FloatSlider, "width": 200},
        #         "scatter_size": {"type": pn.widgets.FloatSlider, "width": 200, "start": 0.1, "end": 10},
        #         "num_bins": {"type": pn.widgets.IntSlider, "width": 200, "start": 2, "end": 1000},
        #         "noise_level": {"type": pn.widgets.Checkbox},
        #         "noise_factor": {"type": pn.widgets.IntSlider, "width": 200, "start": 2, "end": 10},
        #         "segment": {"type": pn.widgets.Select, "width": 200},
        #     },
        #     name="Settings",
        #     show_name=True,
        # )

        self.plot_panel = pn.Row(
            pn.Column(
                self.scatter_fig,
                styles={"flex": "1"},
                sizing_mode="stretch_both"
            ),
            pn.Column(
                self.hist_fig,
                styles={"flex": "0.3"},
                sizing_mode="stretch_both"
            ),
            styles={"display": "flex", "flex-direction": "row"},
            sizing_mode="stretch_both"
        )

        self.layout = pn.Column(
            pn.Column(  # Main content area
                self.plot_panel,
                styles={"flex": "1"},
                sizing_mode="stretch_both"
            ),
            # pn.Card(  # Settings panel
            #     self.settings_panel,
            #     title="Settings",
            #     collapsed=True,
            #     styles={"flex": "0.1"}
            # ),
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both"
        )

    def _refresh_panel(self):
        # import panel as pn
        # from .utils_panel import _bg_color
        # import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource, HoverTool


        # Clear existing data
        scatter_data = {"x": [], "y": [], "color": []}

        # Remove all old noise renderers
        for i in list(self.noise_sources.keys()):
            for renderer in self.hist_fig.renderers[:]:
                if renderer.data_source == self.noise_sources[i]:
                    self.hist_fig.renderers.remove(renderer)
            del self.noise_sources[i]


        d = self.prepare_plotting_data()

        # Get segment data
        # seg_index = int(self.settings.segment.split()[-1])
        # TODO
        seg_index = 0

        # spikes_in_seg, sl, fs = self.get_segment_data(seg_index)

        # Keep track of which units are shown
        # shown_units = set()


        # Update scatter plot and histogram for each unit
        max_count = 0
        for unit_index, unit_id in enumerate(self.controller.unit_ids):
            if not self.controller.unit_visible_dict[unit_id]:
                # Remove histogram renderer if it exists
                if unit_id in self.hist_sources:
                    for renderer in self.hist_fig.renderers[
                        :
                    ]:  # Make a copy of list to avoid modification during iteration
                        if renderer.data_source == self.hist_sources[unit_id]:
                            self.hist_fig.renderers.remove(renderer)
                    del self.hist_sources[unit_id]
                continue

            # shown_units.add(unit_id)


            # Get unit data using the fixed core method
            # spike_times, amps = self.get_unit_data(unit_index, spikes_in_seg)
            spike_times, amps = d['scatter'][unit_id]


            if len(spike_times) == 0:
                continue

            # Update scatter data
            # color = self.controller.qcolors[unit_id].name()
            color = self.get_unit_color(unit_id)
            scatter_data["x"].extend(spike_times)
            scatter_data["y"].extend(amps)
            scatter_data["color"].extend([color] * len(spike_times))

            # Update histogram
            # count, bins = self.compute_amplitude_histogram(amps, self.settings.num_bins)
            count, bins = d['scatter'][unit_id]
            max_count = max(max_count, np.max(count) if len(count) > 0 else 0)

            # Create or update histogram source
            # Always create a new renderer if the unit is visible
            # This ensures clean state when units are toggled
            if unit_id in self.hist_sources:
                # Remove old renderer
                for renderer in self.hist_fig.renderers[:]:
                    if renderer.data_source == self.hist_sources[unit_id]:
                        self.hist_fig.renderers.remove(renderer)

            # Create new source and renderer
            self.hist_sources[unit_id] = ColumnDataSource({"x": [], "y": []})
            self.hist_fig.hbar(
                y="y",
                right="x",
                source=self.hist_sources[unit_id],
                height=0.8 * (self._amp_max - self._amp_min) / self.settings['num_bins'],
                color=color,
                alpha=self.settings['alpha'],
            )

            self.hist_sources[unit_id].data = {
                "x": count,
                "y": bins[:-1],  # Keep bins on y-axis to match scatter plot
            }

        # Add noise level bands after histograms are drawn
        if self.settings['noise_level']:
            noise = np.mean(self.controller.noise_levels)
            n = self.settings['noise_factor']
            alpha_factor = 50 / n  # Same as Qt implementation
            for i in range(1, n + 1):
                # Create new source and renderer for each noise band
                self.noise_sources[i] = ColumnDataSource({"y": [], "x1": [], "x2": []})
                # Use harea for horizontal bands with correct parameters
                self.hist_fig.harea(
                    y="y",
                    x1="x1",
                    x2="x2",
                    source=self.noise_sources[i],
                    alpha=int(i * alpha_factor) / 255,  # Match Qt alpha scaling
                    color="lightgray",
                )

                self.noise_sources[i].data = {
                    "y": [-i * noise, i * noise],
                    "x1": [0, 0],
                    "x2": [max_count, max_count],
                }

        # Set axis ranges
        # t1, t2 = self.get_view_bounds(seg_index)
        t1, t2 = d['time_lims']
        self.scatter_fig.x_range.start = t1
        self.scatter_fig.x_range.end = t2
        self.scatter_fig.y_range.start = self._amp_min
        self.scatter_fig.y_range.end = self._amp_max

        # Update histogram x-range for proper scaling
        self.hist_fig.x_range.start = 0
        self.hist_fig.x_range.end = d['hist_max']

        # Update scatter source with correct alpha parameter
        self.scatter_source.data = scatter_data
        self.scatter.glyph.size = self.settings['scatter_size']
        self.scatter.glyph.fill_alpha = self.settings['alpha']
        



SpikeAmplitudeView._gui_help_txt = """Spike Amplitude view
Check amplitudes of spikes across the recording time or in a histogram
comparing the distribution of ampltidues to the noise levels
Mouse click : change scaling
Left click drag : draw lasso to select spikes"""
