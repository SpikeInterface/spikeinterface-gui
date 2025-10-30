import time
from contextlib import contextmanager

class ViewBase:
    _supported_backend = []
    _need_compute = False
    _settings = None
    _gui_help_txt = "The help for this view is not done yet"
    _depend_on = None

    def __init__(self, controller=None, parent=None, backend="qt"):

        self.backend = backend
        self.controller = controller
        # this is used for panel
        self._panel_view_is_visible = True
        self._panel_view_is_active = False

        if self.backend == "qt":
            # For QT the parent is the **widget**
            from .backend_qt import SignalNotifier, create_settings, listen_setting_changes

            make_layout = self._qt_make_layout
            self.qt_widget = parent
            if self._settings is not None:
                create_settings(self, parent=parent)
            self.notifier = SignalNotifier(parent=self.qt_widget, view=self)

        elif self.backend == "panel":
            import panel as pn
            from .backend_panel import SignalNotifier, create_settings, listen_setting_changes

            make_layout = self._panel_make_layout
            if self._settings is not None:
                create_settings(self)
            self.notifier = SignalNotifier(view=self)
            self.busy = pn.indicators.LoadingSpinner(value=True, size=20, name='busy...')

        make_layout()
        if self._settings is not None:
            listen_setting_changes(self)

        self.controller.declare_a_view(self)

    def notify_spike_selection_changed(self):
        self.notifier.notify_spike_selection_changed()

    def notify_unit_visibility_changed(self):
        if self.controller.main_settings["color_mode"] in ("color_by_visibility", "color_only_visible"):
            # in the mode color change dynamically but without notify to avoid double refresh
            self.controller.refresh_colors()

        self.controller.update_visible_spikes()
        self.notifier.notify_unit_visibility_changed()

    def notify_channel_visibility_changed(self):
        self.notifier.notify_channel_visibility_changed()

    def notify_manual_curation_updated(self):
        self.notifier.notify_manual_curation_updated()

    def notify_time_info_updated(self):
        self.notifier.notify_time_info_updated()

    def notify_use_times_updated(self):
        self.notifier.notify_use_times_updated()

    def notify_active_view_updated(self):
        # this is used for panel
        if self.backend == "panel":
            self.notifier.notify_active_view_updated()

    def notify_unit_color_changed(self):
        self.notifier.notify_unit_color_changed()

    def on_settings_changed(self, *params):
        # what to do when one settings is changed
        # optionally views can implement custom method
        # but the general case is to refesh
        if self.backend == "qt" and hasattr(self, "_qt_on_settings_changed"):
            return self._qt_on_settings_changed()
        elif self.backend == "panel" and hasattr(self, "_panel_on_settings_changed"):
            return self._panel_on_settings_changed()
        elif hasattr(self, "_on_settings_changed"):
            self._on_settings_changed()
        else:
            self.refresh()

    def is_view_visible(self):
        if self.backend == "qt":
            # a widget is visible even is it is hidden under another tab!! TODO fix this
            return self.qt_widget.isVisible()
        elif self.backend == "panel":
            return self._panel_view_is_visible

    def is_view_active(self):
        if self.backend == "qt":
            return True
        elif self.backend == "panel":
            return self._panel_view_is_active

    def refresh(self, **kwargs):
        if self.controller.verbose:
            t0 = time.perf_counter()
        if not self.is_view_visible():
            return
        self._refresh(**kwargs)
        if self.controller.verbose:
            t1 = time.perf_counter()
            print(f"Refresh {self.__class__.__name__} took {t1 - t0:.3f} seconds", flush=True)

    def compute(self, event=None):
        with self.busy_cursor():
            self._compute()
        self.refresh()

    def _compute(self):
        pass

    def _refresh(self, **kwargs):
        if self.backend == "qt":
            self._qt_refresh(**kwargs)
        elif self.backend == "panel":
            self._panel_refresh(**kwargs)

    def warning(self, warning_msg):
        if self.backend == "qt":
            self._qt_insert_warning(warning_msg)
        elif self.backend == "panel":
            self._panel_insert_warning(warning_msg)



    def continue_from_user(self, warning_msg, action, *args):
        """Display a warning and execute risky action only if user continues.

        Params
        -------
        warning_msg : str
            The warning message to display
        action : function
            Function to execute if user chooses to continue
        *args : tuple
            Arguments to pass to action

        For Qt: Shows modal dialog, executes action if Continue is clicked
        For Panel: Shows dialog with callback, executes action in callback
        """
        if self.backend == "qt":
            # Qt: synchronous approach
            if self._qt_insert_warning_with_choice(warning_msg):
                action(*args)
        elif self.backend == "panel":
            # Panel: asynchronous approach with callback
            self._panel_insert_warning_with_choice(warning_msg, action, *args)

    def get_unit_color(self, unit_id):
        if self.backend == "qt":
            from .myqt import QT

            # cache qcolors in the controller
            if not hasattr(self.controller, "_cached_qcolors"):
                self.controller._cached_qcolors = {}
            if unit_id not in self.controller._cached_qcolors:
                color = self.controller.get_unit_color(unit_id)
                r, g, b, a = color
                qcolor = QT.QColor(int(r * 255), int(g * 255), int(b * 255))
                self.controller._cached_qcolors[unit_id] = qcolor

            return self.controller._cached_qcolors[unit_id]

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
        # print(f"on_unit_visibility_changed {self.__class__.__name__} visible{self.is_view_visible()}", flush=True)
        if not self.is_view_visible():
            return
        if self.backend == "qt":
            self._qt_on_unit_visibility_changed()
        elif self.backend == "panel":
            self._panel_on_unit_visibility_changed()

    def on_channel_visibility_changed(self):
        # print(f"on_channel_visibility_changed {self.__class__.__name__} visible{self.is_view_visible()}", flush=True)
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

    def on_time_info_updated(self):
        if self.backend == "qt":
            self._qt_on_time_info_updated()
        elif self.backend == "panel":
            self._panel_on_time_info_updated()

    def on_use_times_updated(self):
        if self.backend == "qt":
            self._qt_on_use_times_updated()
        elif self.backend == "panel":
            self._panel_on_use_times_updated()

    def on_unit_color_changed(self):
        if self.backend == "qt":
            self._qt_on_unit_color_changed()
        elif self.backend == "panel":
            self._panel_on_unit_color_changed()

    def busy_cursor(self):
        if self.backend == "qt":
            return self._qt_busy_cursor()
        elif self.backend == "panel":
            return self._panel_busy_cursor()
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    ## Zone to be done per layout ##

    ## QT ##
    def _qt_make_layout(self):
        raise NotImplementedError

    def _qt_refresh(self):
        raise (NotImplementedError)

    def _qt_on_spike_selection_changed(self):
        pass

    def _qt_on_unit_visibility_changed(self):
        # most veiw need a refresh
        self.refresh()

    def _qt_on_channel_visibility_changed(self):
        pass

    def _qt_on_manual_curation_updated(self):
        pass

    def _qt_on_time_info_updated(self):
        pass

    def _qt_on_use_times_updated(self):
        pass

    def _qt_on_unit_color_changed(self):
        self.refresh()

    def _qt_insert_warning(self, warning_msg):
        from .myqt import QT

        alert = QT.QMessageBox(QT.QMessageBox.Warning, "Warning", warning_msg, parent=self.qt_widget)
        alert.setStandardButtons(QT.QMessageBox.Ok)
        alert.exec_()

    def _qt_insert_warning_with_choice(self, warning_msg):
        from .myqt import QT

        alert = QT.QMessageBox(QT.QMessageBox.Warning, "Warning", warning_msg, parent=self.qt_widget)
        alert.setStandardButtons(QT.QMessageBox.Cancel | QT.QMessageBox.Yes)
        alert.setDefaultButton(QT.QMessageBox.Cancel)

        # Set button text
        alert.button(QT.QMessageBox.Yes).setText("Continue")
        alert.button(QT.QMessageBox.Cancel).setText("Cancel")

        result = alert.exec_()
        return result == QT.QMessageBox.Yes

    @contextmanager
    def _qt_busy_cursor(self):
        from .myqt import QT, QtWidgets
        QtWidgets.QApplication.setOverrideCursor(QT.WaitCursor)
        try:
            yield
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()


    ## PANEL ##
    def _panel_make_layout(self):
        raise NotImplementedError

    def _panel_refresh(self):
        raise (NotImplementedError)

    def _panel_on_spike_selection_changed(self):
        pass

    def _panel_on_unit_visibility_changed(self):
        # most veiw need a refresh
        self.refresh()

    def _panel_on_channel_visibility_changed(self):
        pass

    def _panel_on_manual_curation_updated(self):
        pass

    def _panel_on_time_info_updated(self):
        pass

    def _panel_use_times_updated(self):
        pass

    def _panel_on_unit_color_changed(self):
        self.refresh()

    def _panel_insert_warning(self, warning_msg):
        import panel as pn

        alert_markdown = pn.pane.Markdown(
            f"""⚠️⚠️⚠️
            {warning_msg}""",
            hard_line_break=True,
            styles={"color": "red", "font-size": "16px"},
        )

        close_button = pn.widgets.Button(name="Close", button_type="light")
        close_button.on_click(self._panel_clear_warning)
        row = pn.Column(alert_markdown, close_button, sizing_mode="stretch_width")
        self.layout.insert(0, row)

    def _panel_insert_warning_with_choice(self, warning_msg, continue_callback, *args):
        """Callback-based approach for Panel (recommended)"""
        import panel as pn

        # Store callback and args for later use
        self._panel_continue_callback = continue_callback
        self._panel_continue_args = args

        alert_markdown = pn.pane.Markdown(
            f"""⚠️⚠️⚠️
            {warning_msg}
            """,
            hard_line_break=True,
            styles={"color": "red", "font-size": "16px", "text-align": "center"},
        )

        continue_button = pn.widgets.Button(name="Continue", button_type="primary", width=100)
        cancel_button = pn.widgets.Button(name="Cancel", button_type="light", width=100)

        continue_button.on_click(self._panel_continue_choice_callback)
        cancel_button.on_click(self._panel_cancel_choice_callback)

        buttons_row = pn.Row(pn.Spacer(), continue_button, cancel_button, pn.Spacer(), sizing_mode="stretch_width")
        warning_row = pn.Column(
            alert_markdown,
            buttons_row,
            styles={"background": "#fff3cd", "border": "1px solid #ffeaa7", "padding": "15px", "border-radius": "5px"},
            sizing_mode="stretch_width",
        )
        self.layout.insert(0, warning_row)

    def _panel_continue_choice_callback(self, event):
        """Handler for callback-based approach"""
        # Remove the warning dialog
        try:
            self.layout.pop(0)
        except:
            pass

        # Execute the risky action callback with args
        if hasattr(self, "_panel_continue_callback") and self._panel_continue_callback is not None:
            try:
                args = getattr(self, "_panel_continue_args", ())
                self._panel_continue_callback(*args)
            except Exception as e:
                print(f"Error executing continue callback: {e}")

    def _panel_cancel_choice_callback(self, event):
        """Handler for callback-based approach"""
        # Remove the warning dialog
        try:
            self.layout.pop(0)
        except:
            pass
        # Do nothing on cancel - just remove the dialog

    def _panel_clear_warning(self, event):
        self.layout.pop(0)

    @contextmanager
    def _panel_busy_cursor(self):
        self.layout.insert(0, self.busy)
        try:
            yield
        finally:
            self.layout.pop(0)
