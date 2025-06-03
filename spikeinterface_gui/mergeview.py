import numpy as np
import itertools

from .view_base import ViewBase


class MergeView(ViewBase):
    _supported_backend = ['qt', 'panel']

    _settings = None

    _methods = [{"name": "method", "type": "list", "limits": ["similarity", "automerge"]}]

    _method_params = {
        "similarity": [
            {"name": "similarity_threshold", "type": "float", "value": .9, "step": 0.01},
            {"name": "similarity_method", "type": "list", "limits": ["l1", "l2", "cosine"]},
        ],
        "automerge": [
            {"name": "automerge_preset", "type": "list", "limits": [
                'similarity_correlograms',
                'temporal_splits',
                'x_contaminations',
                'feature_neighbors'
            ]}
        ]
    }

    _need_compute = False

    def __init__(self, controller=None, parent=None, backend="qt"):
        if controller.has_extension("template_similarity"):
            similarity_ext = controller.analyzer.get_extension("template_similarity")
            similarity_method = similarity_ext.params["method"]
            self._method_params["similarity"][1]["value"] = similarity_method
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    def get_potential_merges(self):
        method = self.method
        if self.controller.verbose:
            print(f"Computing potential merges using {method} method")
        if method == 'similarity':
            similarity_params = self.method_params['similarity']
            similarity = self.controller.get_similarity(similarity_params['similarity_method'])
            if similarity is None:
                similarity = self.controller.compute_similarity(similarity_params['similarity_method'])
            th_sim = similarity > similarity_params['similarity_threshold']
            unit_ids = self.controller.unit_ids
            self.proposed_merge_unit_groups = [[unit_ids[i], unit_ids[j]] for i, j in zip(*np.nonzero(th_sim)) if i < j]
            self.merge_info = {'similarity': similarity}
        elif method == 'automerge':
            automerge_params = self.method_params['automerge']
            params = {
                'preset': automerge_params['automerge_preset']
            }
            self.proposed_merge_unit_groups, self.merge_info = self.controller.compute_auto_merge(**params)
        else:
            raise ValueError(f"Unknown method: {method}")
        if self.controller.verbose:
            print(f"Found {len(self.proposed_merge_unit_groups)} merge groups using {method} method")

    def get_table_data(self, include_deleted=False):
        """Get data for displaying in table"""
        if not self.proposed_merge_unit_groups:
            return [], []

        max_group_size = max(len(g) for g in self.proposed_merge_unit_groups)
        potential_labels = {"similarity", "correlogram_diff", "templates_diff"}
        more_labels = []
        for lbl in self.merge_info.keys():
            if lbl in potential_labels:
                if max_group_size == 2:
                    more_labels.append(lbl)
                else:
                    more_labels.append([lbl + "_min", lbl + "_max"])

        labels = [f"unit_id{i}" for i in range(max_group_size)] + more_labels + ["group_ids"]

        rows = []
        unit_ids = list(self.controller.unit_ids)
        for group_ids in self.proposed_merge_unit_groups:
            if not include_deleted and self.controller.curation:
                deleted_unit_ids = self.controller.curation_data["removed_units"]
                if any(unit_id in deleted_unit_ids for unit_id in group_ids):
                    continue

            row = {}
            # Add unit information
            for i, unit_id in enumerate(group_ids):
                row[f"unit_id{i}"] = unit_id
                # row[f"unit_id{i}_color"] = self.controller.get_unit_color(unit_id)
                row["group_ids"] = group_ids

            # Add metrics information
            for info_name in more_labels:
                values = []
                for unit_id1, unit_id2 in itertools.combinations(group_ids, 2):
                    unit_ind1 = unit_ids.index(unit_id1)
                    unit_ind2 = unit_ids.index(unit_id2)
                    values.append(self.merge_info[info_name][unit_ind1][unit_ind2])

                if max_group_size == 2:
                    row[info_name] = f"{values[0]:.2f}"
                else:
                    min_, max_ = min(values), max(values)
                    row[f"{info_name}_min"] = f"{min_:.2f}"
                    row[f"{info_name}_max"] = f"{max_:.2f}"
            rows.append(row)
        return labels, rows

    def accept_group_merge(self, group_ids):
        self.controller.make_manual_merge_if_possible(group_ids)
        self.notify_manual_curation_updated()
        self.refresh()

    ### QT
    def _qt_get_selected_group_ids(self):
        inds = self.table.selectedIndexes()
        if len(inds) != self.table.columnCount():
            row_ix = None
        else:
            row_ix = inds[0].row()
        if row_ix is None:
            return None, None
        item = self.table.item(row_ix, 0)
        group_ids = item.group_ids
        return row_ix, group_ids

    def _qt_on_accept_shorcut(self):
        row_ix, group_ids = self._qt_get_selected_group_ids()
        if group_ids is None:
            return
        self.accept_group_merge(group_ids)
        n_rows = self.table.rowCount()
        self.table.setCurrentCell(min(n_rows - 1, row_ix + 1), 0)

    def _qt_on_item_selection_changed(self):
        r = self._qt_get_selected_group_ids()
        if r is None:
            return
        row_ix, group_ids = r
        if group_ids is None:
            return
        
        self.controller.set_visible_unit_ids(group_ids)

        self.notify_unit_visibility_changed()

    def _qt_on_double_click(self, item):
        self.accept_group_merge(item.group_ids)

    def _qt_on_method_change(self):
        self.method = self.method_selector['method']
        for method in self.method_params_selectors:
            self.method_params_selectors[method].setVisible(method == self.method)
        

    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.proposed_merge_unit_groups = []

        # create method and arguments layout
        self.method_selector = pg.parametertree.Parameter.create(name="method", type='group', children=self._methods)
        method_select = pg.parametertree.ParameterTree(parent=None)
        method_select.header().hide()
        method_select.setParameters(self.method_selector, showTop=True)
        method_select.setWindowTitle(u'View options')
        method_select.setFixedHeight(50)
        self.method_selector.sigTreeStateChanged.connect(self._qt_on_method_change)

        self.merge_info = {}
        self.layout = QT.QVBoxLayout()
        self.layout.addWidget(method_select)

        self.method_params_selectors = {}
        self.method_params = {}
        for method, params in self._method_params.items():
            method_params = pg.parametertree.Parameter.create(name="params", type='group', children=params)
            method_tree_settings = pg.parametertree.ParameterTree(parent=None)
            method_tree_settings.header().hide()
            method_tree_settings.setParameters(method_params, showTop=True)
            method_tree_settings.setWindowTitle(u'View options')
            method_tree_settings.setFixedHeight(100)
            self.method_params_selectors[method] = method_tree_settings
            self.method_params[method] = method_params
            self.layout.addWidget(method_tree_settings)
        self.method = self.method_selector['method']
        self._qt_on_method_change()

        row_layout = QT.QHBoxLayout()

        but = QT.QPushButton('Calculate merges')
        but.clicked.connect(self._qt_calculate_potential_automerge)
        row_layout.addWidget(but)

        if self.controller.curation:
            self.include_deleted = QT.QCheckBox("Include deleted units")
            self.include_deleted.setChecked(False)
            row_layout.addWidget(self.include_deleted)

        self.layout.addLayout(row_layout)

        self.sorting_column = 2
        self.sorting_direction = QT.Qt.SortOrder.AscendingOrder

        self.table = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        self.table.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.layout.addWidget(self.table)
        self.table.itemSelectionChanged.connect(self._qt_on_item_selection_changed)

        shortcut_accept = QT.QShortcut(self.qt_widget)
        shortcut_accept.setKey(QT.QKeySequence('ctrl+a'))
        shortcut_accept.activated.connect(self._qt_on_accept_shorcut)

        self.refresh()

    def _qt_refresh(self):
        from .myqt import QT
        from .utils_qt import CustomItem

        self.table.clear()
        self.table.setSortingEnabled(False)

        include_deleted = self.include_deleted.isChecked() if self.controller.curation else False
        labels, rows = self.get_table_data(include_deleted=include_deleted)
        if "group_ids" in labels:
            labels.remove("group_ids")

        if not rows:
            self.table.setColumnCount(0)
            self.table.setRowCount(0)
            return

        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            for c, label in enumerate(labels):
                if label.startswith("unit_id"):
                    unit_id = row[label]
                    n = self.controller.num_spikes[unit_id]
                    name = f'{unit_id} n={n}'
                    color = self.get_unit_color(unit_id)
                    pix = QT.QPixmap(16, 16)
                    pix.fill(color)
                    icon = QT.QIcon(pix)
                    item = QT.QTableWidgetItem(name)
                    item.setData(QT.Qt.ItemDataRole.UserRole, unit_id)
                    item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
                    self.table.setItem(r, c, item)
                    item.setIcon(icon)
                    item.group_ids = row.get("group_ids", [])
                elif "_color" not in label:
                    value = row[label]
                    item = CustomItem(value)
                    self.table.setItem(r, c, item)

        for i in range(self.table.columnCount()):
            self.table.resizeColumnToContents(i)
        self.table.setSortingEnabled(True)

    def _qt_calculate_potential_automerge(self):
        self.get_potential_merges()
        self.refresh()

    def _qt_on_spike_selection_changed(self):
        pass

    def _qt_on_unit_visibility_changed(self):
        pass

    ## PANEL
    def _panel_make_layout(self):
        import panel as pn
        from .utils_panel import KeyboardShortcut, KeyboardShortcuts
        from .backend_panel import create_dynamic_parameterized, SettingsProxy

        pn.extension("tabulator")

        self.proposed_merge_unit_groups = []

        # Create method and arguments layout
        method_settings = SettingsProxy(create_dynamic_parameterized(self._methods))
        self.method_selector = pn.Param(method_settings._parameterized, sizing_mode="stretch_width", name="Method")
        for setting_data in self._methods:
            method_settings._parameterized.param.watch(self._panel_on_method_change, setting_data["name"])

        self.method_params = {}
        self.method_params_selectors = {}
        for method, params in self._method_params.items():
            method_params = SettingsProxy(create_dynamic_parameterized(params))
            self.method_params[method] = method_params
            self.method_params_selectors[method] = pn.Param(method_params._parameterized, sizing_mode="stretch_width",
                                                            name=f"{method.capitalize()} parameters")
        self.method = list(self.method_params.keys())[0]

        # shortcuts
        shortcuts = [
            KeyboardShortcut(name="accept", key="a", ctrlKey=True),
            KeyboardShortcut(name="next", key="ArrowDown", ctrlKey=False),
            KeyboardShortcut(name="previous", key="ArrowUp", ctrlKey=False),
        ]
        shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        shortcuts_component.on_msg(self._panel_handle_shortcut)

        # Create data source and table
        self.table = None
        self.table_area = pn.pane.Placeholder("No merges computed yet.", height=400)

        self.caluculate_merges_button = pn.widgets.Button(name="Calculate merges", button_type="primary", sizing_mode="stretch_width")
        self.caluculate_merges_button.on_click(self._panel_calculate_merges)

        calculate_list = [self.caluculate_merges_button]

        if self.controller.curation:
            self.include_deleted = pn.widgets.Checkbox(name="Include deleted units", value=False)
            calculate_list.append(self.include_deleted)
        calculate_row = pn.Row(*calculate_list, sizing_mode="stretch_width")

        self.layout = pn.Column(
            # add params
            self.method_selector, 
            self.method_params_selectors[self.method],
            calculate_row,
            self.table_area,
            shortcuts_component,
            scroll=True,
            sizing_mode="stretch_width",
        )


    def _panel_refresh(self):
        """Update the table with current data"""
        import pandas as pd
        import panel as pn
        import matplotlib.colors as mcolors
        from .utils_panel import unit_formatter

        pn.extension("tabulator")
        # Create table
        include_deleted = self.include_deleted.value if self.controller.curation else False
        labels, rows = self.get_table_data(include_deleted=include_deleted)
        # set unmutable data
        data = {label: [] for label in labels}
        for row in rows:
            for label in labels:
                if label.startswith("unit_id"):
                    unit_id = row[label]
                    data[label].append({"id": unit_id, "color": mcolors.to_hex(self.controller.get_unit_color(unit_id))})
                else:
                    data[label].append(row[label])

        df = pd.DataFrame(data=data)
        formatters = {label: unit_formatter for label in labels if label.startswith("unit_id")}
        self.table = pn.widgets.Tabulator(
            df,
            formatters=formatters,
            height=400,
            layout="fit_data",
            show_index=False,
            hidden_columns=["group_ids"],
            disabled=True,
            selectable=1,
            sortable=False
        )

        # Add click handler with double click detection
        self.table.on_click(self._panel_on_click)
        self.table_area.update(self.table)

    def _panel_calculate_merges(self, event):
        import panel as pn
        self.table_area.update(pn.indicators.LoadingSpinner(size=50, value=True))
        self.get_potential_merges()
        self.refresh()

    def _panel_on_method_change(self, event):
        self.method = event.new
        self.layout[1] = self.method_params_selectors[self.method]

    def _panel_on_click(self, event):
        # set unit visibility
        row = event.row
        self.table.selection = [row]
        self._panel_update_visible_pair(row)

    def _panel_update_visible_pair(self, row):
        table_row = self.table.value.iloc[row]
        visible_unit_ids = []
        for name, value in zip(table_row.index, table_row):
            if name.startswith("unit_id"):
                unit_id = value["id"]
                visible_unit_ids.append(unit_id)
        self.controller.set_visible_unit_ids(visible_unit_ids)
        self.notify_unit_visibility_changed()

    def _panel_handle_shortcut(self, event):
        if event.data == "accept":
            selected = self.table.selection
            for row in selected:
                group_ids = self.table.value.iloc[row].group_ids
                self.accept_group_merge(group_ids)
            self.notify_manual_curation_updated()
        elif event.data == "next":
            next_row = min(self.table.selection[0] + 1, len(self.table.value) - 1)
            self.table.selection = [next_row]
            self._panel_update_visible_pair(next_row)
        elif event.data == "previous":
            previous_row = max(self.table.selection[0] - 1, 0)
            self.table.selection = [previous_row]
            self._panel_update_visible_pair(previous_row)

    def _panel_on_spike_selection_changed(self):
        pass

    def _panel_on_unit_visibility_changed(self):
        pass



MergeView._gui_help_txt = """
## Merge View

This view allows you to compute potential merges between units based on their similarity or using the auto merge function.
Select the method to use for merging units.
The available methods are:
- similarity: Computes the similarity between units based on their features.
- automerge: uses the auto merge function in SpikeInterface to find potential merges.

Click "Calculate merges" to compute the potential merges. When finished, the table will be populated 
with the potential merges.

### Controls
- **left click** : select a potential merge group
- **arrow up/down** : navigate through the potential merge groups
- **ctrl + a** : accept the selected merge group
"""
