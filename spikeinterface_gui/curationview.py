import json
from pathlib import Path

from .view_base import ViewBase

from spikeinterface.core.core_tools import check_json


class CurationView(ViewBase):
    id = "curation"
    _supported_backend = ["qt", "panel"]
    _need_compute = False

    def __init__(self, controller=None, parent=None, backend="qt"):
        self.active_table = "merge"
        ViewBase.__init__(self, controller=controller, parent=parent, backend=backend)

    # TODO: Cast unit ids to the correct type here
    def restore_units(self):
        if self.backend == "qt":
            unit_ids = self._qt_get_delete_table_selection()
        else:
            unit_ids = self._panel_get_delete_table_selection()
        if unit_ids is not None:
            unit_ids = [self.controller.unit_ids.dtype.type(unit_id) for unit_id in unit_ids]
            self.controller.make_manual_restore(unit_ids)
            self.notify_manual_curation_updated()
            self.refresh()

    def unmerge(self):
        if self.backend == "qt":
            merge_indices = self._qt_get_merge_table_row()
        else:
            merge_indices = self._panel_get_merge_table_row()
        if merge_indices is not None:
            self.controller.make_manual_restore_merge(merge_indices)
            self.notify_manual_curation_updated()
            self.refresh()

    def unsplit(self):
        if self.backend == "qt":
            split_indices = self._qt_get_split_table_row()
        else:
            split_indices = self._panel_get_split_table_row()
        if split_indices is not None:
            self.controller.make_manual_restore_split(split_indices)
            self.controller.set_indices_spike_selected([])
            self.notify_spike_selection_changed()
            self.notify_manual_curation_updated()
            self.refresh()

    def select_and_notify_split(self, split_unit_id):
        self.controller.set_visible_unit_ids([split_unit_id])
        self.notify_unit_visibility_changed()
        spike_inds = self.controller.get_spike_indices(split_unit_id, segment_index=None)
        active_split = [s for s in self.controller.curation_data["splits"] if s["unit_id"] == split_unit_id][0]
        split_indices = active_split["indices"][0]
        self.controller.set_indices_spike_selected(spike_inds[split_indices])
        self.notify_spike_selection_changed()

    ## Qt
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.merge_info = {}
        self.layout = QT.QVBoxLayout()

        tb = self.qt_widget.view_toolbar
        if self.controller.curation_can_be_saved():
            but = QT.QPushButton("Save in analyzer")
            tb.addWidget(but)
            but.clicked.connect(self.save_in_analyzer)

        but = QT.QPushButton("Export JSON")
        but.clicked.connect(self._qt_export_json)
        tb.addWidget(but)

        h = QT.QHBoxLayout()
        self.layout.addLayout(h)

        v = QT.QVBoxLayout()
        h.addLayout(v)
        self.table_delete = QT.QTableWidget(
            selectionMode=QT.QAbstractItemView.SingleSelection, selectionBehavior=QT.QAbstractItemView.SelectRows
        )
        v.addWidget(self.table_delete)
        self.table_delete.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table_delete.customContextMenuRequested.connect(self._qt_open_context_menu_delete)
        self.table_delete.itemSelectionChanged.connect(self._qt_on_item_selection_changed_delete)

        self.delete_menu = QT.QMenu()
        act = self.delete_menu.addAction("Restore")
        act.triggered.connect(self.restore_units)
        shortcut_restore = QT.QShortcut(self.qt_widget)
        shortcut_restore.setKey(QT.QKeySequence("ctrl+r"))
        shortcut_restore.activated.connect(self.restore_units)

        v = QT.QVBoxLayout()
        h.addLayout(v)
        self.table_merge = QT.QTableWidget(
            selectionMode=QT.QAbstractItemView.SingleSelection, selectionBehavior=QT.QAbstractItemView.SelectRows
        )
        # self.table_merge.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        v.addWidget(self.table_merge)

        self.table_merge.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table_merge.customContextMenuRequested.connect(self._qt_open_context_menu_merge)
        self.table_merge.itemSelectionChanged.connect(self._qt_on_item_selection_changed_merge)

        self.merge_menu = QT.QMenu()
        act = self.merge_menu.addAction("Remove merge")
        act.triggered.connect(self.unmerge)
        shortcut_unmerge = QT.QShortcut(self.qt_widget)
        shortcut_unmerge.setKey(QT.QKeySequence("ctrl+u"))
        shortcut_unmerge.activated.connect(self.unmerge)

        v = QT.QVBoxLayout()
        h.addLayout(v)
        self.table_split = QT.QTableWidget(
            selectionMode=QT.QAbstractItemView.SingleSelection, selectionBehavior=QT.QAbstractItemView.SelectRows
        )
        v.addWidget(self.table_split)
        self.table_split.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table_split.customContextMenuRequested.connect(self._qt_open_context_menu_split)
        self.table_split.itemSelectionChanged.connect(self._qt_on_item_selection_changed_split)
        self.split_menu = QT.QMenu()
        act = self.split_menu.addAction("Remove split")
        act.triggered.connect(self.unsplit)
        shortcut_unsplit = QT.QShortcut(self.qt_widget)
        shortcut_unsplit.setKey(QT.QKeySequence("ctrl+x"))
        shortcut_unsplit.activated.connect(self.unsplit)

    def _qt_refresh(self):
        from .myqt import QT

        # Merged
        merged_units = [m["unit_ids"] for m in self.controller.curation_data["merges"]]
        self.table_merge.clear()
        self.table_merge.setRowCount(len(merged_units))
        self.table_merge.setColumnCount(1)
        self.table_merge.setHorizontalHeaderLabels(["merges"])
        self.table_merge.setSortingEnabled(False)
        for ix, group in enumerate(merged_units):
            item = QT.QTableWidgetItem(str(group))
            item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
            self.table_merge.setItem(ix, 0, item)
        for i in range(self.table_merge.columnCount()):
            self.table_merge.resizeColumnToContents(i)

        # Removed
        removed_units = self.controller.curation_data["removed"]
        self.table_delete.clear()
        self.table_delete.setRowCount(len(removed_units))
        self.table_delete.setColumnCount(1)
        self.table_delete.setHorizontalHeaderLabels(["removed"])
        self.table_delete.setSortingEnabled(False)
        for i, unit_id in enumerate(removed_units):
            color = self.get_unit_color(unit_id)
            pix = QT.QPixmap(16, 16)
            pix.fill(color)
            icon = QT.QIcon(pix)
            item = QT.QTableWidgetItem(f"{unit_id}")
            item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
            self.table_delete.setItem(i, 0, item)
            item.setIcon(icon)
            item.unit_id = unit_id
        self.table_delete.resizeColumnToContents(0)

        # Splits
        splits = self.controller.curation_data["splits"]
        self.table_split.clear()
        self.table_split.setRowCount(len(splits))
        self.table_split.setColumnCount(1)
        self.table_split.setHorizontalHeaderLabels(["splits"])
        self.table_split.setSortingEnabled(False)
        for i, split in enumerate(splits):
            unit_id = split["unit_id"]
            num_indices = len(split["indices"][0])
            num_spikes = self.controller.num_spikes[unit_id]
            num_splits = f"({num_indices}-{num_spikes - num_indices})"
            item = QT.QTableWidgetItem(f"{unit_id} {num_splits}")
            item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
            self.table_split.setItem(i, 0, item)
            item.unit_id = unit_id
        self.table_split.resizeColumnToContents(0)

    def _qt_get_delete_table_selection(self):
        selected_items = self.table_delete.selectedItems()
        if len(selected_items) == 0:
            return None
        else:
            return [s.unit_id for s in selected_items]

    def _qt_get_merge_table_row(self):
        selected_items = self.table_merge.selectedItems()
        if len(selected_items) == 0:
            return None
        else:
            return [s.row() for s in selected_items]

    def _qt_get_split_table_row(self):
        selected_items = self.table_split.selectedItems()
        if len(selected_items) == 0:
            return None
        else:
            return [s.row() for s in selected_items]

    def _qt_open_context_menu_delete(self):
        self.delete_menu.popup(self.qt_widget.cursor().pos())

    def _qt_open_context_menu_merge(self):
        self.merge_menu.popup(self.qt_widget.cursor().pos())

    def _qt_open_context_menu_split(self):
        self.split_menu.popup(self.qt_widget.cursor().pos())

    def _qt_on_item_selection_changed_merge(self):
        if len(self.table_merge.selectedIndexes()) == 0:
            return

        self._qt_clear_selection(self.table_merge)

        dtype = self.controller.unit_ids.dtype
        ind = self.table_merge.selectedIndexes()[0].row()
        visible_unit_ids = [m["unit_ids"] for m in self.controller.curation_data["merges"]][ind]
        visible_unit_ids = [dtype.type(unit_id) for unit_id in visible_unit_ids]
        self.controller.set_visible_unit_ids(visible_unit_ids)
        self.notify_unit_visibility_changed()

    def _qt_on_item_selection_changed_split(self):
        if len(self.table_split.selectedIndexes()) == 0:
            return

        self._qt_clear_selection(self.table_split)

        dtype = self.controller.unit_ids.dtype
        ind = self.table_split.selectedIndexes()[0].row()
        split_unit_str = self.table_split.item(ind, 0).text()
        split_unit_id = dtype.type(split_unit_str.split(" ")[0])
        self.select_and_notify_split(split_unit_id)

    def _qt_on_item_selection_changed_delete(self):
        if len(self.table_delete.selectedIndexes()) == 0:
            return

        self._qt_clear_selection(self.table_delete)

        ind = self.table_delete.selectedIndexes()[0].row()
        unit_id = self.controller.curation_data["removed"][ind]
        self.controller.set_all_unit_visibility_off()
        # convert to the correct type
        unit_id = self.controller.unit_ids.dtype.type(unit_id)
        self.controller.set_visible_unit_ids([unit_id])
        self.notify_unit_visibility_changed()

    def _qt_clear_selection(self, active_table=None):
        tables = [self.table_delete, self.table_merge, self.table_split]
        for table in tables:
            if active_table is None:
                table.clearSelection()
            elif table != active_table:
                table.clearSelection()

    def _qt_on_restore_shortcut(self):
        sel_rows = self._qt_get_selected_rows()
        self._qt_delete_unit()
        if len(sel_rows) > 0:
            self.table.clearSelection()
            self.table.setCurrentCell(min(sel_rows[-1] + 1, self.table.rowCount() - 1), 0)

    def _qt_on_unit_visibility_changed(self):
        self._qt_clear_selection()

    def on_manual_curation_updated(self):
        self.refresh()

    def save_in_analyzer(self):
        self.controller.save_curation_in_analyzer()

    def _qt_export_json(self):
        from .myqt import QT

        fd = QT.QFileDialog(fileMode=QT.QFileDialog.AnyFile, acceptMode=QT.QFileDialog.AcceptSave)
        fd.setNameFilters(["JSON (*.json);"])
        fd.setDefaultSuffix("json")
        fd.setViewMode(QT.QFileDialog.Detail)
        if fd.exec_():
            json_file = Path(fd.selectedFiles()[0])
            curation_model = self.controller.construct_final_curation()
            with json_file.open("w") as f:
                f.write(curation_model.model_dump_json(indent=4))
            self.controller.current_curation_saved = True

    # PANEL
    def _panel_make_layout(self):
        import pandas as pd
        import panel as pn

        from .utils_panel import KeyboardShortcut, KeyboardShortcuts, SelectableTabulator, IFrameDetector

        pn.extension("tabulator")

        # Initialize listenet_pane as None
        self.listener_pane = None

        # Create dataframe
        delete_df = pd.DataFrame({"removed": []})
        merge_df = pd.DataFrame({"merges": []})
        split_df = pd.DataFrame({"splits": []})

        # Create tables
        self.table_delete = SelectableTabulator(
            delete_df,
            show_index=False,
            disabled=True,
            sortable=False,
            selectable=True,
            formatters={"removed": "plaintext"},
            sizing_mode="stretch_width",
            # SelectableTabulator functions
            parent_view=self,
            conditional_shortcut=self._conditional_refresh_delete,
            column_callbacks={"removed": self._panel_on_deleted_col},
        )
        self.table_merge = SelectableTabulator(
            merge_df,
            show_index=False,
            disabled=True,
            sortable=False,
            selectable=1,
            formatters={"merges": "plaintext"},
            sizing_mode="stretch_width",
            # SelectableTabulator functions
            parent_view=self,
            conditional_shortcut=self._conditional_refresh_merge,
            column_callbacks={"merges": self._panel_on_merged_col},
        )
        self.table_split = SelectableTabulator(
            split_df,
            show_index=False,
            disabled=True,
            sortable=False,
            selectable=1,
            formatters={"splits": "plaintext"},
            sizing_mode="stretch_width",
            # SelectableTabulator functions
            parent_view=self,
            conditional_shortcut=self._conditional_refresh_split,
            column_callbacks={"splits": self._panel_on_split_col},
        )

        # Watch selection changes instead of calling from column callbacks
        self.table_delete.param.watch(self._panel_on_table_selection_changed, "selection")
        self.table_merge.param.watch(self._panel_on_table_selection_changed, "selection")
        self.table_split.param.watch(self._panel_on_table_selection_changed, "selection")

        # Create buttons
        buttons_row = []
        self.save_button = None
        if self.controller.curation_can_be_saved():
            self.save_button = pn.widgets.Button(name="Save in analyzer", button_type="primary", height=30)
            self.save_button.on_click(self._panel_save_in_analyzer)
            buttons_row.append(self.save_button)

        self.download_button = pn.widgets.FileDownload(
            button_type="primary", filename="curation.json", callback=self._panel_generate_json, height=30
        )
        buttons_row.append(self.download_button)

        restore_button = pn.widgets.Button(name="Restore", button_type="primary", height=30)
        restore_button.on_click(self._panel_restore_units)

        remove_merge_button = pn.widgets.Button(name="Unmerge", button_type="primary", height=30)
        remove_merge_button.on_click(self._panel_unmerge)

        remove_split = pn.widgets.Button(name="Unsplit", button_type="primary", height=30)
        remove_split.on_click(self._panel_unsplit)

        # Create layout
        self.buttons_save = pn.Row(
            *buttons_row,
            sizing_mode="stretch_width",
        )

        buttons_curate = pn.Row(
            restore_button,
            remove_merge_button,
            remove_split,
            sizing_mode="stretch_width",
        )

        # shortcuts
        shortcuts = [
            KeyboardShortcut(name="restore", key="r", ctrlKey=True),
            KeyboardShortcut(name="unmerge", key="u", ctrlKey=True),
            KeyboardShortcut(name="unsplit", key="x", ctrlKey=True),
        ]
        shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        shortcuts_component.on_msg(self._panel_handle_shortcut)

        # Create main layout with proper sizing
        sections = pn.Row(self.table_delete, self.table_merge, self.table_split, sizing_mode="stretch_width")
        self.layout = pn.Column(
            self.buttons_save, buttons_curate, sections, shortcuts_component, scroll=True, sizing_mode="stretch_both"
        )

        self.iframe_detector = IFrameDetector()
        self.iframe_detector.param.watch(self._panel_on_iframe_change, "in_iframe")
        self.layout.append(self.iframe_detector)

    def _panel_refresh(self):
        import pandas as pd

        ## deleted
        removed_units = self.controller.curation_data["removed"]
        removed_units = [str(unit_id) for unit_id in removed_units]
        df = pd.DataFrame({"removed": removed_units})
        self.table_delete.value = df
        self.table_delete.selection = []

        # Merged
        merged_units = [m["unit_ids"] for m in self.controller.curation_data["merges"]]
        # for visualization, we make all row entries strings
        merged_units_str = []
        for group in merged_units:
            # convert to string
            group = [str(unit_id) for unit_id in group]
            merged_units_str.append(" - ".join(group))
        df = pd.DataFrame({"merges": merged_units_str})
        self.table_merge.value = df
        self.table_merge.selection = []

        # Splits
        split_units_str = []
        num_spikes = self.controller.num_spikes
        for split in self.controller.curation_data["splits"]:
            unit_id = split["unit_id"]
            num_indices = len(split["indices"][0])
            num_splits = f"({num_indices}-{num_spikes[unit_id] - num_indices})"
            split_units_str.append(f"{unit_id} {num_splits}")
        df = pd.DataFrame({"splits": split_units_str})
        self.table_split.value = df
        self.table_split.selection = []

        if not self.controller.current_curation_saved:
            self.ensure_save_warning_message()
        else:
            self.ensure_no_message()

    def ensure_save_warning_message(self):

        if self.layout[0].name == "curation_save_warning":
            return

        import panel as pn

        alert_markdown = pn.pane.Markdown(
            f"""⚠️⚠️⚠️ Your curation is not saved""",
            hard_line_break=True,
            styles={"color": "red", "font-size": "16px"},
            name="curation_save_warning",
        )

        self.layout.insert(0, alert_markdown)

    def ensure_no_message(self):
        if self.layout[0].name == "curation_save_warning":
            self.layout.pop(0)

    def _panel_update_unit_visibility(self, event):
        unit_dtype = self.controller.unit_ids.dtype
        if self.active_table == "delete":
            visible_unit_ids = self.table_delete.value["removed"].values[self.table_delete.selection].tolist()
            visible_unit_ids = [unit_dtype.type(unit_id) for unit_id in visible_unit_ids]
            self.controller.set_visible_unit_ids(visible_unit_ids)
            self.notify_unit_visibility_changed()
        elif self.active_table == "merge":
            merge_groups = self.table_merge.value["merges"].values[self.table_merge.selection].tolist()
            # self.controller.set_all_unit_visibility_off()
            visible_unit_ids = []
            for merge_group in merge_groups:
                merge_unit_ids = [unit_dtype.type(unit_id) for unit_id in merge_group.split(" - ")]
                visible_unit_ids.extend(merge_unit_ids)
            self.controller.set_visible_unit_ids(visible_unit_ids)
            self.notify_unit_visibility_changed()
        elif self.active_table == "split":
            # this is handled by the table callback to properly set the selected spikes, so we do nothing here
            pass


    def _panel_restore_units(self, event):
        self.restore_units()

    def _panel_unmerge(self, event):
        self.unmerge()

    def _panel_unsplit(self, event):
        self.unsplit()

    def _panel_save_in_analyzer(self, event):
        self.save_in_analyzer()
        self.refresh()

    def _panel_generate_json(self):
        # Get the path from the text input
        export_path = Path("curation.json")
        # Save the JSON file
        curation_model = self.controller.construct_final_curation()
        with export_path.open("w") as f:
            f.write(curation_model.model_dump_json(indent=4))

        self.controller.current_curation_saved = True

        self.refresh()

        return export_path

    def _panel_submit_to_parent(self, event):        
        """Send the curation data to the parent window"""
        import time

        # Get the curation data and convert it to a JSON string
        curation_model = self.controller.construct_final_curation()
        curation_data = curation_model.model_dump_json()
        # Trigger the JavaScript function via the TextInput
        # Update the value to trigger the jscallback
        self.submit_trigger.value = curation_data + f"_{int(time.time() * 1000)}"

        # Submitting to parent is a way to "save" the curation (the parent can handle it)
        self.controller.current_curation_saved = True
        self.ensure_no_message()
        print(f"Curation data sent to parent app!")

    def _panel_set_curation_data(self, event):
        """
        Handler for PostMessageListener.on_msg.

        event.data is whatever the JS side passed to model.send_msg(...).
        Expected shape:
        {
            "payload": {"type": "curation-data", "data": <curation_dict>},
        }
        """
        msg = event.data
        payload = (msg or {}).get("payload", {})
        curation_data = payload.get("data", None)

        if curation_data is None:
            print("Received message without curation data:", msg)
            return

        # Optional: validate basic structure
        if not isinstance(curation_data, dict):
            print("Invalid curation_data type:", type(curation_data), curation_data)
            return

        self.controller.set_curation_data(curation_data)
        self.refresh()

    def _panel_on_iframe_change(self, event):
        import panel as pn

        in_iframe = event.new
        print(f"CurationView detected iframe mode: {in_iframe}")
        if in_iframe:
            # Remove save in analyzer button and add submit to parent button
            self.submit_button = pn.widgets.Button(name="Submit to parent", button_type="primary", height=30)
            self.submit_button.on_click(self._panel_submit_to_parent)

            self.buttons_save = pn.Row(
                self.submit_button,
                self.download_button,
                sizing_mode="stretch_width",
            )
            self.layout[0] = self.buttons_save
            
            # Create objects to submit and listen
            self.submit_trigger = pn.widgets.TextInput(value="", visible=False)
            # Add JavaScript callback that triggers when the TextInput value changes
            self.submit_trigger.jscallback(
                value="""
                // Extract just the JSON data (remove timestamp suffix)
                const fullValue = cb_obj.value;
                const lastUnderscore = fullValue.lastIndexOf('_');
                const dataStr = lastUnderscore > 0 ? fullValue.substring(0, lastUnderscore) : fullValue;

                if (dataStr && dataStr.length > 0) {
                    try {
                        const data = JSON.parse(dataStr);
                        console.log('Sending data to parent:', data);
                        parent.postMessage({
                                type: 'panel-data',
                                data: data
                            },
                        '*');
                        console.log('Data sent successfully to parent window');
                    } catch (error) {
                        console.error('Error sending data to parent:', error);
                    }
                }
                """
            )
            self.layout.append(self.submit_trigger)

    def _panel_get_delete_table_selection(self):
        selected_items = self.table_delete.selection
        if len(selected_items) == 0:
            return None
        else:
            return self.table_delete.value["removed"].values[selected_items].tolist()

    def _panel_get_merge_table_row(self):
        selected_items = self.table_merge.selection
        if len(selected_items) == 0:
            return None
        else:
            return selected_items

    def _panel_get_split_table_row(self):
        selected_items = self.table_split.selection
        if len(selected_items) == 0:
            return None
        else:
            return selected_items

    def _panel_handle_shortcut(self, event):
        if event.data == "restore":
            self.restore_units()
        elif event.data == "unmerge":
            self.unmerge()
        elif event.data == "unsplit":
            self.unsplit()

    def _panel_on_unit_visibility_changed(self):
        for table in [self.table_delete, self.table_merge, self.table_split]:
            table.selection = []
        self.active_table = None

    def _panel_on_deleted_col(self, row):
        self.active_table = "delete"

    def _panel_on_merged_col(self, row):
        self.active_table = "merge"

    def _panel_on_split_col(self, row):
        self.active_table = "split"

    def _panel_on_table_selection_changed(self, event):
        """
        Unified handler for all table selection changes.
        Determines which table was changed and updates visibility accordingly.
        """
        import panel as pn

        # Determine which table triggered the change
        if self.active_table == "delete" and len(self.table_delete.selection) > 0:
            self.table_merge.selection = []
            self.table_split.selection = []
            # Defer to avoid nested Bokeh callbacks (especially from ctrl+click)
            pn.state.execute(lambda: self._panel_update_unit_visibility(None), schedule=True)
        elif self.active_table == "merge" and len(self.table_merge.selection) > 0:
            self.table_delete.selection = []
            self.table_split.selection = []
            # Defer to avoid nested Bokeh callbacks (especially from ctrl+click)
            pn.state.execute(lambda: self._panel_update_unit_visibility(None), schedule=True)
        elif self.active_table == "split" and len(self.table_split.selection) > 0:
            self.table_delete.selection = []
            self.table_merge.selection = []
            # Handle split specially (sets selected spikes) - also deferred
            def handle_split():
                split_unit_str = self.table_split.value["splits"].values[self.table_split.selection[0]]
                split_unit_id = self.controller.unit_ids.dtype.type(split_unit_str.split(" ")[0])
                self.select_and_notify_split(split_unit_id)
            # Defer to avoid nested Bokeh callbacks (especially from ctrl+click)
            pn.state.execute(handle_split, schedule=True)
        elif len(self.table_delete.selection) == 0 and len(self.table_merge.selection) == 0 and len(self.table_split.selection) == 0:
            # All tables are cleared
            self.active_table = None


    def _conditional_refresh_merge(self):
        # Check if the view is active before refreshing
        if self.is_view_active() and self.active_table == "merge":
            return True
        else:
            return False

    def _conditional_refresh_delete(self):
        # Check if the view is active before refreshing
        if self.is_view_active() and self.active_table == "delete":
            return True
        else:
            return False

    def _conditional_refresh_split(self):
        # Check if the view is active before refreshing
        if self.is_view_active() and self.active_table == "split":
            return True
        else:
            return False


CurationView._gui_help_txt = """
## Curation View

The curation view shows the current status of the curation process and allows the user to manually visualize,
revert, and export the curation data.

### Controls
- **save in analyzer**: Save the current curation state in the analyzer.
- **export/download JSON**: Export the current curation state to a JSON file.
- **restore**: Restore the selected unit from the deleted units table.
- **unmerge**: Unmerge the selected merges from the merged units table.
- **unsplit**: Unsplit the selected split groups from the split units table.
- **submit to parent**: Submit the current curation state to the parent window (for use in web applications).
- **press 'ctrl+r'**: Restore the selected units from the deleted units table.
- **press 'ctrl+u'**: Unmerge the selected merges from the merged units table.
- **press 'ctrl+x'**: Unsplit the selected split groups from the split units table.

### Note
When setting the `iframe_mode` setting to `True` using the `user_settings=dict(curation=dict(iframe_mode=True))`,
the GUI is expected to be used inside an iframe. In this mode, the curation view will include a "Submit to parent" 
button that, when clicked, will send the current curation data to the parent window.
In this mode, bi-directional communication is established between the GUI and the parent window using the `postMessage`
API. The GUI listens for incoming messages of this expected shape:

```
{
    "payload": {"type": "curation-data", "data": <curation_dict>},
}
```
"""
