from .basescatterview import BaseScatterView


class AmplitudeScalingsView(BaseScatterView):
    id = "amplitudescalings"
    _depend_on = ["amplitude_scalings"]

    def __init__(self, controller=None, parent=None, backend="qt"):
        y_label = "Amplitude scaling"
        spike_data = controller.amplitude_scalings

        # Overwrite "range_type", "range_min", and "range_max"so that default range is 0 - 2
        for setting in AmplitudeScalingsView._settings:
            if setting['name'] == 'range_type':
                setting['value'] = 'absolute'
            elif setting['name'] == 'range_min':
                setting['value'] = 0.0
            elif setting['name'] == 'range_max':
                setting['value'] = 2.0

        BaseScatterView.__init__(
            self,
            controller=controller,
            parent=parent,
            backend=backend,
            y_label=y_label,
            spike_data=spike_data,
        )


AmplitudeScalingsView._gui_help_txt = """
## Amplitude Scalings View

Amplitude scalings measure the optimal scaling which should be applied to the template so that
it best matches each spike waveform.

### Controls
- **select** : activate lasso selection to select individual spikes
- **split** or **ctrl+s** : split the selected spikes into a new unit (only if one unit is visible)
"""
