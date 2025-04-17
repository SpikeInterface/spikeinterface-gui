from .basescatterview import BaseScatterView


class SpikeDepthView(BaseScatterView):
    _depend_on = ["spike_locations"]

    def __init__(self, controller=None, parent=None, backend="qt"):
        y_label = "Depth (um)"
        spike_data = controller.spike_depths
        BaseScatterView.__init__(
            self,
            controller=controller,
            parent=parent,
            backend=backend,
            y_label=y_label,
            spike_data=spike_data,
        )



SpikeDepthView._gui_help_txt = """
## Spike Depth View

Check deppth of spikes across the recording time or in a histogram.

### Controls
- **select** : activate lasso selection to select individual spikes
"""
