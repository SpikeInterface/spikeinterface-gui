import json
from pathlib import Path

from .view_base import ViewBase

from spikeinterface.core.core_tools import check_json




class CurationView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _need_compute = False

    def __init__(self, controller=None, parent=None, backend="qt"):
        self.active_table = "merge"
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    # TODO: Cast unit ids to the correct type here
    def restore_units(self):
        if self.backend == 'qt':
            unit_ids = self._qt_get_delete_table_selection()
        else:
            unit_ids = self._panel_get_delete_table_selection()
        if unit_ids is not None:
            unit_ids = [self.controller.unit_ids.dtype.type(unit_id) for unit_id in unit_ids]
            self.controller.make_manual_restore(unit_ids)
            self.notify_manual_curation_updated()
            self.refresh()

    def unmerge_groups(self):
        if self.backend == 'qt':
            merge_indices = self._qt_get_merge_table_row()
        else:
            merge_indices = self._panel_get_merge_table_row()
        if merge_indices is not None:
            self.controller.make_manual_restore_merge(merge_indices)
            self.notify_manual_curation_updated()
            self.refresh()

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
        v.addWidget(QT.QLabel("<b>Merges</b>"))
        self.table_merge = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        # self.table_merge.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        v.addWidget(self.table_merge)

        self.table_merge.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table_merge.customContextMenuRequested.connect(self._qt_open_context_menu_merge)
        self.table_merge.itemSelectionChanged.connect(self._qt_on_item_selection_changed_merge)

        self.merge_menu = QT.QMenu()
        act = self.merge_menu.addAction('Remove merge group')
        act.triggered.connect(self.unmerge_groups)
        shortcut_unmerge = QT.QShortcut(self.qt_widget)
        shortcut_unmerge.setKey(QT.QKeySequence("ctrl+u"))
        shortcut_unmerge.activated.connect(self.unmerge_groups)


        v = QT.QVBoxLayout()
        h.addLayout(v)
        v.addWidget(QT.QLabel("<b>Deleted</b>"))
        self.table_delete = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        v.addWidget(self.table_delete)
        self.table_delete.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table_delete.customContextMenuRequested.connect(self._qt_open_context_menu_delete)
        self.table_delete.itemSelectionChanged.connect(self._qt_on_item_selection_changed_delete)


        self.delete_menu = QT.QMenu()
        act = self.delete_menu.addAction('Restore')
        act.triggered.connect(self.restore_units)
        shortcut_restore = QT.QShortcut(self.qt_widget)
        shortcut_restore.setKey(QT.QKeySequence("ctrl+r"))
        shortcut_restore.activated.connect(self.restore_units)

    def _qt_refresh(self):
        from .myqt import QT
        # Merged
        merged_units = self.controller.curation_data["merge_unit_groups"]
        self.table_merge.clear()
        self.table_merge.setRowCount(len(merged_units))
        self.table_merge.setColumnCount(1)
        self.table_merge.setHorizontalHeaderLabels(["Merged groups"])
        self.table_merge.setSortingEnabled(False)
        for ix, group in enumerate(merged_units):
            item = QT.QTableWidgetItem(str(group))
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table_merge.setItem(ix, 0, item)
        for i in range(self.table_merge.columnCount()):
            self.table_merge.resizeColumnToContents(i)

        ## deleted        
        removed_units = self.controller.curation_data["removed_units"]
        self.table_delete.clear()
        self.table_delete.setRowCount(len(removed_units))
        self.table_delete.setColumnCount(1)
        self.table_delete.setHorizontalHeaderLabels(["unit_id"])
        self.table_delete.setSortingEnabled(False)
        for i, unit_id in enumerate(removed_units):
            color = self.get_unit_color(unit_id)
            pix = QT.QPixmap(16,16)
            pix.fill(color)
            icon = QT.QIcon(pix)
            item = QT.QTableWidgetItem( f'{unit_id}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table_delete.setItem(i,0, item)
            item.setIcon(icon)
            item.unit_id = unit_id
        self.table_delete.resizeColumnToContents(0)



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

    def _qt_open_context_menu_delete(self):
        self.delete_menu.popup(self.qt_widget.cursor().pos())

    def _qt_open_context_menu_merge(self):
        self.merge_menu.popup(self.qt_widget.cursor().pos())
    
    def _qt_on_item_selection_changed_merge(self):
        if len(self.table_merge.selectedIndexes()) == 0:
            return

        dtype = self.controller.unit_ids.dtype
        ind = self.table_merge.selectedIndexes()[0].row()
        visible_unit_ids = self.controller.curation_data["merge_unit_groups"][ind]
        visible_unit_ids = [dtype.type(unit_id) for unit_id in visible_unit_ids]
        self.controller.set_visible_unit_ids(visible_unit_ids)
        self.notify_unit_visibility_changed()

    def _qt_on_item_selection_changed_delete(self):
        if len(self.table_delete.selectedIndexes()) == 0:
            return
        ind = self.table_delete.selectedIndexes()[0].row()
        unit_id = self.controller.curation_data["removed_units"][ind]
        self.controller.set_all_unit_visibility_off()
        # convert to the correct type
        unit_id = self.controller.unit_ids.dtype.type(unit_id)
        self.controller.set_visible_unit_ids([unit_id])
        self.notify_unit_visibility_changed()

    def _qt_on_restore_shortcut(self):
        sel_rows = self._qt_get_selected_rows()
        self._qt_delete_unit()
        if len(sel_rows) > 0:
            self.table.clearSelection()
            self.table.setCurrentCell(min(sel_rows[-1] + 1, self.table.rowCount() - 1), 0)


    def on_manual_curation_updated(self):
        self.refresh()

    def on_unit_visibility_changed(self):
        pass
    
    def save_in_analyzer(self):
        self.controller.save_curation_in_analyzer()

    def _qt_export_json(self):
        from .myqt import QT
        fd = QT.QFileDialog(fileMode=QT.QFileDialog.AnyFile, acceptMode=QT.QFileDialog.AcceptSave)
        fd.setNameFilters(['JSON (*.json);'])
        fd.setDefaultSuffix('json')
        fd.setViewMode(QT.QFileDialog.Detail)
        if fd.exec_():
            json_file = Path(fd.selectedFiles()[0])
            with json_file.open("w") as f:
                curation_dict = check_json(self.controller.construct_final_curation())
                json.dump(curation_dict, f, indent=4)

    # PANEL
    def _panel_make_layout(self):
        import pandas as pd
        import panel as pn

        from .utils_panel import KeyboardShortcut, KeyboardShortcuts, SelectableTabulator

        pn.extension("tabulator")

        # Create dataframe
        merge_df = pd.DataFrame({"merge_groups": []})
        delete_df = pd.DataFrame({"deleted_unit_id": []})

        # Create tables
        self.table_merge = SelectableTabulator(
            merge_df,
            show_index=False,
            disabled=True,
            sortable=False,
            formatters={"merge_groups": "plaintext"},
            sizing_mode="stretch_width",
            # SelectableTabulator functions
            parent_view=self,
            # refresh_table_function=self.refresh,
            conditional_shortcut=self._conditional_refresh_merge,
            column_callbacks={"merge_groups": self._panel_on_merged_col},
        )
        self.table_delete = SelectableTabulator(
            delete_df,
            show_index=False,
            disabled=True,
            sortable=False,
            formatters={"deleted_unit_id": "plaintext"},
            sizing_mode="stretch_width",
            # SelectableTabulator functions
            parent_view=self,
            # refresh_table_function=self.refresh,
            conditional_shortcut=self._conditional_refresh_delete,
            column_callbacks={"deleted_unit_id": self._panel_on_deleted_col},
        )

        self.table_delete.param.watch(self._panel_update_unit_visibility, "selection")
        self.table_merge.param.watch(self._panel_update_unit_visibility, "selection")

        # Create buttons
        save_button = pn.widgets.Button(
            name="Save in analyzer",
            button_type="primary",
            height=30
        )
        save_button.on_click(self._panel_save_in_analyzer)

        download_button = pn.widgets.FileDownload(
            button_type="primary",
            filename="curation.json",
            callback=self._panel_generate_json,
            height=30
        )

        restore_button = pn.widgets.Button(
            name="Restore",
            button_type="primary",
            height=30
        )
        restore_button.on_click(self._panel_restore_units)

        remove_merge_button = pn.widgets.Button(
            name="Unmerge",
            button_type="primary",
            height=30
        )
        remove_merge_button.on_click(self._panel_unmerge_groups)

        submit_button = pn.widgets.Button(
            name="Submit to parent", 
            button_type="primary",
            height=30
        )

        # Create layout
        buttons_save = pn.Row(
            save_button,
            download_button,
            submit_button,
            sizing_mode="stretch_width",
        )
        save_sections = pn.Column(
            buttons_save,
            sizing_mode="stretch_width",
        )
        buttons_curate = pn.Row(
            restore_button,
            remove_merge_button,
            sizing_mode="stretch_width",
        )

        # shortcuts
        shortcuts = [
            KeyboardShortcut(name="restore", key="r", ctrlKey=True),
            KeyboardShortcut(name="unmerge", key="u", ctrlKey=True),
        ]
        shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        shortcuts_component.on_msg(self._panel_handle_shortcut)

        # Create main layout with proper sizing
        sections = pn.Row(self.table_merge, self.table_delete, sizing_mode="stretch_width")
        self.layout = pn.Column(
            save_sections,
            buttons_curate,
            sections,
            shortcuts_component,
            scroll=True,
            sizing_mode="stretch_both"
        )

        # Add a custom JavaScript callback to the button that doesn't interact with Bokeh models
        submit_button.on_click(self._panel_submit_to_parent)

        # Add a hidden div to store the data
        self.data_div = pn.pane.HTML("", width=0, height=0, margin=0, sizing_mode="fixed")
        self.layout.append(self.data_div)


    def _panel_refresh(self):
        import pandas as pd
        # Merged
        merged_units = self.controller.curation_data["merge_unit_groups"]

        # for visualization, we make all row entries strings
        merged_units_str = []
        for group in merged_units:
            # convert to string
            group = [str(unit_id) for unit_id in group]
            merged_units_str.append(" - ".join(group))
        df = pd.DataFrame({"merge_groups": merged_units_str})
        self.table_merge.value = df
        self.table_merge.selection = []

        ## deleted        
        removed_units = self.controller.curation_data["removed_units"]
        removed_units = [str(unit_id) for unit_id in removed_units]
        df = pd.DataFrame({"deleted_unit_id": removed_units})
        self.table_delete.value = df
        self.table_delete.selection = []

    def _panel_update_unit_visibility(self, event):
        unit_dtype = self.controller.unit_ids.dtype
        if self.active_table == "delete":
            visible_unit_ids = self.table_delete.value["deleted_unit_id"].values[self.table_delete.selection].tolist()
            visible_unit_ids = [unit_dtype.type(unit_id) for unit_id in visible_unit_ids]
            self.controller.set_visible_unit_ids(visible_unit_ids)
        elif self.active_table == "merge":
            merge_groups = self.table_merge.value["merge_groups"].values[self.table_merge.selection].tolist()
            # self.controller.set_all_unit_visibility_off()
            visible_unit_ids = []
            for merge_group in merge_groups:
                merge_unit_ids = [unit_dtype.type(unit_id) for unit_id in merge_group.split(" - ")]
                visible_unit_ids.extend(merge_unit_ids)
            self.controller.set_visible_unit_ids(visible_unit_ids)
        self.notify_unit_visibility_changed()

    def _panel_restore_units(self, event):
        self.restore_units()

    def _panel_unmerge_groups(self, event):
        self.unmerge_groups()

    def _panel_save_in_analyzer(self, event):
        self.save_in_analyzer()

    def _panel_generate_json(self):
        # Get the path from the text input
        export_path = "curation.json"
        # Save the JSON file
        curation_dict = check_json(self.controller.construct_final_curation())

        with open(export_path, "w") as f:
            json.dump(curation_dict, f, indent=4)

        return export_path

    def _panel_get_delete_table_selection(self):
        selected_items = self.table_delete.selection
        if len(selected_items) == 0:
            return None
        else:
            return self.table_delete.value["deleted_unit_id"].values[selected_items].tolist()

    def _panel_get_merge_table_row(self):
        selected_items = self.table_merge.selection
        if len(selected_items) == 0:
            return None
        else:
            return selected_items

    def _panel_handle_shortcut(self, event):
        if event.data == "restore":
            self.restore_units()
        elif event.data == "unmerge":
            self.unmerge_groups()

    def _panel_submit_to_parent(self, event):
        """Send the curation data to the parent window"""
        # Get the curation data and convert it to a JSON string
        curation_data = json.dumps(check_json(self.controller.construct_final_curation()))

        # Create a JavaScript snippet that will send the data to the parent window
        js_code = f"""
        <script>
        (function() {{
            try {{
                const jsonData = {json.dumps(curation_data)};
                const data = {{
                    type: 'curation_data',
                    curation_data: JSON.parse(jsonData)
                }};
                console.log('Sending data to parent:', data);
                parent.postMessage({{
                    type: 'panel-data',
                    data: data
                }}, '*');
                console.log('Data sent successfully');
            }} catch (error) {{
                console.error('Error sending data to parent:', error);
            }}
        }})();
        </script>
        """

        # Update the hidden div with the JavaScript code
        self.data_div.object = js_code

    def _panel_on_deleted_col(self, row):
        self.active_table = "delete"
        self.table_merge.selection = []

    def _panel_on_merged_col(self, row):
        self.active_table = "merge"
        self.table_delete.selection = []

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


CurationView._gui_help_txt = """
## Curation View

The curation view shows the current status of the curation process and allows the user to manually visualize,
revert, and export the curation data.

### Controls
- **save in analyzer**: Save the current curation state in the analyzer.
- **export/download JSON**: Export the current curation state to a JSON file.
- **restore**: Restore the selected unit from the deleted units table.
- **unmerge**: Unmerge the selected merge group from the merged units table.
- **submit to parent**: Submit the current curation state to the parent window (for use in web applications).
- **press 'ctrl+r'**: Restore the selected units from the deleted units table.
- **press 'ctrl+u'**: Unmerge the selected merge groups from the merged units table.
"""
