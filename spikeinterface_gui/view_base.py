import time

class ViewBase():
    _supported_backend = []
    _need_compute = False
    _settings = None
    _gui_help_txt = "The help for this view is not done yet"
    _depend_on = None
    
    def __init__(self, controller=None, parent=None, backend="qt"):

        self.backend = backend
        self.controller = controller
        # this is used for panel
        self.is_visible = True

        if self.backend == "qt":
            # For QT the parent is the **widget**
            from .backend_qt import SignalNotifier, create_settings, listen_setting_changes
            make_layout = self._qt_make_layout
            self.qt_widget = parent
            settings_kwargs = {"parent": parent}
        elif self.backend == "panel":
            from .backend_panel import SignalNotifier, create_settings, listen_setting_changes
            make_layout = self._panel_make_layout
            settings_kwargs = {}

        self.notifier = SignalNotifier(parent=self.qt_widget, view=self)
        if self._settings is not None:
            create_settings(self, **settings_kwargs)
        make_layout()
        if self._settings is not None:
            listen_setting_changes(self)

        self.controller.declare_a_view(self)

    def notify_spike_selection_changed(self):
        self.notifier.notify_spike_selection_changed()

    def notify_unit_visibility_changed(self):
        self.controller.update_visible_spikes()
        self.notifier.notify_unit_visibility_changed()

    def notify_channel_visibility_changed(self):
        self.notifier.notify_channel_visibility_changed()

    def notify_manual_curation_updated(self):
        self.notifier.notify_manual_curation_updated()

    
    def on_settings_changed(self, *params):
        # what to do when one settings is changed
        # optionally views can implement custom method
        # but the general case is to refesh
        if self.backend == "qt" and hasattr(self, '_qt_on_settings_changed'):
            return self._qt_on_settings_changed()
        elif self.backend == "panel" and hasattr(self, '_panel_on_settings_changed'):
            return self._panel_on_settings_changed()
        elif  hasattr(self, '_on_settings_changed'):
            self._on_settings_changed()
        else:
            self.refresh()

    def is_view_visible(self):
        print('ViewBase.is_view_visible', self.qt_widget.isVisible(), self.__class__.__name__)
        if self.backend == "qt":
            return self.qt_widget.isVisible()
        elif self.backend == "panel":
            return self.is_visible
    
    def refresh(self):
        t_start = time.perf_counter()
        if not self.is_view_visible():
            return
        self._refresh()
        t_end = time.perf_counter()
        print(f"Refresh {self.__class__.__name__} took {t_end - t_start:.3f} seconds", flush=True)

    def compute(self, event=None):
        self._compute()
        self.refresh()

    def _compute(self):
        pass

    def _refresh(self):
        if self.backend == "qt":
            self._qt_refresh()
        elif self.backend == "panel":
            self._panel_refresh()
    
    def get_unit_color(self, unit_id):
        if self.backend == "qt":
            from .myqt import QT
            # cache qcolors in the controller
            if not hasattr(self.controller, "_cached_qcolors"):
                self._cached_qcolors = {}
            if unit_id not in self._cached_qcolors:
                color = self.controller.get_unit_color(unit_id)
                r, g, b, a = color
                qcolor = QT.QColor(int(r*255), int(g*255), int(b*255))
                self._cached_qcolors[unit_id] = qcolor

            return self._cached_qcolors[unit_id]

        elif self.backend == "panel":
            import matplotlib
            color = self.controller.get_unit_color(unit_id)
            html_color = matplotlib.colors.rgb2hex(color, keep_alpha=True)
            return html_color

    # Default behavior for all views : this can be changed view by view for perfs reaons
    def on_spike_selection_changed(self):
        if not self.is_view_visible():
            return
        if self.backend == "qt":
            self._qt_on_spike_selection_changed()
        elif self.backend == "panel":
            self._panel_on_spike_selection_changed()
        

    def on_unit_visibility_changed(self):

        print(f"on_unit_visibility_changed {self.__class__.__name__} visible{self.is_view_visible()}", flush=True)
        if not self.is_view_visible():
            return
        if self.backend == "qt":
            self._qt_on_unit_visibility_changed()
        elif self.backend == "panel":
            self._panel_on_unit_visibility_changed()

    
    def on_channel_visibility_changed(self):
        print(f"on_channel_visibility_changed {self.__class__.__name__} visible{self.is_view_visible()}", flush=True)
        if not self.is_view_visible():
            return
        if self.backend == "qt":
            self._qt_on_channel_visibility_changed()
        elif self.backend == "panel":
            self._panel_on_channel_visibility_changed()


    def on_manual_curation_updated(self):
        if not self.is_view_visible():
            return
        if self.backend == "qt":
            self._qt_on_manual_curation_updated()
        elif self.backend == "panel":
            self._panel_on_manual_curation_updated()


    ## Zone to be done per layout ##

    ## QT ##
    def _qt_make_layout(self):
        raise NotImplementedError

    def _qt_refresh(self):
        raise(NotImplementedError)

    def _qt_on_spike_selection_changed(self):
        pass

    def _qt_on_unit_visibility_changed(self):
        # most veiw need a refresh
        self.refresh()
    
    def _qt_on_channel_visibility_changed(self):
        pass

    def _qt_on_manual_curation_updated(self):
        pass

    ## PANEL ##
    def _panel_make_layout(self):
        raise NotImplementedError

    def _panel_refresh(self):
        raise(NotImplementedError)

    def _panel_on_spike_selection_changed(self):
        pass

    def _panel_on_unit_visibility_changed(self):
        # most veiw need a refresh
        self.refresh()
    
    def _panel_on_channel_visibility_changed(self):
        pass

    def _panel_on_manual_curation_updated(self):
        pass
