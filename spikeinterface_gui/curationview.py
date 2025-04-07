import json
from pathlib import Path

from .view_base import ViewBase

from spikeinterface.core.core_tools import check_json




class CurationView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _need_compute = False

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

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
        self.table_merge.customContextMenuRequested.connect(self.open_context_menu_merge)
        self.table_merge.itemSelectionChanged.connect(self.on_item_selection_changed_merge)

        self.merge_menu = QT.QMenu()
        act = self.merge_menu.addAction('Remove merge group')
        act.triggered.connect(self.unmerge_groups)


        v = QT.QVBoxLayout()
        h.addLayout(v)
        v.addWidget(QT.QLabel("<b>Deleted</b>"))
        self.table_delete = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        v.addWidget(self.table_delete)
        self.table_delete.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table_delete.customContextMenuRequested.connect(self.open_context_menu_delete)
        self.table_delete.itemSelectionChanged.connect(self.on_item_selection_changed_delete)


        self.delete_menu = QT.QMenu()
        act = self.delete_menu.addAction('Restore')
        act.triggered.connect(self.restore_unit)

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
            return [s.row for s in selected_items]

    def open_context_menu_delete(self):
        self.delete_menu.popup(self.qt_widget.cursor().pos())

    def open_context_menu_merge(self):
        self.merge_menu.popup(self.qt_widget.cursor().pos())

    def restore_unit(self):
        if self.backend == 'qt':
            unit_ids = self._qt_get_delete_table_selection()
        else:
            unit_ids = self._panel_get_delete_table_selection()
        if unit_ids is not None:
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
    
    def on_item_selection_changed_merge(self):
        if len(self.table_merge.selectedIndexes()) == 0:
            return

        ind = self.table_merge.selectedIndexes()[0].row()
        unit_ids = self.controller.curation_data["merge_unit_groups"][ind]
        for k in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[k] = False
        for unit_id in unit_ids:
            self.controller.unit_visible_dict[unit_id] = True
        self.notify_unit_visibility_changed()

    def on_item_selection_changed_delete(self):
        if len(self.table_delete.selectedIndexes()) == 0:
            return
        ind = self.table_delete.selectedIndexes()[0].row()
        unit_id = self.controller.curation_data["removed_units"][ind]
        for k in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[k] = False
        self.controller.unit_visible_dict[unit_id] = True
        self.notify_unit_visibility_changed()

    def on_manual_curation_updated(self):
        self.refresh()
    
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
            # print(json_file)
            with json_file.open("w") as f:
                curation_dict = check_json(self.controller.construct_final_curation())
                json.dump(curation_dict, f, indent=4)

    # PANEL
    def _panel_make_layout(self):
        import pandas as pd
        import panel as pn
        pn.extension("tabulator")

        # Create dataframe
        merge_df = pd.DataFrame({"Merge groups": []})
        delete_df = pd.DataFrame({"Deleted unit ID": []})

        # Create tables
        self.table_merge = pn.widgets.Tabulator(merge_df, show_index=False, disabled=True, sizing_mode="stretch_width")
        self.table_delete = pn.widgets.Tabulator(delete_df, show_index=False, disabled=True, sizing_mode="stretch_width")

        # Create buttons
        save_button = pn.widgets.Button(name="Save in analyzer", button_type="primary")
        save_button.on_click(lambda event: self.save_in_analyzer)

        self.export_path = pn.widgets.TextInput(name="Export Path", placeholder="Enter path to save JSON")
        export_button = pn.widgets.Button(name="Export JSON", button_type="primary")
        export_button.on_click(lambda event: self._panel_export_json)

        restore_button = pn.widgets.Button(name="Restore", button_type="primary")
        restore_button.on_click(lambda event: self.restore_unit)
        remove_merge_button = pn.widgets.Button(name="Unmerge", button_type="primary")
        remove_merge_button.on_click(lambda event: self.unmerge_groups)

        submit_button = pn.widgets.Button(name="Submit to parent", button_type="primary")
        # Create layout
        buttons_save = pn.Row(
            save_button,
            export_button,
            submit_button,
            sizing_mode="stretch_width",
        )
        save_sections = pn.Column(
            buttons_save,
            self.export_path,
            sizing_mode="stretch_width",
        )
        buttons_curate = pn.Row(
            restore_button,
            remove_merge_button,
            sizing_mode="stretch_width",
        )

        # Create main layout with proper sizing
        sections = pn.Row(self.table_merge, self.table_delete, sizing_mode="stretch_width")
        self.layout = pn.Column(save_sections, buttons_curate, sections, sizing_mode="stretch_both")

        # # JavaScript code to send the data to the parent window when the button is clicked
        # TODO: fix this
        # submit_button.js_on_click(code=
        #     """
        #         const raw_data = JSON.parse(JSON.stringify(arguments[0]));
        #         const data = {
        #             type: 'curation_data',
        #             curation_data: raw_data
        #         };
        #         console.log(data); 
        #         parent.postMessage({
        #             type: 'panel-data',
        #             data: data
        #         }, '*');
        #     """, 
        #     args=dict(curation_data=check_json(self.controller.construct_final_curation()))
        # )


    def _panel_refresh(self):
        import pandas as pd
        # Merged
        merged_units = self.controller.curation_data["merge_unit_groups"]
        df = pd.DataFrame({"Merged groups": merged_units})
        self.table_merge.value = df
        self.table_merge.selection = []

        ## deleted        
        removed_units = self.controller.curation_data["removed_units"]
        df = pd.DataFrame({"Deleted Unit ID": removed_units})
        self.table_delete.value = df
        self.table_delete.selection = []


    def _panel_export_json(self):
        # Get the path from the text input
        export_path = Path(self.export_path.value)

        # Check if the path is valid
        if not export_path.suffix == ".json":
            export_path += export_path.parent / f"{export_path.name}.json"

        # Save the JSON file
        curation_dict = check_json(self.controller.construct_final_curation())

        with open(export_path, "w") as f:
            json.dump(curation_dict, f, indent=4)

    def _panel_get_delete_table_selection(self):
        selected_items = self.table_delete.selection
        if len(selected_items) == 0:
            return None
        else:
            return self.table_delete.value["Deleted Unit ID"].values.tolist()

    def _panel_get_merge_table_row(self):
        selected_items = self.table_merge.selection
        if len(selected_items) == 0:
            return None
        else:
            return selected_items



CurationView._gui_help_txt = """Curation includes potential delete + merge
Must export or apply to analyzer to make persistent
Click on items to make then visible
Right click to remove merges or restore deletions
"""
