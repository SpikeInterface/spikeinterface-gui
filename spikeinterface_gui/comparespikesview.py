import numpy as np

from .compareunitvennview import CompareUnitVennView, solve_venn_geometry


class CompareSpikesView(CompareUnitVennView):
    """
    Venn diagram of the spikes of one pair of units (one per sorter): spikes found by both,
    and spikes found by only one of the two. Clicking a region selects its spikes.
    When the waveforms extension is loaded, sample waveforms of the 3 regions are plotted below.
    """
    id = "comparespikes"
    _supported_backend = ['qt', 'panel']
    _depend_on = ['comparison']
    _settings = [
        {'name': 'max_waveforms', 'type': 'int', 'value': 100},
    ]
    # the waveform panels, left to right like the venn regions
    _regions = ('only1', 'matched', 'only2')

    def __init__(self, controller=None, parent=None, backend="qt"):
        # the spike venn of the visible pair, recomputed when the pair changes (it is cheap)
        self._compared_pair = None
        self._spike_venn = None
        CompareUnitVennView.__init__(self, controller=controller, parent=parent, backend=backend)

    def has_waveforms(self):
        return self.controller.waveforms_ext is not None

    def get_visible_pair(self):
        """The (unit_id1, unit_id2) pair when the visible units are one unit of each sorter, else None"""
        visible_unit_ids = list(self.controller.get_visible_unit_ids())
        if len(visible_unit_ids) != 2:
            return None
        visible_unit_ids.sort(key=self.controller.get_analyzer_index)
        if [self.controller.get_analyzer_index(u) for u in visible_unit_ids] != [1, 2]:
            return None
        return tuple(visible_unit_ids)

    def update_spike_venn(self):
        pair = self.get_visible_pair()
        if pair == self._compared_pair:
            return
        self._compared_pair = pair
        self._spike_venn = None if pair is None else self.controller.get_spike_venn(*pair)

    def get_venn_data(self):
        if self._spike_venn is None:
            venn = dict(matched=[], only1=[], only2=[])
        else:
            venn = dict(
                matched=self._spike_venn['matched1'],
                only1=self._spike_venn['only1'],
                only2=self._spike_venn['only2'],
            )
        geometry = solve_venn_geometry(len(venn['only1']), len(venn['matched']), len(venn['only2']))
        return venn, geometry

    def get_region_spikes(self, region):
        """The spikes of a region, as {unit_id: spike_inds}"""
        unit_id1, unit_id2 = self._compared_pair
        if region == 'matched':
            return {
                unit_id1: self._spike_venn['matched1'],
                unit_id2: self._spike_venn['matched2'],
            }
        elif region == 'only1':
            return {unit_id1: self._spike_venn['only1']}
        else:
            return {unit_id2: self._spike_venn['only2']}

    def select_units_on_click(self, x, y, reset=True):
        # here a click selects the spikes of a region, not units
        _, geometry = self.get_venn_data()
        self.select_region(self.get_clicked_region(x, y, geometry))

    def get_region_button_labels(self):
        """{region: label} of the buttons that select a region, which can be too thin to click"""
        return {
            'only1': f'Select {self.controller.analyzer1_name}',
            'matched': 'Select match',
            'only2': f'Select {self.controller.analyzer2_name}',
        }

    def select_region(self, region):
        """Select the spikes of a region: 'only1', 'matched' or 'only2'"""
        venn, _ = self.get_venn_data()
        if region is None or len(venn[region]) == 0:
            return
        spike_inds_by_unit = self.get_region_spikes(region)
        self.controller.set_indices_spike_selected(np.sort(np.concatenate(list(spike_inds_by_unit.values()))))
        self.notify_spike_selection_changed()

    def get_waveforms_data(self, spike_inds_by_unit):
        """
        The waveforms to plot, on the extremum channel of the unit of sorter 1, so that the
        3 panels are comparable.

        Returns (times_ms, lines, title) where lines is a list of (color, wfs, is_mean),
        or None when there are no waveforms.
        """
        controller = self.controller
        unit_id1, unit_id2 = self._compared_pair
        channel_index = controller.get_main_channel(unit_id1)
        colors = {unit_id1: self._color1, unit_id2: self._color2}
        rng = np.random.default_rng()

        lines = []
        num_plotted = []
        for unit_id, spike_inds in spike_inds_by_unit.items():
            result = controller.get_waveforms_for_spikes(unit_id, spike_inds)
            if result is None:
                return None
            wfs, chan_inds, kept = result
            num_plotted.append(len(kept))
            chan_pos = np.flatnonzero(chan_inds == channel_index)
            if len(chan_pos) == 0 or len(kept) == 0:
                # the extremum channel is not in the sparsity of this unit
                continue
            wfs = wfs[:, :, chan_pos[0]]
            if wfs.shape[0] > self.settings['max_waveforms']:
                wfs = wfs[rng.choice(wfs.shape[0], self.settings['max_waveforms'], replace=False)]
            lines.append((colors[unit_id], wfs, False))
            lines.append((colors[unit_id], wfs.mean(axis=0, keepdims=True), True))

        num_samples = controller.nbefore + controller.nafter
        times_ms = (np.arange(num_samples) - controller.nbefore) / controller.sampling_frequency * 1000.
        # the counts of the regions are in the Venn diagram, the title only tells how many
        # spikes have waveforms: short, a title wider than the plot crops it in Qt
        if len(num_plotted) == 1:
            title = f"n={num_plotted[0]}"
        else:
            title = " ".join(f"n{i + 1}={n}" for i, n in enumerate(num_plotted))
        return times_ms, lines, title

    def iter_waveforms_data(self):
        """(panel index, waveforms data or None) for the 3 regions"""
        for i, region in enumerate(self._regions):
            data = None if self._spike_venn is None else self.get_waveforms_data(self.get_region_spikes(region))
            yield i, data

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        self.pair_label = QT.QLabel('')
        self.layout.addWidget(self.pair_label)

        self._qt_make_venn_plot()

        buttons = QT.QHBoxLayout()
        self.region_buttons = {}
        for region, label in self.get_region_button_labels().items():
            button = QT.QPushButton(label)
            button.clicked.connect(lambda checked=False, region=region: self.select_region(region))
            buttons.addWidget(button)
            self.region_buttons[region] = button
        self.layout.addLayout(buttons)

        self.waveform_plots = []
        if self.has_waveforms():
            waveform_layout = QT.QHBoxLayout()
            for i in range(len(self._regions)):
                plot = pg.PlotWidget()
                plot.setLabel('bottom', 'time (ms)')
                if i > 0:
                    plot.setYLink(self.waveform_plots[0])
                waveform_layout.addWidget(plot)
                self.waveform_plots.append(plot)
            self.layout.addLayout(waveform_layout)

    def _qt_refresh(self):
        self.update_spike_venn()
        pair = self._compared_pair
        if pair is None:
            self.pair_label.setText('select a pair of units, one of each sorter')
        else:
            self.pair_label.setText(f'{pair[0]} vs {pair[1]}')
        venn, geometry = self.get_venn_data()
        self._qt_draw_venn(venn, geometry)
        for region, button in self.region_buttons.items():
            button.setEnabled(len(venn[region]) > 0)
        self._qt_draw_waveforms()

    def _qt_draw_waveforms(self):
        import pyqtgraph as pg

        for i, data in self.iter_waveforms_data() if self.has_waveforms() else []:
            plot = self.waveform_plots[i]
            plot.clear()
            plot.setTitle('')
            if data is None:
                continue
            times_ms, lines, title = data
            for color, wfs, is_mean in lines:
                qcolor = pg.mkColor(color)
                qcolor.setAlphaF(1.0 if is_mean else 0.3)
                # all the waveforms of a unit in one curve, separated by nan
                xs = np.tile(np.append(times_ms, np.nan), wfs.shape[0])
                ys = np.hstack([wfs, np.full((wfs.shape[0], 1), np.nan)]).ravel()
                curve = pg.PlotCurveItem(xs, ys, connect='finite', pen=pg.mkPen(qcolor, width=3 if is_mean else 1))
                plot.addItem(curve)
            plot.setTitle(title, size='9pt')
            # a zoom on a previous pair would otherwise stick to the next ones
            plot.enableAutoRange()

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource
        from .utils_panel import _bg_color

        self.pair_label = pn.pane.Markdown("")

        self._panel_make_venn_figure()

        self.waveform_figures = []
        self.waveform_sources = []
        if self.has_waveforms():
            for i in range(len(self._regions)):
                # the 3 panels share the y range of the first one
                y_range = dict(y_range=self.waveform_figures[0].y_range) if i > 0 else {}
                fig = bpl.figure(
                    sizing_mode="stretch_both",
                    tools="pan,wheel_zoom,reset",
                    background_fill_color=_bg_color,
                    border_fill_color=_bg_color,
                    outline_line_color="white",
                    x_axis_label="time (ms)",
                    **y_range,
                )
                fig.toolbar.logo = None
                source = ColumnDataSource({"xs": [], "ys": [], "color": [], "alpha": [], "width": []})
                fig.multi_line(
                    xs="xs", ys="ys", source=source,
                    line_color="color", line_alpha="alpha", line_width="width",
                )
                self.waveform_figures.append(fig)
                self.waveform_sources.append(source)

        self.region_buttons = {}
        for region, label in self.get_region_button_labels().items():
            button = pn.widgets.Button(name=label, sizing_mode="stretch_width")
            button.on_click(lambda event, region=region: self.select_region(region))
            self.region_buttons[region] = button

        items = [self.pair_label, self.figure, pn.Row(*self.region_buttons.values(), sizing_mode="stretch_width")]
        if self.has_waveforms():
            items.append(pn.Row(*self.waveform_figures, sizing_mode="stretch_both", styles={"flex": "1"}))
        self.layout = pn.Column(
            *items,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

    def _panel_refresh(self):
        self.update_spike_venn()
        pair = self._compared_pair
        self.pair_label.object = "select a pair of units, one of each sorter" if pair is None else f"{pair[0]} vs {pair[1]}"
        venn, geometry = self.get_venn_data()
        self._panel_draw_venn(venn, geometry)
        for region, button in self.region_buttons.items():
            button.disabled = len(venn[region]) == 0
        self._panel_draw_waveforms()

    def _panel_draw_waveforms(self):
        for i, wf_data in self.iter_waveforms_data() if self.has_waveforms() else []:
            data = {"xs": [], "ys": [], "color": [], "alpha": [], "width": []}
            title = ""
            if wf_data is not None:
                times_ms, lines, title = wf_data
                for color, wfs, is_mean in lines:
                    for wf in wfs:
                        data["xs"].append(times_ms.tolist())
                        data["ys"].append(wf.tolist())
                        data["color"].append(color)
                        data["alpha"].append(1.0 if is_mean else 0.3)
                        data["width"].append(3 if is_mean else 1)
            self.waveform_sources[i].data.update(data)
            self.waveform_figures[i].title.text = title


CompareSpikesView._gui_help_txt = """
## Compare Spikes View

Spike level comparison of one pair of units, one unit of each sorter. Select a row of the
comparison unit table with two units: the comparison is computed automatically.

The Venn diagram shows the spikes found by both units (matched, within the comparison
`delta_time`), and the spikes found by only one of them. The areas are proportional to the
spike counts.

When the waveforms extension is loaded, sample waveforms of the 3 regions are plotted below,
on the extremum channel of the unit of sorter 1: sorter 1 only (left), both (middle) and
sorter 2 only (right), with the colors of the Venn diagram.
Waveforms only exist for the `random_spikes` subset, so only those spikes are plotted. The
titles tell how many of the region's spikes have waveforms (`n1` and `n2` for the units of
sorter 1 and 2 in the middle panel).

### Controls
- **left click on a region** : select the spikes of that region (they show up in the spike
  list and trace views).
- **Select {sorter 1} / Select match / Select {sorter 2}** : the same as clicking a region,
  for when a region is too thin to click on.

### Settings
- **max_waveforms** : the maximum number of waveforms plotted per unit and region.
"""
