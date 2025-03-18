import numpy as np

from .view_base import ViewBase






# TODO Sam : settings choix de column


class UnitListView(ViewBase):
    _supported_backend = ['qt']
    _settings = [] # this is a hack to create the settings button

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    def _make_layout_qt(self):
        from .myqt import QT
        import pyqtgraph as pg
        

        self.menu = None
        self.layout = QT.QVBoxLayout()
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)

        h.addStretch()
        
        self.table = QT.QTableWidget()
        self.layout.addWidget(self.table)
        self.table.itemChanged.connect(self._qt_on_item_changed)
        self.table.cellDoubleClicked.connect(self._qt_on_double_clicked)
        shortcut_visible = QT.QShortcut(self.qt_widget)
        shortcut_visible.setKey(QT.QKeySequence(QT.Key_Space))
        shortcut_visible.activated.connect(self.on_visible_shortcut)
        
        # Enable column dragging
        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        header.sectionMoved.connect(self.on_column_moved)
        
        # Store original column order
        self.column_order = None
        
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
            shortcut_delete = QT.QShortcut(self.qt_widget)
            shortcut_delete.setKey(QT.QKeySequence('d'))
            shortcut_delete.activated.connect(self.on_delete_shortcut)

    def on_column_moved(self, logical_index, old_visual_index, new_visual_index):
        # Update stored column order
        self.column_order = [self.table.horizontalHeader().logicalIndex(i) for i in range(self.table.columnCount())]

    def create_settings_TODO(self):
        # hack to use settings to control visible columns

        params = []
        for col in self.controller.units_table.columns:
            params.append(
                {'name': str(col), 'type': 'bool', 'value': col in self.controller.displayed_unit_properties }
            )
        self.params = pg.parametertree.Parameter.create( name='Visible', type='group', children=params)
        
        self.tree_settings = pg.parametertree.ParameterTree(parent=self)
        self.tree_settings.header().hide()
        self.tree_settings.setParameters(self.params, showTop=True)
        self.tree_settings.setWindowTitle(u'Options for waveforms hist viewer')
        self.tree_settings.setWindowFlags(QT.Qt.Window)
        
        self.params.sigTreeStateChanged.connect(self.on_params_changed)

    def on_params_changed_TODO(self):
        new_displayed = [col for col in self.controller.units_table.columns if self.params[col]]
        self.controller.displayed_unit_properties = new_displayed
        self.refresh()

    def _refresh_qt(self):
        from .myqt import QT
        from .utils_qt import OrderableCheckItem, CustomItem, LabelComboBox

        self.table.itemChanged.disconnect(self._qt_on_item_changed)
        
        # Store current column order before clearing
        if self.table.columnCount() > 0:
            self.column_order = [self.table.horizontalHeader().logicalIndex(i) for i in range(self.table.columnCount())]
        
        self.table.clear()


        internal_column_names = ['unit_id', 'visible',  'channel_id', 'sparsity']

        # internal labels
        column_labels = list(internal_column_names)

        if self.controller.curation:
            label_definitions = self.controller.get_curation_label_definitions()
            num_labels = len(label_definitions)
            column_labels += [k for k, label_def in label_definitions.items()]
        else:
            label_definitions = None
            num_labels = 0
        
        column_labels += self.controller.displayed_unit_properties
        
        self.table.setColumnCount(len(column_labels))
        self.table.setHorizontalHeaderLabels(column_labels)

        self.table.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._qt_on_open_context_menu)
        self.table.setSelectionMode(QT.QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QT.QAbstractItemView.SelectRows)

        unit_ids = self.controller.unit_ids
        
        self.table.setRowCount(len(unit_ids))
        self.table.setSortingEnabled(False)

        # internal_column_names
        for i, unit_id in enumerate(unit_ids):
            color = self.get_unit_color(unit_id)
            pix = QT.QPixmap(16,16)
            pix.fill(color)
            icon = QT.QIcon(pix)
            
            item = QT.QTableWidgetItem( f'{unit_id}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i,0, item)
            item.setIcon(icon)
            
            item = OrderableCheckItem('')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable|QT.Qt.ItemIsUserCheckable)
            item.setCheckState({ False: QT.Qt.Unchecked, True : QT.Qt.Checked}[self.controller.unit_visible_dict.get(unit_id, False)])
            self.table.setItem(i,1, item)
            item.unit_id = unit_id
            
            channel_index = self.controller.get_extremum_channel(unit_id)
            channel_id = self.controller.channel_ids[channel_index]
            item = CustomItem(f'{channel_id}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i, 2, item)
            
            num_chan = np.sum(self.controller.get_sparsity_mask()[i, :])
            item = CustomItem(f'{num_chan}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i, 3, item)



            n_first = len(internal_column_names)
            if label_definitions is not None:
                for ix, (category, label_def) in enumerate(label_definitions.items()):
                    label = self.controller.get_unit_label(unit_id, category)
                    item = LabelComboBox(i, category, label_def['label_options'], parent=self.qt_widget)
                    item.set_label(label)
                    item.remove_label_clicked.connect(self.on_remove_label)
                    item.label_changed.connect(self.on_label_changed)
                    self.table.setCellWidget(i, n_first + ix, item)

            # if with_metrics:
            if True:
                
                for m, col in enumerate(self.controller.displayed_unit_properties):
                    v = self.controller.units_table.loc[unit_id, col]
                    if isinstance(v, float):
                        item = CustomItem(f'{v:0.2f}')
                    else:
                        item = CustomItem(f'{v}')
                    self.table.setItem(i, n_first + num_labels + m, item)

        for i in range(5):
            self.table.resizeColumnToContents(i)
        self.table.setSortingEnabled(True)
        self.table.itemChanged.connect(self._qt_on_item_changed)
        
        # Restore column order if it exists
        if self.column_order is not None and len(self.column_order) == self.table.columnCount():
            header = self.table.horizontalHeader()
            for visual_index, logical_index in enumerate(self.column_order):
                current_visual = header.visualIndex(logical_index)
                if current_visual != visual_index:
                    header.moveSection(current_visual, visual_index)

    def on_label_changed(self, unit_index, category, new_label):
        unit_id = self.controller.unit_ids[unit_index]
        self.controller.set_label_to_unit(unit_id, category, new_label)

    def on_remove_label(self, unit_index, category):
        unit_id = self.controller.unit_ids[unit_index]
        self.controller.set_label_to_unit(unit_id, category, None)

    def _qt_on_item_changed(self, item):
        from .myqt import QT
        if item.column() != 1: return
        sel = {QT.Qt.Unchecked : False, QT.Qt.Checked : True}[item.checkState()]
        unit_id = item.unit_id
        self.controller.unit_visible_dict[unit_id] = bool(item.checkState())

        # self.controller.update_visible_spikes()
        self.notify_unit_visibility_changed()
    
    def _qt_on_double_clicked(self, row, col):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = False
            
        unit_id = self.table.item(row, 1).unit_id
        self.controller.unit_visible_dict[unit_id] = True
        self.refresh()

        # self.controller.update_visible_spikes()
        self.notify_unit_visibility_changed()
    
    def _qt_on_open_context_menu(self):
        self.menu.popup(self.cursor().pos())
    
    def show_all(self):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = True
        self.refresh()

        # self.controller.update_visible_spikes()
        self.notify_unit_visibility_changed()
    
    def hide_all(self):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = False
        self.refresh()

        # self.controller.update_visible_spikes()
        self.notify_unit_visibility_changed()

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
        rows = self._get_selected_rows()
        for unit_id in self.controller.unit_ids:
            self.controller.unit_visible_dict[unit_id] = False
        for unit_id in self.get_selected_unit_ids():
            self.controller.unit_visible_dict[unit_id] = True
        self.refresh()
        # self.controller.update_visible_spikes()
        self.notify_unit_visibility_changed()
        # self.table.set
        # self.table.setCurrentCell(rows[0], None, QT.QItemSelectionModel.Select)
        # self.table.scrollTo(index)
        for row in rows:
            self.table.selectRow(row)

    def delete_unit(self):
        removed_unit_ids = self.get_selected_unit_ids()
        self.controller.make_manual_delete_if_possible(removed_unit_ids)
        self.notigy_manual_curation_updated()
        self.refresh()

    def on_delete_shortcut(self):
        sel_rows = self._get_selected_rows()
        self.delete_unit()
        if len(sel_rows) > 0:
            self.table.setCurrentCell(min(sel_rows[-1] + 1, self.table.rowCount() - 1), 0)

    def merge_selected(self):
        merge_unit_ids = self.get_selected_unit_ids()
        self.controller.make_manual_merge_if_possible(merge_unit_ids)
        self.notify_manual_curation_updated()
        self.refresh()



UnitListView._gui_help_txt = """Unit list
This control the visibility of units : check/uncheck visible
Check box : make visible or unvisible
Double click on a row : make it visible  alone
Right click : context menu (delete or merge if curation=True)
Drag column headers : reorder columns
"""
