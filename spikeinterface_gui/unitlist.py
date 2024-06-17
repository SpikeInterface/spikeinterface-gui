from .myqt import QT
import pyqtgraph as pg

import numpy as np

from .base import WidgetBase
from .tools import ParamDialog, CustomItem, find_category, LabelComboBox


_column_names = ['unit_id', 'visible', 'num_spikes', 'channel_id', 'sparsity']

# TODO: Save categories / labels


class UnitListView(WidgetBase):
    """
    """
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)

        self.menu = None
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        if self.controller.handle_metrics():
            self.checkbox_metrics = QT.QCheckBox('metrics')
            self.checkbox_metrics.setChecked(True)
            h.addWidget(self.checkbox_metrics)
            self.checkbox_metrics.stateChanged.connect(self.refresh)
        
        # self.categories = self._basic_categories.copy()
        # self.labels_btn = QT.QPushButton('Labels')
        # h.addWidget(self.labels_btn)
        # self.labels_btn.clicked.connect(self.update_labels)

        h.addStretch()
        
        self.table = QT.QTableWidget()
        self.layout.addWidget(self.table)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.cellDoubleClicked.connect(self.on_double_clicked)
        shortcut_visible = QT.QShortcut(self)
        shortcut_visible.setKey(QT.QKeySequence(QT.Key_Space))
        shortcut_visible.activated.connect(self.on_visible_shortcut)
        self.make_menu()
        
        self.refresh()

    # def update_labels(self):
    #     print(self.categories)
    #     label_add = LabelCreator(self)
    #     r = label_add.edit_label(self.categories)
    #     if r is None:
    #         return
    #     print(r)
    #     cat, old_label, new_label = r
    #     cat_info = find_category(self.categories, cat)
    #     if cat_info is None:
    #         # New category
    #         self.categories.append({'name': cat, 'labels': [new_label]})
    #         self.refresh()
    #         return
    #     else:
    #         # Renaming a label or adding a new label
    #         cat_ix, cat = cat_info
    #     if old_label == '':
    #         # Creating a new label
    #         self.categories[cat_ix]['labels'].append(new_label)
    #     else:
    #         # Renaming a label
    #         self.categories[cat_ix]['labels'] = [lbl for lbl in self.categories[cat_ix]['labels'] if lbl != old_label]
    #         self.categories[cat_ix]['labels'].append(new_label)
    #     self.refresh()

    def make_menu(self):
        self.menu = QT.QMenu()
        act = self.menu.addAction('Show all')
        act.triggered.connect(self.show_all)
        act = self.menu.addAction('Hide all')
        act.triggered.connect(self.hide_all)
        
        if self.controller.curation:
            act = self.menu.addAction('Delete')
            act.triggered.connect(self.delete_unit)
            act = self.menu.addAction('Merge selected')
            act.triggered.connect(self.merge_selected)
            shortcut_delete = QT.QShortcut(self)
            shortcut_delete.setKey(QT.QKeySequence('d'))
            shortcut_delete.activated.connect(self.on_delete_shortcut)

    def _refresh(self):
        self.table.itemChanged.disconnect(self.on_item_changed)
        
        self.table.clear()
        labels = list(_column_names)
        
        if self.controller.handle_metrics():
            with_metrics = self.checkbox_metrics.isChecked()
        else:
            with_metrics = False

        if self.controller.curation:
            label_definitions = self.controller.get_curation_label_definitions()
            num_labels = len(label_definitions)
            labels += [k for k, label_def in label_definitions.items()]
        else:
            label_definitions = None
            num_labels = 0


        # categories = [cat['name'] for cat in self.categories]
        # labels += categories

        if with_metrics:
            metrics = self.controller.metrics
            labels += list(metrics.columns)
        
        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)

        self.table.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.setSelectionMode(QT.QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QT.QAbstractItemView.SelectRows)

        unit_ids = self.controller.unit_ids
        
        self.table.setRowCount(len(unit_ids))
        self.table.setSortingEnabled(False)
        for i, unit_id in enumerate(unit_ids):
            color = self.controller.qcolors.get(unit_id, QT.QColor( 'black'))
            pix = QT.QPixmap(16,16)
            pix.fill(color)
            icon = QT.QIcon(pix)
            
            item = QT.QTableWidgetItem( f'{unit_id}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i,0, item)
            item.setIcon(icon)
            
            item = QT.QTableWidgetItem('')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable|QT.Qt.ItemIsUserCheckable)
            item.setCheckState({ False: QT.Qt.Unchecked, True : QT.Qt.Checked}[self.controller.unit_visible_dict.get(unit_id, False)])
            self.table.setItem(i,1, item)
            item.unit_id = unit_id
            
            num_spike = self.controller.num_spikes[unit_id]
            item = CustomItem(f'{num_spike}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i, 2, item)
            
            channel_index = self.controller.get_extremum_channel(unit_id)
            channel_id = self.controller.channel_ids[channel_index]
            item = CustomItem(f'{channel_id}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i, 3, item)
            
            num_chan = np.sum(self.controller.get_sparsity_mask()[i, :])
            item = CustomItem(f'{num_chan}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i, 4, item)

            if label_definitions is not None:
                for ix, (category, label_def) in enumerate(label_definitions.items()):
                    # item = QT.QComboBox()
                    # item.addItems(label_def['label_options'])
                    # item.addItem('')
                    idx, lbl = self.controller.find_unit_labels(unit_id, category)
                    if idx is None:
                        label = None
                    else:
                        label = lbl['labels'][0]
                    print(unit_id, category, label)
                    item = LabelComboBox(i, 5 + ix, label_def['label_options'], self)
                    item.remove_label_clicked.connect(self.on_remove_label)
                    item.label_changed.connect(self.on_label_changed)
                    self.table.setCellWidget(i, 5 + ix, item)

            if with_metrics:
                for m, col in enumerate(metrics.columns):
                    v = metrics.loc[unit_id, col]
                    if isinstance(v, float):
                        item = CustomItem(f'{v:0.2f}')
                    else:
                        item = CustomItem(f'{v}')
                    self.table.setItem(i, 5 + num_labels + m, item)

        for i in range(5):
            self.table.resizeColumnToContents(i)
        self.table.setSortingEnabled(True)
        self.table.itemChanged.connect(self.on_item_changed)        

    def on_label_changed(self, row, col, new_label):
        item = self.table.item(row, 1)
        unit_id = item.unit_id
        header = self.table.horizontalHeaderItem(col)
        category = header.text()
        self.controller.set_label_to_unit(unit_id, category, new_label)

    def on_remove_label(self, row, col):
        item = self.table.item(row, 1)
        unit_id = item.unit_id
        self.controller.remove_all_labels(unit_id)

    def on_item_changed(self, item):
        if item.column() != 1: return
        sel = {QT.Qt.Unchecked : False, QT.Qt.Checked : True}[item.checkState()]
        unit_id = item.unit_id
        self.controller.unit_visible_dict[unit_id] = bool(item.checkState())

        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()
    
    def on_double_clicked(self, row, col):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = False
            
        unit_id = self.table.item(row, 1).unit_id
        self.controller.unit_visible_dict[unit_id] = True
        self.refresh()

        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()
    
    def open_context_menu(self):
        self.menu.popup(self.cursor().pos())
    
    def show_all(self):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = True
        self.refresh()

        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()
    
    def hide_all(self):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = False
        self.refresh()

        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()

    def _get_selected_rows(self):
        rows = []
        for item in self.table.selectedItems():
            if item.column() != 1: continue
            rows.append(item.row())
        return sorted(rows)

    def get_selected_unit_ids(self):
        unit_ids = []
        for item in self.table.selectedItems():
            if item.column() != 1: continue
            unit_ids.append(item.unit_id)
        return unit_ids

    def on_visible_shortcut(self):
        selected_unit_ids = self.get_selected_unit_ids()
        for c_uid in selected_unit_ids:
            self.controller.unit_visible_dict[c_uid] = not self.controller.unit_visible_dict[c_uid]
        self.refresh()
        self.unit_visibility_changed.emit()

    def delete_unit(self):
        removed_unit_ids = self.get_selected_unit_ids()
        self.controller.make_manual_delete_if_possible(removed_unit_ids)
        self.manual_curation_updated.emit()
        self.refresh()

    def on_delete_shortcut(self):
        sel_rows = self._get_selected_rows()
        self.delete_unit()
        if len(sel_rows) > 0:
            self.table.setCurrentCell(min(sel_rows[-1] + 1, self.table.rowCount() - 1), 0)

    def merge_selected(self):
        merge_unit_ids = self.get_selected_unit_ids()
        self.controller.make_manual_merge_if_possible(merge_unit_ids)
        self.manual_curation_updated.emit()
        self.refresh()


# @remi-pr: merci pour tout ça! pour le momement je l'enlève pour des raisons de consistency avec les entrées
# class LabelCreator(QT.QDialog):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle('Edit or add a label')
#         self._categories = []  # [{'name': 'category', 'labels': ['label1', 'label2']}, }
#         main_lyt = QT.QVBoxLayout(self)
#         form_lyt = QT.QFormLayout()
#         self.cat_cb = QT.QComboBox(self)
#         self.labels_cb = QT.QComboBox(self)
#         self.label_le = QT.QLineEdit(self)
#         self.cat_cb.currentTextChanged.connect(self.category_changed)
#         self.cat_cb.setEditable(True)
#         form_lyt.addRow('Category', self.cat_cb)
#         form_lyt.addRow('Old label', self.labels_cb)
#         form_lyt.addRow('Label', self.label_le)
#         btn_lyt = QT.QHBoxLayout()
#         self.cancel_btn = QT.QPushButton('&Cancel')
#         self.ok_btn = QT.QPushButton('&Apply')
#         self.ok_btn.setDefault(True)
#         self.cancel_btn.clicked.connect(self.reject)
#         self.ok_btn.clicked.connect(self.accept)
#         btn_lyt.addWidget(self.cancel_btn)
#         btn_lyt.addWidget(self.ok_btn)
#         main_lyt.addLayout(form_lyt)
#         main_lyt.addLayout(btn_lyt)

#     def category_changed(self, cat_name):
#         self.labels_cb.clear()
#         self.labels_cb.addItem('')
#         r = find_category(self._categories, cat_name)
#         if r is None:
#             return
#         _, cat = r
#         self.labels_cb.addItems(cat['labels'])

#     def edit_label(self, categories):
#         print(categories)
#         self._categories = categories
#         for cat in categories:
#             self.cat_cb.addItem(cat['name'], cat)
#             # self.labels_cb.addItems(cat.labels)
#         if self.exec_():
#             return self.cat_cb.currentText(), self.labels_cb.currentText(), self.label_le.text()


UnitListView._gui_help_txt = """Unit list
This control the visibility of units
Check box : make visible or unvisible
Right click : context menu"""

