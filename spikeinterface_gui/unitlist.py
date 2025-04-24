import warnings
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
        self.controller.set_all_unit_visibility_off()
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
        # self._qt_full_table_refresh()
        
    
    def _qt_full_table_refresh(self):
        # TODO sam make this faster

        from .myqt import QT
        from .utils_qt import OrderableCheckItem, CustomItem, UnitTableDelegate

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
            self.label_columns = list(range(n_first, n_first + num_labels))
            self.label_definitions_by_cols = {}
            if label_definitions is not None:
                for ix, (category, label_def) in enumerate(label_definitions.items()):
                    # label = self.controller.get_unit_label(unit_id, category)
                    # item = LabelComboBox(i, category, label_def['label_options'], parent=self.qt_widget)
                    # item.set_label(label)
                    # item.remove_label_clicked.connect(self._qt_on_remove_label)
                    # item.label_changed.connect(self._qt_on_label_changed)
                    # self.table.setCellWidget(i, n_first + ix, item)

                    col = self.label_columns[ix]
                    self.label_definitions_by_cols[col] = category
                    label = self.controller.get_unit_label(unit_id, category)
                    label = label if label is not None else ''
                    item = QT.QTableWidgetItem( f'{label}')
                    self.table.setItem(i, n_first + ix, item)
            delegate = UnitTableDelegate(parent=self.table, label_definitions=label_definitions, label_columns=self.label_columns)
            self.table.setItemDelegate(delegate)

                
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

    # def _qt_on_label_changed(self, unit_index, category, new_label):
    #     unit_id = self.controller.unit_ids[unit_index]
    #     self.controller.set_label_to_unit(unit_id, category, new_label)

    def _qt_on_remove_label(self, unit_index, category):
        unit_id = self.controller.unit_ids[unit_index]
        self.controller.set_label_to_unit(unit_id, category, None)

    def _qt_on_item_changed(self, item):
        from .myqt import QT

        col = item.column()
        if col == 1:
            # visibility checkbox
            # sel = {QT.Qt.Unchecked : False, QT.Qt.Checked : True}[item.checkState()]
            unit_id = item.unit_id
            self.controller.unit_visible_dict[unit_id] = bool(item.checkState())
            self.notify_unit_visibility_changed()
        elif col in self.label_columns:
            # label combobox
            category = self.label_definitions_by_cols[col]
            row = item.row()
            new_label = self.table.item(row, col).text()
            print(category, new_label)
            if new_label == '':
                new_label = None
            unit_id = self.controller.unit_ids[row]
            self.controller.set_label_to_unit(unit_id, category, new_label)

    
    def _qt_on_double_clicked(self, row, col):
        self.controller.set_all_unit_visibility_off()

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
        self.controller.set_all_unit_visibility_off()
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
            warnings.warn("Merge not possible, some units are already deleted or in a merge group")
            # optional: notify.failed merge?




    ## panel zone ##
    def _panel_make_layout(self):
        import panel as pn
        import pandas as pd
        import matplotlib.colors as mcolors
        from bokeh.models.widgets.tables import BooleanFormatter, SelectEditor
        from .utils_panel import unit_formatter, KeyboardShortcut, KeyboardShortcuts, SelectableTabulator

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
                data[label] = [""] * len(unit_ids)
                # pre-populate labels with existing curation
                for unit_index, unit_id in enumerate(unit_ids):
                    label_value = self.controller.get_unit_label(unit_id, label)
                    data[label][unit_index] = label_value
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

        self.df_full = pd.DataFrame(
            data=data,
            index=unit_ids
        )
        formatters = {
            "unit_id": unit_formatter,
            "visible": BooleanFormatter()
        }
        editors = {}

        for col in self.df_full.columns:
            if col != "visible":
                editors[col] = {'type': 'editable', 'value': False}
        if self.label_definitions is not None:
            for label in self.label_definitions:
                editors[label] = SelectEditor(options=[""] + list(self.label_definitions[label]['label_options']))

        # Here we make a copy so we can filter the data
        self.df = self.df_full.copy()
        self.table = SelectableTabulator(
            self.df,
            formatters=formatters,
            frozen_columns=frozen_columns,
            sizing_mode="stretch_both",
            layout="fit_data",
            show_index=False,
            selectable=True,
            editors=editors,
            pagination=None,
            # SelectableTabulator functions
            parent_view=self,
            refresh_table_function=self.refresh,
            conditional_shortcut=self.is_view_active,
            on_only_function=self._panel_on_only_selection,
            column_callbacks={"visible": self._panel_on_visible_changed},
        )

        self.select_all_button = pn.widgets.Button(name="Select All", button_type="default")
        self.unselect_all_button = pn.widgets.Button(name="Unselect All", button_type="default")
        self.refresh_button = pn.widgets.Button(name="↻", button_type="default")

        button_list = [
            self.select_all_button,
            self.unselect_all_button,
            self.refresh_button
        ]

        if self.controller.curation:
            self.delete_button = pn.widgets.Button(name="Delete", button_type="default")
            self.merge_button = pn.widgets.Button(name="Merge", button_type="default")
            # self.hide_noise = pn.widgets.Toggle(name="Show/Hide Noise", button_type="default")

            # if "quality" in self.label_definitions:
            #     self.show_only = pn.widgets.Select(
            #         name="Show only",
            #         options=["all"] + list(self.label_definitions["quality"]['label_options']),
            #         sizing_mode="stretch_width",
            #     )
            # else:
            #     self.show_only = None

            # self.hide_noise.param.watch(self._panel_on_hide_noise, 'value')
            # self.show_only.param.watch(self._panel_on_show_only, 'value')

            curation_row = pn.Row(
                self.delete_button,
                self.merge_button,
                # self.hide_noise,
                # self.show_only,
                sizing_mode="stretch_width",
            )

        self.info_text = pn.pane.HTML("")

        buttons = pn.Row(*button_list, sizing_mode="stretch_width")

        # shortcuts
        shortcuts = [KeyboardShortcut(name="visible", key=" ", ctrlKey=False),]
        if self.controller.curation:
            shortcuts.extend(
                [
                    KeyboardShortcut(name="delete", key="d", ctrlKey=True),
                    KeyboardShortcut(name="merge", key="m", ctrlKey=True),
                ]
            )
        if self.controller.has_default_quality_labels:
            shortcuts.extend(
                [
                    KeyboardShortcut(name="good", key="g", ctrlKey=False),
                    KeyboardShortcut(name="mua", key="m", ctrlKey=False),
                    KeyboardShortcut(name="noise", key="n", ctrlKey=False),
                ]
            )
        shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        shortcuts_component.on_msg(self._panel_handle_shortcut)

        self.layout = pn.Column(
            pn.Row(
                self.info_text,
            ),
            buttons,
            sizing_mode="stretch_width",
        )
        if self.controller.curation:
            self.layout.append(curation_row)
        self.layout.append(self.table)
        self.layout.append(shortcuts_component)

        self.table.tabulator.on_edit(self._panel_on_edit)

        self.select_all_button.on_click(self._panel_select_all)
        self.unselect_all_button.on_click(self._panel_unselect_all)
        self.refresh_button.on_click(self._panel_refresh_click)

        if self.controller.curation:
            self.delete_button.on_click(self._panel_delete_unit_callback)
            self.merge_button.on_click(self._panel_merge_units_callback)

    def _panel_refresh_click(self, event):
        self.df = self.df_full.copy()
        self.table.selection = []
        self.table.value = self.df
        self.table.sorters = []
        self.refresh()
        self.notifier.notify_active_view_updated()

    def _panel_refresh(self):
        df = self.table.value
        visible = []
        for unit_id in df.index.values:
            visible.append(self.controller.unit_visible_dict.get(unit_id, False))
        df.loc[:, "visible"] = visible

        table_columns = self.df.columns

        for table_col in table_columns:
            if table_col not in self.main_cols + self.controller.displayed_unit_properties:
                df.drop(columns=[table_col], inplace=True)

        for col in self.controller.displayed_unit_properties:
            if col not in table_columns:
                self.table.hidden_columns.append(col)

        self.table.value = df
        self._panel_refresh_header()

    def _panel_refresh_header(self):
        unit_ids = self.controller.unit_ids
        n1 = len(unit_ids)
        n2 = sum(self.controller.unit_visible_dict.values())
        n3 = len(self.table.selection)
        txt = f"<b>All units</b>: {n1} - <b>visible</b>: {n2} - <b>selected</b>: {n3}"
        self.info_text.object = txt

    def _panel_select_all(self, event):
        self.show_all()
        self.notifier.notify_active_view_updated()

    def _panel_unselect_all(self, event):
        self.hide_all()
        self.notifier.notify_active_view_updated()

    def _panel_delete_unit_callback(self, event):
        self._panel_delete_unit()
        self.notifier.notify_active_view_updated()

    def _panel_merge_units_callback(self, event):
        self._panel_merge_units()
        self.notifier.notify_active_view_updated()

    def _panel_on_visible_changed(self, row):
        unit_ids = self.df.index.values
        selected_unit_id = unit_ids[row]
        self.controller.unit_visible_dict[selected_unit_id] = True
        # update the visible column
        df = self.table.value
        df.loc[:, "visible"] = list(self.controller.unit_visible_dict.values())
        self.table.value = df
        self.notify_unit_visibility_changed()

    def _panel_on_unit_visibility_changed(self):
        # update selection to match visible units
        visible_units = self.controller.get_visible_unit_ids()
        unit_ids = list(self.df.index.values)
        rows_to_select = [unit_ids.index(unit_id) for unit_id in visible_units if unit_id in unit_ids]
        self.table.selection = rows_to_select
        self.refresh()

    def _panel_on_edit(self, event):
        column = event.column
        if self.label_definitions is not None and column in self.label_definitions:
            row = event.row
            unit_index = self.table._get_sorted_indices()[row]
            unit_id = self.df.index[unit_index]
            new_label = event.value
            if new_label == "":
                new_label = None
            self.controller.set_label_to_unit(unit_id, column, new_label)
        self.notifier.notify_active_view_updated()

    def _panel_on_only_selection(self):
        self.controller.set_all_unit_visibility_off()
        selected_unit = self.table.selection[0]
        unit_id = self.df.index.values[selected_unit]
        self.controller.unit_visible_dict[unit_id] = True
        # update the visible column
        df = self.table.value
        df.loc[:, "visible"] = list(self.controller.unit_visible_dict.values())
        self.table.value = df
        self.notify_unit_visibility_changed()

    def _panel_get_selected_unit_ids(self):
        return self.table._get_selected_rows(sort_with_sorters=False)

    def _panel_delete_unit(self):
        removed_unit_ids = self.get_selected_unit_ids()
        self.controller.make_manual_delete_if_possible(removed_unit_ids)
        self.notify_manual_curation_updated()
        self.refresh()

    def _panel_merge_units(self):
        merge_unit_ids = self.get_selected_unit_ids()
        merge_successful = self.controller.make_manual_merge_if_possible(merge_unit_ids)
        if merge_successful:
            self.notify_manual_curation_updated()
            self.refresh()
        else:
            print("Merge not possible, some units are already deleted or in a merge group")
            # optional: notify.failed merge?

    def _panel_handle_shortcut(self, event):
        if self.is_view_active():
            if event.data in ["delete", "merge", "good", "mua", "noise"]:
                if not self.controller.curation:
                    return
            if event.data == "delete":
                self._panel_delete_unit()
            elif event.data == "merge":
                if self.controller.curation:
                    self._panel_merge_units()
            elif event.data == "visible":
                selected_rows = self._panel_get_selected_unit_ids()
                self.controller.set_all_unit_visibility_off()
                for unit_id in self.df.index.values[selected_rows]:
                    self.controller.unit_visible_dict[unit_id] = True
                self.notify_unit_visibility_changed()
                self.refresh()
            elif event.data == "good":
                selected_rows = self._panel_get_selected_unit_ids()
                if len(selected_rows) > 0:
                    unit_ids = self.df.index.values[selected_rows]
                    for unit_id in unit_ids:
                        self.controller.set_label_to_unit(unit_id, "quality", "good")
                    self.df.loc[unit_ids, "quality"] = "good"
                    self.refresh()
            elif event.data == "mua":
                selected_rows = self._panel_get_selected_unit_ids()
                if len(selected_rows) > 0:
                    unit_ids = self.df.index.values[selected_rows]
                    for unit_id in unit_ids:
                        self.controller.set_label_to_unit(unit_id, "quality", "MUA")
                    self.df.loc[unit_ids, "quality"] = "MUA"
                    self.refresh()
            elif event.data == "noise":
                selected_rows = self._panel_get_selected_unit_ids()
                if len(selected_rows) > 0:
                    unit_ids = self.df.index.values[selected_rows]
                    for unit_id in unit_ids:
                        self.controller.set_label_to_unit(unit_id, "quality", "noise")
                    self.df.loc[unit_ids, "quality"] = "noise"
                    self.refresh()



UnitListView._gui_help_txt = """
## Unit List

This view controls the visibility of units.

### Controls
* **check box** : make visible or unvisible
* **double click** : make it visible alone
* **space** : make selected units visible
* **arrow up/down** : select next/previous unit
* **ctrl + arrow up/down** : select next/previous unit and make it visible alone
* **press 'ctrl+d'** : delete selected units (if curation=True)
* **press 'ctrl+m'** : merge selected units (if curation=True)
* **press 'g'** : label selected units as good (if curation=True)
* **press 'm'** : label selected units as mua (if curation=True)
* **press 'n'** : label selected units as noise (if curation=True)
* **drag column headers** : reorder columns
* **click on column header** : sort by this column
* **"↻"** : reset the unit table
"""
