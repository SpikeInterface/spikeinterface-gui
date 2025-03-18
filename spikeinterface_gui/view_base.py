

class ViewBase():
    _supported_backend = []
    _need_compute = False
    _settings = None
    _gui_help_txt = "The help for this view is not done yet"
    _depend_on = None
    
    def __init__(self, controller=None, parent=None,  backend="qt"):


        self.backend = backend
        self.controller = controller

        if self.backend == "qt":
            # For QT the parent is the **widget**
            from .backend_qt import SignalNotifyer, create_settings
            self.qt_widget = parent
            self.notifyer = SignalNotifyer(parent=parent)
            if self._settings is not None:
                create_settings(self, parent)
            self._make_layout_qt()

        elif self.backend == "panel":
            from .backend_panel import SignalNotifyer, create_settings
            self.notifyer = SignalNotifyer(parent=parent)
            if self._settings is not None:
                create_settings(self)
            self._make_layout_panel()

        self.controller.declare_a_view(self)

    def notify_spike_selection_changed(self):
        self.notifyer.notify_spike_selection_changed()

    def notify_unit_visibility_changed(self):
        self.notifyer.notify_unit_visibility_changed()

    def notify_channel_visibility_changed(self):
        self.notifyer.notify_channel_visibility_changed()

    def notify_manual_curation_updated(self):
        self.notifyer.notify_manual_curation_updated()

    # what to do when one settings is changed
    def on_settings_changed(self, *params):
        # print("on_settings_changed", type(params))
        # NOte param is either from panel or pyqtgraph
        self.refresh()

    def is_view_visible(self):
        if self.backend == "qt":
            return self.qt_widget.isVisible()
        elif self.backend == "panel":
            return True
    
    def refresh(self):
        if not self.is_view_visible():
            return
        self._refresh()

    def _refresh(self):
        if self.backend == "qt":
            self._refresh_qt()
        elif self.backend == "panel":
            self._refresh_panel()
    
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

    # def open_settings(self):
    #     NON mauvaise idée
    #     if self.backend == "qt":
    #         if not self.tree_settings.isVisible():
    #             self.tree_settings.show()
    #         else:
    #             self.tree_settings.hide()

    # def open_help(self):
    #     but = self.sender()
    #     QT.QToolTip.showText(but.mapToGlobal(QT.QPoint()),self._gui_help_txt, but)
    
    # Default behavior for all views : this can be changed view by view for perfs reaons    
    def on_spike_selection_changed(self):
        if self.backend == "qt":
            self._on_spike_selection_changed_qt()
        elif self.backend == "panel":
            self._on_spike_selection_changed_panel()
        

    def on_unit_visibility_changed(self):
        if self.backend == "qt":
            self._on_unit_visibility_changed_qt()
        elif self.backend == "panel":
            self._on_unit_visibility_changed_panel()

    
    def on_channel_visibility_changed(self):
        if self.backend == "qt":
            self._on_channel_visibility_changed_qt()
        elif self.backend == "panel":
            self._on_channel_visibility_changed_panel()


    def on_manual_curation_updated(self):
        if self.backend == "qt":
            self._on_manual_curation_updated_qt()
        elif self.backend == "panel":
            self._on_manual_curation_updated_panel()


    ## Zone to be done per layout ##

    ## QT ##
    def _make_layout_qt(self):
        raise NotImplementedError

    def _refresh_qt(self):
        raise(NotImplementedError)

    def _on_spike_selection_changed_qt(self):
        pass

    def _on_unit_visibility_changed_qt(self):
        # most veiw need a refresh
        self.refresh()
    
    def _on_channel_visibility_changed_qt(self):
        pass

    def _on_manual_curation_updated_qt(self):
        pass

    ## PANEL ##
    def _make_layout_panel(self):
        raise NotImplementedError

    def _refresh_panel(self):
        raise(NotImplementedError)

    def _on_spike_selection_changed_panel(self):
        pass

    def _on_unit_visibility_changed_panel(self):
        # most veiw need a refresh
        self.refresh()
    
    def _on_channel_visibility_changed_panel(self):
        pass

    def _on_manual_curation_updated_panel(self):
        pass
