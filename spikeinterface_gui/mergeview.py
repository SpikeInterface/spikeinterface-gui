import numpy as np
import itertools

from .view_base import ViewBase

from .curation_tools import adding_group


class MergeView(ViewBase):
    _supported_backend = ['qt']

    _settings = [
        {"name": "method", "type": "list", "limits": ["similarity", "automerge"]},
        {"name": "similarity_threshold", "type": "float", "value": .9, "step": 0.01},
        {"name": "similarity_method", "type": "list", "limits": ["l1", "l2", "cosine"]},
        {"name": "automerge_preset", "type": "list", "limits": [
            'similarity_correlograms',
            'temporal_splits',
            'x_contaminations',
            'feature_neighbors'
            ]
        },
    ]

    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    def compute(self):
        method = self.settings['method']
        if method == 'similarity':
            similarity = self.controller.get_similarity(self.settings['similarity_method'])
            if similarity is None:
                similarity = self.controller.compute_similarity(self.settings['similarity_threshold'])
            th_sim = similarity > self.settings['similarity_threshold']
            unit_ids = self.controller.unit_ids
            self.proposed_merge_unit_groups = [[unit_ids[i], unit_ids[j]] for i, j in zip(*np.nonzero(th_sim)) if i < j]
            self.merge_info = {'similarity': similarity}
        elif method == 'automerge':
            params = {
                'preset': self.settings['automerge_preset']
            }
            self.proposed_merge_unit_groups, self.merge_info = self.controller.compute_auto_merge(**params)
        else:
            raise ValueError(f"Unknown method: {method}")
        print(f"Found {len(self.proposed_merge_unit_groups)} merge groups using {method} method:\n{self.proposed_merge_unit_groups}")
        self.refresh()

    def get_table_data(self):
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

        labels = [f"unit_id{i}" for i in range(max_group_size)] + more_labels

        rows = []
        unit_ids = list(self.controller.unit_ids)
        for group_ids in self.proposed_merge_unit_groups:
            row = {}
            # Add unit information
            for i, unit_id in enumerate(group_ids):
                row[f"unit_id{i}"] = unit_id
                row[f"unit_id{i}_color"] = self.controller.get_unit_color(unit_id)
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
    
    def _qt_on_merge_shorcut(self):
        row_ix, group_ids = self._qt_get_selected_group_ids()
        if group_ids is None:
            return
        self.accept_group_merge(group_ids)
        n_rows = self.table.rowCount()
        self.table.setCurrentCell(min(n_rows - 1, row_ix + 1), 0)

    def _qt_on_item_selection_changed(self):
        r = self._get_selected_group_ids()
        if r is None:
            return
        row_ix, group_ids = r
        if group_ids is None:
            return
        
        for k in self.controller.unit_ids:
            self.controller.unit_visible_dict[k] = False
        for unit_id in group_ids:
            self.controller.unit_visible_dict[unit_id] = True

        self.notify_unit_visibility_changed()

    def _qt_on_double_click(self, item):
        self.accept_group_merge(item.group_ids)


    def _qt_make_layout(self):
        from .myqt import QT

        self.merge_info = {}
        self.layout = QT.QVBoxLayout()

        self.sorting_column = 2
        self.sorting_direction = QT.Qt.SortOrder.AscendingOrder

        self.table = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        self.table.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.layout.addWidget(self.table)
        self.table.itemSelectionChanged.connect(self._qt_on_item_selection_changed)
        self.table.itemDoubleClicked.connect(self._qt_on_double_click)

        shortcut_merge = QT.QShortcut(self.qt_widget)
        shortcut_merge.setKey(QT.QKeySequence('m'))
        shortcut_merge.activated.connect(self._qt_on_merge_shorcut)
        self.proposed_merge_unit_groups = [] # self.controller.get_merge_list()

        self.refresh()

    def _qt_refresh(self):
        from .myqt import QT
        from .utils_qt import CustomItem

        self.table.clear()
        self.table.setSortingEnabled(False)

        labels, rows = self.get_table_data()

        for row in rows:
            print(row)

        if not rows:
            self.table.setColumnCount(0)
            self.table.setRowCount(0)
            return

        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            for c, label in enumerate(labels):
                value = row.get(label, "")
                if label.startswith("unit_id") and "_color" not in label:
                    unit_id = row.get(label)
                    color = row.get(f"{label}_color")
                    print(color)
                    pix = QT.QPixmap(16, 16)
                    pix.fill(color)
                    icon = QT.QIcon(pix)
                    item = QT.QTableWidgetItem(value)
                    item.setIcon(icon)
                else:
                    item = CustomItem(value)
                item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
                item.group_ids = row.get("group_ids", [])
                self.table.setItem(r, c, item)

        for i in range(self.table.columnCount()):
            self.table.resizeColumnToContents(i)
        self.table.setSortingEnabled(True)

    def _qt_on_spike_selection_changed(self):
        pass

    def _qt_on_unit_visibility_changed(self):
        pass

    ## PANEL
    def _panel_make_layout(self):
        from bokeh.models import ColumnDataSource
        import panel as pn
        from bokeh.models import TableColumn, DataTable

        # Create data source and table
        self.source = ColumnDataSource({})
        self.table = None
        self.table_area = pn.pane.Placeholder("No merges computed yet.", sizing_mode="stretch_width")

        self.compute_button = pn.widgets.Button(name="Compute", button_type="primary")
        self.compute_button.on_click(self.compute)

        # Create main layout with table area
        self.layout = self.table_area

        # Initial refresh
        self.refresh()

    def _panel_refresh(self):
        """Update the table with current data"""
        import pandas as pd
        labels, rows = self.core.get_table_data()
        if not rows:
            if self.table is not None:
                self.layout.pop(-1)
                self.table = None
            return

        # Prepare data for ColumnDataSource
        data = {label: [] for label in labels}
        data["group_ids"] = []

        for row in rows:
            for label in labels:
                data[label].append(row.get(label, ""))
            data["group_ids"].append(row["group_ids"])

        self.source.data = data

        # Create table if it doesn't exist
        if self.table is None:
            columns = []
            for label in labels:
                column_args = {"field": label, "title": label}
                if label.startswith("unit_id"):
                    column_args["formatter"] = HTMLTemplateFormatter(
                        template="""
                        <div style="color: <%= value %>"><%= value %></div>
                    """
                    )
                columns.append(TableColumn(**column_args))

            # Convert data to DataFrame
            df_data = []
            for i, group_ids in enumerate(data["group_ids"]):
                row = {}
                for label in labels:
                    if label.startswith("unit_id"):
                        # Get value and ensure it's a string
                        value = str(data[label][i])
                        # Get color from the original data in rows
                        unit_id = group_ids[int(label[-1])]  # Extract unit number from label
                        color = self.controller.qcolors.get(unit_id, "#FFFFFF").name()
                        # Format with color
                        row[label] = f'<span style="color: {color}">{value}</span>'
                    else:
                        row[label] = data[label][i]
                row["_group_ids"] = group_ids  # Store group_ids in DataFrame
                df_data.append(row)

            # Create DataFrame
            df = pd.DataFrame(df_data)

            # Configure columns
            column_configs = []
            for label in labels:
                config = {
                    "field": label,
                    "title": label,
                    "headerSort": True,
                    "editor": False,  # Make all columns non-editable
                }
                if label.startswith("unit_id"):
                    config["formatter"] = "html"
                column_configs.append(config)

            # Add hidden group_ids column
            column_configs.append(
                {
                    "field": "_group_ids",
                    "visible": False,
                    "headerSort": False,
                    "editor": False,
                }
            )

            # Create tabulator widget
            self.table = pn.widgets.Tabulator(
                df,
                show_index=False,
                height=400,
                sizing_mode="stretch_width",
                configuration={
                    "columns": column_configs,
                    "selectable": True,
                    "headerVisible": True,
                    "movableColumns": True,
                },
            )

            # Add click handler with double click detection
            self.table.on_click(self._on_click)
            self._last_click = None
            self._last_clicked_row = None

            self.table_area.clear()
            self.table_area.append(self.table)

    def _panel_on_spike_selection_changed(self):
        pass

    def _panel_on_unit_visibility_changed(self):
        pass

    


MergeView._gui_help_txt = """Merge proposal.
Click "compute" button to select similarity or to use the `get_potential_auto_merges` function
Click on a row to make visible a unique pair of unit.
To accept the merge : double click one onr row  or press "m" key.
"""
