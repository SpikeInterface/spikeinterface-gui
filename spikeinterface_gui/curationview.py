import json
from pathlib import Path

from .view_base import ViewBase

from spikeinterface.core.core_tools import check_json




class CurationView(ViewBase):
    _supported_backend = ['qt']
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
        act.triggered.connect(self.remove_merge_group)



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

    def open_context_menu_delete(self):
        self.delete_menu.popup(self.cursor().pos())

    def open_context_menu_merge(self):
        self.merge_menu.popup(self.cursor().pos())

    def restore_unit(self):
        unit_id = self.table_delete.selectedItems()[0].unit_id
        self.controller.make_manual_restore([unit_id])
        self.notify_manual_curation_updated()
        self.refresh()
    

    def remove_merge_group(self):
        merge_index = self.table_merge.selectedItems()[0].row()

        self.controller.make_manual_restore_merge(merge_index)
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



CurationView._gui_help_txt = """Curation includes potential delete + merge
Must export or apply to analyzer to make persistent
Click on items to make then visible
Right click to remove merges or restore deletions
"""
