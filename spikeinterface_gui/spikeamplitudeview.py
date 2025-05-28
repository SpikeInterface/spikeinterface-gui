import numpy as np


from .basescatterview import BaseScatterView


class SpikeAmplitudeView(BaseScatterView):
    _depend_on = ["spike_amplitudes"]
    _settings = BaseScatterView._settings + [
        {'name': 'noise_level', 'type': 'bool', 'value' : True },
        {'name': 'noise_factor', 'type': 'int', 'value' : 5 },
    ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        y_label = "Amplitude (uV)"
        spike_data = controller.spike_amplitudes
        # set noise level to False by default in panel
        if backend == 'panel':
            noise_level_settings_index = [s["name"] for s in SpikeAmplitudeView._settings].index("noise_level")
            SpikeAmplitudeView._settings[noise_level_settings_index]['value'] = False
        BaseScatterView.__init__(
            self,
            controller=controller,
            parent=parent,
            backend=backend,
            y_label=y_label,
            spike_data=spike_data,
        )

    def _qt_make_layout(self):
        super()._qt_make_layout()
        self.noise_harea = []
        if self.settings["noise_level"]:
            self._qt_add_noise_area()

    def _qt_refresh(self):
        super()._qt_refresh()
        # average noise across channels
        if self.settings["noise_level"] and len(self.noise_harea) == 0:
            self._qt_add_noise_area()
        # remove noise area if not selected
        elif not self.settings["noise_level"] and len(self.noise_harea) > 0:
            for n in self.noise_harea:
                self.plot2.removeItem(n)
            self.noise_harea = []

    def _qt_add_noise_area(self):
        import pyqtgraph as pg

        n = self.settings["noise_factor"]
        noise = np.mean(self.controller.noise_levels)
        alpha_factor = 50 / n
        for i in range(1, n + 1):
            n = self.plot2.addItem(
                pg.LinearRegionItem(values=(-i * noise, i * noise), orientation="horizontal",
                                    brush=(255, 255, 255, int(i * alpha_factor)), pen=(0, 0, 0, 0))
            )
            self.noise_harea.append(n)

    def _panel_refresh(self):
        super()._panel_refresh()
        # update noise area
        self.noise_harea = []
        if self.settings['noise_level'] and len(self.noise_harea) == 0:
            self._panel_add_noise_area()
        else:
            self.noise_harea = []

    def _panel_add_noise_area(self):
        self.noise_harea = []
        noise = np.mean(self.controller.noise_levels)
        n = self.settings['noise_factor']
        alpha_factor = 50 / n
        for i in range(1, n + 1):
            h = self.hist_fig.harea(
                y="y",
                x1="x1",
                x2="x2",
                source={
                    "y": [-i * noise, i * noise],
                    "x1": [0, 0],
                    "x2": [10_000, 10_000],
                },
                alpha=int(i * alpha_factor) / 255,  # Match Qt alpha scaling
                color="lightgray",
            )
            self.noise_harea.append(h)


SpikeAmplitudeView._gui_help_txt = """
## Spike Amplitude View

Check amplitudes of spikes across the recording time or in a histogram
comparing the distribution of ampltidues to the noise levels.

### Controls
- **select** : activate lasso selection to select individual spikes
"""
