import numpy as np
import time

from .view_base import ViewBase



class UnitListView(ViewBase):
    _supported_backend = ['qt', 'panel']
    # _settings = [] # this is a hack to create the settings button
    _settings = None

    def __init__(self, controller=None, parent=None, backend="qt"):
        UnitListView._settings = [
            {'name': col, 'type': 'bool', 'value': col in controller.displayed_unit_properties, 'default': True}
            for col in controller.units_table.columns
        ]
        ViewBase.__init__(self, controller=controller, parent=parent, backend=backend)


    ## common ##
    def show_all(self):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = True
        self.refresh()
        self.notify_unit_visibility_changed()
    
    def hide_all(self):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = False
        self.refresh()
        self.notify_unit_visibility_changed()

    def get_selected_unit_ids(self):
        if self.backend == 'qt':
            return self._qt_get_selected_unit_ids()
        elif self.backend == 'panel':
            return self._panel_get_selected_unit_ids()

    ## Qt ##
    def _qt_make_layout(self):
        
        from .myqt import QT
        import pyqtgraph as pg
        

        self.menu = None
        self.layout = QT.QVBoxLayout()
        
        tb = self.qt_widget.view_toolbar
        but = QT.QPushButton('columns')
        but.clicked.connect(self._qt_select_columns)
        tb.addWidget(but)


        visible_cols = []
        for col in self.controller.units_table.columns:
            visible_cols.append(
                {'name': str(col), 'type': 'bool', 'value': col in self.controller.displayed_unit_properties, 'default': True}
            )
        self.visible_columns = pg.parametertree.Parameter.create( name='visible columns', type='group', children=visible_cols)
        self.tree_visible_columns = pg.parametertree.ParameterTree(parent=self.qt_widget)
        self.tree_visible_columns.header().hide()
        self.tree_visible_columns.setParameters(self.visible_columns, showTop=True)
        # self.tree_visible_columns.setWindowTitle(u'visible columns')
        # self.tree_visible_columns.setWindowFlags(QT.Qt.Window)
        self.visible_columns.sigTreeStateChanged.connect(self._qt_on_visible_columns_changed)
        self.layout.addWidget(self.tree_visible_columns)
        self.tree_visible_columns.hide()

        # h = QT.QHBoxLayout()
        # self.layout.addLayout(h)
        # h.addStretch()
        
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
        header.sectionMoved.connect(self._qt_on_column_moved)
        
        # Store original column order
        self.column_order = None
        
        self.menu = QT.QMenu()
        act = self.menu.addAction('Show all')
        act.triggered.connect(self.show_all)
        act = self.menu.addAction('Hide all')
        act.triggered.connect(self.hide_all)
        
        if self.controller.curation:
            act = self.menu.addAction('Delete')
            act.triggered.connect(self._qt_delete_unit)
            act = self.menu.addAction('Merge selected')
            act.triggered.connect(self._qt_merge_selected)
            shortcut_delete = QT.QShortcut(self.qt_widget)
            shortcut_delete.setKey(QT.QKeySequence('d'))
            shortcut_delete.activated.connect(self._qt_on_delete_shortcut)

    def _qt_on_column_moved(self, logical_index, old_visual_index, new_visual_index):
        # Update stored column order
        self.column_order = [self.table.horizontalHeader().logicalIndex(i) for i in range(self.table.columnCount())]

    def _qt_select_columns(self):
        if not self.tree_visible_columns.isVisible():
            self.tree_visible_columns.show()
        else:
            self.tree_visible_columns.hide()

    def _qt_on_visible_columns_changed(self):
        new_displayed = [col for col in self.controller.units_table.columns if self.visible_columns[col]]
        self.controller.displayed_unit_properties = new_displayed
        self._qt_full_table_refresh()
    
    def _qt_on_unit_visibility_changed(self):
        self._qt_refresh_visibility_items()

    def _qt_refresh_visibility_items(self):
        from .myqt import QT

        self.table.itemChanged.disconnect(self._qt_on_item_changed)
        for i, unit_id in enumerate(self.controller.unit_ids):
            item = self.items_visibility[unit_id]
            item.setCheckState({ False: QT.Qt.Unchecked, True : QT.Qt.Checked}[self.controller.unit_visible_dict[unit_id]])
        self.table.itemChanged.connect(self._qt_on_item_changed)

    def _qt_refresh(self):
        # TODO sam change this bad hack after speedup the combox
        if hasattr(self, 'items_visibility'):
            self._qt_refresh_visibility_items()
        else:
            # the time at startup
            self._qt_full_table_refresh()
        
    
    def _qt_full_table_refresh(self):
        # TODO sam make this faster

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
        self.items_visibility = {}
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
            self.items_visibility[unit_id] = item
            
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
                    item.remove_label_clicked.connect(self._qt_on_remove_label)
                    item.label_changed.connect(self._qt_on_label_changed)
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

    def _qt_on_label_changed(self, unit_index, category, new_label):
        unit_id = self.controller.unit_ids[unit_index]
        self.controller.set_label_to_unit(unit_id, category, new_label)

    def _qt_on_remove_label(self, unit_index, category):
        unit_id = self.controller.unit_ids[unit_index]
        self.controller.set_label_to_unit(unit_id, category, None)

    def _qt_on_item_changed(self, item):
        from .myqt import QT
        if item.column() != 1: return
        sel = {QT.Qt.Unchecked : False, QT.Qt.Checked : True}[item.checkState()]
        unit_id = item.unit_id
        self.controller.unit_visible_dict[unit_id] = bool(item.checkState())

        self.notify_unit_visibility_changed()
    
    def _qt_on_double_clicked(self, row, col):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = False
            
        unit_id = self.table.item(row, 1).unit_id
        self.controller.unit_visible_dict[unit_id] = True
        # self.refresh()
        self._qt_refresh_visibility_items()

        self.notify_unit_visibility_changed()
    
    def _qt_on_open_context_menu(self):
        self.menu.popup(self.qt_widget.cursor().pos())
    
    def _qt_get_selected_rows(self):
        rows = []
        for item in self.table.selectedItems():
            if item.column() != 1: continue
            rows.append(item.row())
        return sorted(rows)

    def _qt_get_selected_unit_ids(self):
        unit_ids = []
        for item in self.table.selectedItems():
            if item.column() != 1: continue
            unit_ids.append(item.unit_id)
        return unit_ids


    def on_visible_shortcut(self):
        rows = self._qt_get_selected_rows()
        for unit_id in self.controller.unit_ids:
            self.controller.unit_visible_dict[unit_id] = False
        for unit_id in self.get_selected_unit_ids():
            self.controller.unit_visible_dict[unit_id] = True
        # self.refresh()
        self._qt_refresh_visibility_items()
        self.notify_unit_visibility_changed()
        for row in rows:
            self.table.selectRow(row)


    def _qt_on_delete_shortcut(self):
        sel_rows = self._qt_get_selected_rows()
        self._qt_delete_unit()
        if len(sel_rows) > 0:
            self.table.setCurrentCell(min(sel_rows[-1] + 1, self.table.rowCount() - 1), 0)


    def _qt_delete_unit(self):
        removed_unit_ids = self.get_selected_unit_ids()
        self.controller.make_manual_delete_if_possible(removed_unit_ids)
        self.notify_manual_curation_updated()

    def _qt_merge_selected(self):
        merge_unit_ids = self.get_selected_unit_ids()
        merge_successful = self.controller.make_manual_merge_if_possible(merge_unit_ids)
        if merge_successful:
            self.notify_manual_curation_updated()
        else:
            print("Merge not possible, some units are already deleted or in a merge group")
            # optional: notify.failed merge?




    ## panel zone ##
    def _panel_make_layout(self):
        import panel as pn
        import pandas as pd
        import matplotlib.colors as mcolors
        from bokeh.models.widgets.tables import BooleanFormatter, SelectEditor
        from .utils_panel import unit_formatter, KeyboardShortcut, KeyboardShortcuts

        pn.extension("tabulator")

        if self.controller.curation:
            self.label_definitions = self.controller.get_curation_label_definitions()
        else:
            self.label_definitions = None

        unit_ids = self.controller.unit_ids

        # set unmutable data
        data = {
            "unit_id": [],
            "visible": list(self.controller.unit_visible_dict.values()),
        }
        frozen_columns = ["unit_id", "visible"]
        if self.label_definitions is not None:
            for label in self.label_definitions:
                data[label] = [None] * len(unit_ids)
                if label == "quality":
                    frozen_columns.append(label)
        data["channel_id"] = []
        data["sparsity"] = []

        self.main_cols = list(data.keys())
        sparsity_mask = self.controller.get_sparsity_mask()
        for unit_index, unit_id in enumerate(unit_ids):
            data["unit_id"].append(
                {"id": str(unit_id), "color": mcolors.to_hex(self.controller.get_unit_color(unit_id))}
            )
            data["channel_id"].append(
                self.controller.channel_ids[self.controller.get_extremum_channel(unit_id)]
            )
            data["sparsity"].append(
                np.sum(sparsity_mask[unit_index, :])
            )
        for col in self.controller.displayed_unit_properties:
            data[col] = self.controller.units_table[col]

        self.df = pd.DataFrame(
            data=data,
            index=unit_ids
        )
        formatters = {
            "unit_id": unit_formatter,
            "visible": BooleanFormatter()
        }
        editors = {}
        for col in self.df.columns:
            if col != "visible":
                editors[col] = {'type': 'editable', 'value': False}
        if self.label_definitions is not None:
            for label in self.label_definitions:
                editors[label] = SelectEditor(options=self.label_definitions[label]['label_options'])
        self.table = pn.widgets.Tabulator(
            self.df,
            formatters=formatters,
            frozen_columns=frozen_columns,
            sizing_mode="stretch_both",
            layout="fit_data",
            show_index=False,
            selectable=True,
            editors=editors,
            pagination=None,
        )

        self.select_all_button = pn.widgets.Button(name="Select All", button_type="default")
        self.unselect_all_button = pn.widgets.Button(name="Unselect All", button_type="default")

        button_list = [
            self.select_all_button,
            self.unselect_all_button,
        ]
        self.delete_button = pn.widgets.Button(name="Delete", button_type="default")
        self.merge_button = pn.widgets.Button(name="Merge", button_type="default")

        if self.controller.curation:
            button_list += [
                self.delete_button,
                self.merge_button,
            ]
        self.info_text = pn.pane.HTML("")

        buttons = pn.Row(*button_list, sizing_mode="stretch_width")

        # shortcuts
        shortcuts = [
            KeyboardShortcut(name="delete", key="d", ctrlKey=False),
            KeyboardShortcut(name="merge", key="m", ctrlKey=False),
            KeyboardShortcut(name="visible", key=" ", ctrlKey=False),
            KeyboardShortcut(name="next", key="ArrowDown", ctrlKey=False),
            KeyboardShortcut(name="previous", key="ArrowUp", ctrlKey=False),
            KeyboardShortcut(name="next_only", key="ArrowDown", ctrlKey=True),
            KeyboardShortcut(name="previous_only", key="ArrowUp", ctrlKey=True),
        ]
        shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        shortcuts_component.on_msg(self._panel_handle_shortcut)

        self.layout = pn.Column(
            pn.Row(
                self.info_text,
            ),
            buttons,
            self.table,
            shortcuts_component,
            sizing_mode="stretch_width",
        )

        # self.source.selected.on_change("indices", self._panel_on_selection_changed)
        self.table.on_click(self._panel_on_selection_changed)
        self.select_all_button.on_click(lambda event: self.show_all)
        self.unselect_all_button.on_click(lambda event: self.hide_all)

        if self.controller.curation:
            self.delete_button.on_click(lambda event: self._panel_delete_unit)
            self.merge_button.on_click(lambda event: self._panel_merge_selected)

        self.last_row = None
        self.last_clicked = None


    def _panel_refresh(self):
        unit_ids = self.controller.unit_ids
        df = self.table.value
        df.loc[:, "visible"] = list(self.controller.unit_visible_dict.values())

        table_columns = self.df.columns

        for table_col in table_columns:
            if table_col not in self.main_cols + self.controller.displayed_unit_properties:
                df.drop(columns=[table_col], inplace=True)

        for col in self.controller.displayed_unit_properties:
            if col not in table_columns:
                self.table.hidden_columns.append(col)

        self.table.value = df

        # self.source.data.update(data)
        n1 = len(unit_ids)
        n2 = sum(self.controller.unit_visible_dict.values())
        txt = f"<b>All units</b>: {n1} - <b>selected</b>: {n2}"
        self.info_text.object = txt

    def _panel_on_selection_changed(self, event):
        row = event.row
        col = event.column
        unit_ids = self.controller.unit_ids
        selected_unit_id = unit_ids[row]
        time_clicked = time.perf_counter()
        df = self.table.value
        double_clicked = False
        visibility_changed = False
        if self.last_clicked is not None:
            if (time_clicked - self.last_clicked) < 0.8 and self.last_row == row:
                double_clicked = True
                
                # select only this unit
                for unit_id in self.controller.unit_visible_dict:
                    self.controller.unit_visible_dict[unit_id] = False
                self.controller.unit_visible_dict[selected_unit_id] = True
                self.notify_unit_visibility_changed()
                visibility_changed = True
        if not double_clicked:
            if col == "visible":
                self.controller.unit_visible_dict[selected_unit_id] = True
                self.notify_unit_visibility_changed()
                visibility_changed = True
            else:
                unit_id = self.df.index[row]

        if visibility_changed:
            df.loc[:, "visible"] = list(self.controller.unit_visible_dict.values())
            self.table.value = df

        self.last_clicked = time_clicked
        self.last_row = row

    def _panel_get_selected_unit_ids(self):
        if self.table.sorters is None or len(self.table.sorters) == 0:
            return self.table.selection
        elif len(self.table.sorters) == 1:
            # apply sorters to selection
            sorter = self.table.sorters[0]
            if sorter["field"] != "unit_id":
                sorted_df = self.df.sort_values(
                    by=sorter['field'],
                    ascending=(sorter['dir'] == 'asc')
                )
            else:
                sorted_df = self.df.sort_index(ascending=(sorter['dir'] == 'asc'))
            sorted_df.reset_index(inplace=True)
            new_selection = []
            for index in self.table.selection:
                new_index = sorted_df.index[sorted_df['unit_id'] == self.df.iloc[index]['unit_id']]
                if len(new_index) > 0:
                    new_selection.append(int(new_index[0]))
            return new_selection

    def _panel_get_sorted_indices(self):
        if self.table.sorters is None or len(self.table.sorters) == 0:
            return list(range(len(self.df)))
        elif len(self.table.sorters) == 1:
            # apply sorters to selection
            sorter = self.table.sorters[0]
            if sorter["field"] != "unit_id":
                sorted_df = self.df.sort_values(
                    by=sorter['field'],
                    ascending=(sorter['dir'] == 'asc')
                )
            else:
                sorted_df = self.df.sort_index(ascending=(sorter['dir'] == 'asc'))
            # sorted_df.reset_index(inplace=True)
            sorted_unit_ids = sorted_df.index.values
            original_unit_ids = list(self.df.index)
            new_indices = [original_unit_ids.index(unit_id) for unit_id in sorted_unit_ids]
            return new_indices

    def _panel_handle_shortcut(self, event):
        if event.data == "delete":
            self._panel_delete_unit()
        elif event.data == "merge":
            self._panel_merge_selected()
        elif event.data == "visible":
            selected_rows = self._panel_get_selected_unit_ids()
            for unit_id in self.controller.unit_ids:
                self.controller.unit_visible_dict[unit_id] = False
            for unit_id in self.controller.unit_ids[selected_rows]:
                self.controller.unit_visible_dict[unit_id] = True
            self.notify_unit_visibility_changed()
            self.refresh()
        elif event.data == "next":
            selected_rows = self._panel_get_selected_unit_ids()
            if len(selected_rows) == 0:
                next_row = 0
            else:
                next_row = max(selected_rows) + 1
            if next_row < len(self.controller.unit_ids):
                next_row = self._panel_get_sorted_indices()[next_row]
                if next_row not in self.table.selection:
                    self.table.selection.append(next_row)
                    self.refresh()
        elif event.data == "previous":
            selected_rows = self._panel_get_selected_unit_ids()
            if len(selected_rows) == 0:
                previous_row = 0
            else:
                previous_row = min(selected_rows) - 1
            if previous_row >= 0:
                previous_row = self._panel_get_sorted_indices()[previous_row]
                if previous_row not in self.table.selection:
                    self.table.selection.append(previous_row)
                    self.refresh()
        elif event.data == "next_only":
            selected_rows = self._panel_get_selected_unit_ids()
            if len(selected_rows) == 0:
                next_row = 0
            else:
                next_row = max(selected_rows) + 1
            if next_row < len(self.controller.unit_ids):
                next_row = self._panel_get_sorted_indices()[next_row]
                for unit_id in self.controller.unit_visible_dict:
                    self.controller.unit_visible_dict[unit_id] = False
                unit_id = self.controller.unit_ids[next_row]
                self.controller.unit_visible_dict[unit_id] = True
                self.table.selection = [next_row]
                self.notify_unit_visibility_changed()
                self.refresh()
        elif event.data == "previous_only":
            selected_rows = self._panel_get_selected_unit_ids()
            if len(selected_rows) == 0:
                previous_row = 0
            else:
                previous_row = min(selected_rows) - 1
            if previous_row >= 0:
                previous_row = self._panel_get_sorted_indices()[previous_row]
                for unit_id in self.controller.unit_visible_dict:
                    self.controller.unit_visible_dict[unit_id] = False
                unit_id = self.controller.unit_ids[previous_row]
                self.controller.unit_visible_dict[unit_id] = True
                self.table.selection = [previous_row]
                self.notify_unit_visibility_changed()
                self.refresh()

    def _panel_delete_unit(self):
        removed_unit_ids = self.get_selected_unit_ids()
        self.controller.make_manual_delete_if_possible(removed_unit_ids)
        self.notify_manual_curation_updated()
        self.refresh()

    def _panel_merge_selected(self):
        merge_unit_ids = self.get_selected_unit_ids()
        merge_successful = self.controller.make_manual_merge_if_possible(merge_unit_ids)
        if merge_successful:
            self.notify_manual_curation_updated()
            self.refresh()
        else:
            print("Merge not possible, some units are already deleted or in a merge group")
            # optional: notify.failed merge?




UnitListView._gui_help_txt = """
## Unit List

This view controls the visibility of units.

### Controls
* Check box : make visible or unvisible
* Double click on a row : make it visible alone
* Space : make selected units visible
* Press d : delete selected units (if curation=True)
* Press m : merge selected units (if curation=True)

*QT-specific*
* Drag column headers : sort columns
* Right click (QT) : context menu (delete or merge if curation=True)

*Panel-specific*
* Arrow up/down : select next/previous unit
* Arrow up/down + CTRL : select next/previous unit and make it visible alone
"""
