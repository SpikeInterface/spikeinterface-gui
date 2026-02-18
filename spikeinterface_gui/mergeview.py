import numpy as np
import itertools

from .view_base import ViewBase

from spikeinterface.curation.auto_merge import _compute_merge_presets, _default_step_params


default_preset_list = ["similarity"] + list(_compute_merge_presets.keys())

all_presets = {}
all_presets["similarity"] = ["unit_locations", "template_similarity"]
all_presets.update(_compute_merge_presets)

class MergeView(ViewBase):
    id = "merge"
    _supported_backend = ['qt', 'panel']

    _settings = None

    _presets = [
        {
            "name": "preset",
            "type": "list",
            # set similarity to default
            "limits": default_preset_list
        }
    ]

    _preset_params = {}
    # add similarity preset parameters
    for preset_name, preset_params in all_presets.items():
        _preset_params[preset_name] = []
        for step_name in preset_params:
            for step_parameter_name, step_parameter_ in _default_step_params[step_name].items():
                parameter_dict = {
                    "name": step_name + "/" + step_parameter_name,
                    "value": step_parameter_,
                }
                if step_parameter_name == "similarity_method":
                    parameter_dict["type"] = "list"
                    parameter_dict["limits"] = ["l1", "l2", "cosine"]
                else:
                    parameter_dict["type"] = type(step_parameter_).__name__
                _preset_params[preset_name].append(parameter_dict)
    _need_compute = False

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)
        self.include_deleted = False

    def compute_potential_merges(self):
        preset = self.preset
        if self.controller.verbose:
            print(f"Computing potential merges using {preset} method")
        params_dict = {}
        params_dict["preset"] = preset

        preset_params = self.preset_params[preset]

        steps_params = {}
        for name in preset_params.keys():
            step_name, step_param = name.split("/")
            if steps_params.get(step_name) is None:
                steps_params[step_name] = {}
            steps_params[step_name][step_param] = preset_params[name]
        params_dict["steps_params"] = steps_params

        # define steps for similarity preset
        if preset == "similarity":
            params_dict["preset"] = None
            params_dict["steps"] = all_presets["similarity"]
        self.proposed_merge_unit_groups_all, self.merge_info = self.controller.compute_auto_merge(**params_dict)
        potential_merges = self.get_potential_merges()

        if self.controller.verbose:
            if len(potential_merges) == len(self.proposed_merge_unit_groups_all):
                print(f"Found {len(potential_merges)} potential merges")
            else:
                print(
                    f"Found {len(self.proposed_merge_unit_groups_all)} potential merges "
                    f"({len(potential_merges)} after filtering deleted units).")

    def get_potential_merges(self):
        # return the potential merges, considering the include deleted option
        unit_ids = list(self.controller.unit_ids)
        proposed_merge_unit_groups = []
        for group_ids in self.proposed_merge_unit_groups_all:
            if not self.include_deleted and self.controller.curation:
                deleted_unit_ids = self.controller.curation_data["removed"]
                if any(unit_id in deleted_unit_ids for unit_id in group_ids):
                    continue
            proposed_merge_unit_groups.append(group_ids)
        return proposed_merge_unit_groups

    def get_table_data(self):
        """Get data for displaying in table"""
        proposed_merge_unit_groups = self.get_potential_merges()
        if len(proposed_merge_unit_groups) == 0:
            return [], []

        max_group_size = max(len(g) for g in proposed_merge_unit_groups)
        more_labels = []
        for lbl in self.merge_info.keys():
            if max_group_size == 2:
                more_labels.append(lbl)
            else:
                more_labels.append([lbl + "_min", lbl + "_max"])

        labels = [f"unit_id{i}" for i in range(max_group_size)] + more_labels + ["group_ids"]

        rows = []
        unit_ids = list(self.controller.unit_ids)
        for group_ids in proposed_merge_unit_groups:
            row = {}
            # Add unit information
            for i, unit_id in enumerate(group_ids):
                row[f"unit_id{i}"] = unit_id
                # row[f"unit_id{i}_color"] = self.controller.get_unit_color(unit_id)
                row["group_ids"] = group_ids

            # Add pairwise metric information
            for info_name in more_labels:
                values = []
                merge_info = self.merge_info[info_name]
                if isinstance(merge_info, np.ndarray) and \
                    merge_info.shape == (len(unit_ids), len(unit_ids)):
                        for unit_id1, unit_id2 in itertools.combinations(group_ids, 2):
                            unit_ind1 = unit_ids.index(unit_id1)
                            unit_ind2 = unit_ids.index(unit_id2)
                            values.append(merge_info[unit_ind1][unit_ind2])

                        if max_group_size == 2:
                            row[info_name] = f"{values[0]:.2f}"
                        else:
                            min_, max_ = min(values), max(values)
                            row[f"{info_name}_min"] = f"{min_:.2f}"
                            row[f"{info_name}_max"] = f"{max_:.2f}"
                else:
                    if info_name in labels:
                        labels.remove(info_name)
                    elif f"{info_name}_min" in labels:
                        labels.remove(f"{info_name}_min")
                        labels.remove(f"{info_name}_max")
            rows.append(row)
        return labels, rows

    def accept_group_merge(self, group_ids):
        if not self.controller.curation:
            self.warning("You are not in 'curation' mode. Merge cannot be performed.")
            return

        success = self.controller.make_manual_merge_if_possible(group_ids)
        if not success:
            self.warning(
                "Merge could not be performed. Ensure unit ids are not removed "
                "merged, or split already."
            )
            return
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

    def _qt_on_preset_change(self):
        self.preset = self.preset_selector['preset']
        for preset in self.preset_params_selectors:
            self.preset_params_selectors[preset].setVisible(preset == self.preset)

    def _qt_on_include_deleted_change(self):
        self.include_deleted = self.include_deleted_checkbox.isChecked()
        self.refresh()

    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.proposed_merge_unit_groups_all = []

        # create presets and arguments layout
        self.preset_selector = pg.parametertree.Parameter.create(name="preset", type='group', children=self._presets)
        preset_select = pg.parametertree.ParameterTree(parent=None)
        preset_select.header().hide()
        preset_select.setParameters(self.preset_selector, showTop=True)
        preset_select.setWindowTitle(u'View options')
        preset_select.setFixedHeight(50)
        self.preset_selector.sigTreeStateChanged.connect(self._qt_on_preset_change)

        self.merge_info = {}
        self.layout = QT.QVBoxLayout()
        self.layout.addWidget(preset_select)

        self.preset_params_selectors = {}
        self.preset_params = {}
        for preset, params in self._preset_params.items():
            preset_params = pg.parametertree.Parameter.create(name="params", type='group', children=params)
            preset_tree_settings = pg.parametertree.ParameterTree(parent=None)
            preset_tree_settings.header().hide()
            preset_tree_settings.setParameters(preset_params, showTop=True)
            preset_tree_settings.setWindowTitle(u'View options')
            preset_tree_settings.setFixedHeight(100)
            self.preset_params_selectors[preset] = preset_tree_settings
            self.preset_params[preset] = preset_params
            self.layout.addWidget(preset_tree_settings)
        self.preset = self.preset_selector['preset']
        self._qt_on_preset_change()

        row_layout = QT.QHBoxLayout()

        but = QT.QPushButton('Calculate merges')
        but.clicked.connect(self._compute_merges)
        row_layout.addWidget(but)

        if self.controller.curation:
            self.include_deleted_checkbox = QT.QCheckBox("Include deleted units")
            self.include_deleted_checkbox.setChecked(False)
            self.include_deleted_checkbox.stateChanged.connect(self._qt_on_include_deleted_change)
            row_layout.addWidget(self.include_deleted_checkbox)

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

        labels, rows = self.get_table_data()
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
                elif "_color" not in label and label in row:
                    value = row[label]
                    item = CustomItem(value)
                    self.table.setItem(r, c, item)

        for i in range(self.table.columnCount()):
            self.table.resizeColumnToContents(i)
        self.table.setSortingEnabled(True)

    def _compute_merges(self):
        with self.busy_cursor():
            self.compute_potential_merges()
        proposed_merge_unit_groups = self.get_potential_merges()
        if len(proposed_merge_unit_groups) == 0:
            self.warning(f"No potential merges found with preset {self.preset}")
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

        self.proposed_merge_unit_groups_all = []

        # Create presets and arguments layout
        preset_settings = SettingsProxy(create_dynamic_parameterized(self._presets))
        self.preset_selector = pn.Param(preset_settings._parameterized, sizing_mode="stretch_width", name="Preset")
        for setting_data in self._presets:
            preset_settings._parameterized.param.watch(self._panel_on_preset_change, setting_data["name"])

        self.preset_params = {}
        self.preset_params_selectors = {}
        for preset, params in self._preset_params.items():
            preset_params = SettingsProxy(create_dynamic_parameterized(params))
            self.preset_params[preset] = preset_params
            self.preset_params_selectors[preset] = pn.Param(preset_params._parameterized, sizing_mode="stretch_width",
                                                            name=f"{preset.capitalize()} parameters")
        self.preset = list(self.preset_params.keys())[0]

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
        self.caluculate_merges_button.on_click(self._panel_compute_merges)

        calculate_list = [self.caluculate_merges_button]

        if self.controller.curation:
            self.include_deleted = pn.widgets.Checkbox(name="Include deleted units", value=False)
            self.include_deleted.param.watch(self._panel_include_deleted_change, "value")
            calculate_list.append(self.include_deleted)
        calculate_row = pn.Row(*calculate_list, sizing_mode="stretch_width")

        self.layout = pn.Column(
            # add params
            self.preset_selector, 
            self.preset_params_selectors[self.preset],
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
        labels, rows = self.get_table_data()
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

    def _panel_compute_merges(self, event):
        self._compute_merges()

    def _panel_on_preset_change(self, event):
        self.preset = event.new
        if self.is_warning_active():
            layout_index = 2
        else:
            layout_index = 1
        self.layout[layout_index] = self.preset_params_selectors[self.preset]

    def _panel_on_click(self, event):
        import panel as pn

        # set unit visibility
        row = event.row

        def _do_update():
            self.table.selection = [row]

        pn.state.execute(_do_update, schedule=True)
        self._panel_update_visible_pair(row)

    def _panel_include_deleted_change(self, event):
        self.include_deleted = event.new
        self.refresh()

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
        import panel as pn

        if event.data == "accept":
            selected = self.table.selection
            for row in selected:
                group_ids = self.table.value.iloc[row].group_ids
                self.accept_group_merge(group_ids)
            self.notify_manual_curation_updated()
        elif event.data == "next":
            next_row = min(self.table.selection[0] + 1, len(self.table.value) - 1)

            def _do_next():
                self.table.selection = [next_row]

            pn.state.execute(_do_next, schedule=True)
            self._panel_update_visible_pair(next_row)
        elif event.data == "previous":
            previous_row = max(self.table.selection[0] - 1, 0)

            def _do_prev():
                self.table.selection = [previous_row]

            pn.state.execute(_do_prev, schedule=True)
            self._panel_update_visible_pair(previous_row)

    def _panel_on_spike_selection_changed(self):
        pass

    def _panel_on_unit_visibility_changed(self):
        pass



MergeView._gui_help_txt = """
## Merge View

This view allows you to compute potential merges between units based on their similarity or using the auto merge function.
Select the preset to use for merging units.
The available presets are inherited from spikeinterface.

Click "Calculate merges" to compute the potential merges. When finished, the table will be populated 
with the potential merges.

### Controls
- **left click** : select a potential merge group
- **arrow up/down** : navigate through the potential merge groups
- **ctrl + a** : accept the selected merge group
"""
