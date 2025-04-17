import numpy as np


from .basescatterview import BaseScatterView


# TODO alessio : handle lasso


class SpikeAmplitudeView(BaseScatterView):
    _depend_on = ["spike_amplitudes"]
    _settings = BaseScatterView._settings + [
        {'name': 'noise_level', 'type': 'bool', 'value' : True },
        {'name': 'noise_factor', 'type': 'int', 'value' : 5 },
    ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        y_label = "Amplitude (uV)"
        spike_data = controller.spike_amplitudes
        BaseScatterView.__init__(
            self,
            controller=controller,
            parent=parent,
            backend=backend,
            y_label=y_label,
            spike_data=spike_data,
        )

    def _qt_refresh(self):
        import pyqtgraph as pg
        
        super()._qt_refresh()
        # average noise across channels
        if self.settings["noise_level"] and self.controller.has_extension("noise_levels"):
            n = self.settings["noise_factor"]
            noise = np.mean(self.controller.noise_levels)
            alpha_factor = 50 / n
            for i in range(1, n + 1):
                self.plot2.addItem(
                    pg.LinearRegionItem(values=(-i * noise, i * noise), orientation="horizontal",
                                        brush=(255, 255, 255, int(i * alpha_factor)), pen=(0, 0, 0, 0))
                )

    def _panel_refresh(self):
        super()._panel_refresh()
        if self.settings['noise_level']:
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
                        "x2": [self._max_count, self._max_count],
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
