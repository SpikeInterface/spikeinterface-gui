from .basescatterview import BaseScatterView


class AmplitudeScalingsView(BaseScatterView):
    id = "amplitudescalings"
    _depend_on = ["amplitude_scalings"]

    def __init__(self, controller=None, parent=None, backend="qt"):
        y_label = "Amplitude scaling"
        spike_data = controller.amplitude_scalings

        BaseScatterView.__init__(
            self,
            controller=controller,
            parent=parent,
            backend=backend,
            y_label=y_label,
            spike_data=spike_data,
        )

    def _qt_make_layout(self):
        from .myqt import QT

        super()._qt_make_layout()

        # add split shortcut, so that it's not duplicated
        shortcut_split = QT.QShortcut(self.qt_widget)
        shortcut_split.setKey(QT.QKeySequence("ctrl+s"))
        shortcut_split.activated.connect(self.split)


AmplitudeScalingsView._gui_help_txt = """
## Amplitude Scalings View

Amplitude scalings measure the optimal scaling which should be applied to the template so that
it best matches each spike waveform.

### Controls
- **select** : activate lasso selection to select individual spikes
- **split** or **ctrl+s** : split the selected spikes into a new unit (only if one unit is visible)
"""
