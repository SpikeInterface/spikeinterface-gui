import numpy as np

from .view_base import ViewBase


class CompareUnitListView(ViewBase):
    """
    View for displaying unit comparison between two analyzers.
    Shows matched units, their agreement scores, and spike counts.
    """
    id = "compareunitlist"
    _supported_backend = ['qt', 'panel']
    _depend_on = ['comparison']
    _settings = [
        {"name": "matching_mode", "type": "list", "limits": ["hungarian", "best_match"]},
    ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        # optional columns: unit properties that both sorters have, shown once per sorter
        self.shared_columns_dict = {col: False for col in controller.get_shared_unit_properties()}
        ViewBase.__init__(self, controller=controller, parent=parent, backend=backend)

    def get_shared_columns(self):
        return [col for col, visible in self.shared_columns_dict.items() if visible]

    def get_column_names(self):
        """The header of the table: the 2 units, the score, then each shared column per sorter"""
        names = [
            f'Unit ({self.controller.analyzer1_name})',
            f'Unit ({self.controller.analyzer2_name})',
            'Agreement Score',
        ]
        for col in self.get_shared_columns():
            names += [f'{col} ({self.controller.analyzer1_name})', f'{col} ({self.controller.analyzer2_name})']
        return names

    def get_shared_values(self, row):
        """The values of the shared columns of a row, in the order of get_column_names"""
        table = self.controller.units_table
        values = []
        for col in self.get_shared_columns():
            for unit_id in (row['unit_id1'], row['unit_id2']):
                value = None if unit_id is None else table.at[unit_id, col]
                values.append(None if value is None or (isinstance(value, float) and np.isnan(value)) else value)
        return values

    def get_rows(self):
        """
        One row per match pair, plus one row per unmatched unit of either analyzer,
        sorted by decreasing agreement score.

        Each row is a dict with the *combined* unit ids (or None when there is no unit on
        that side) and the numeric agreement score.
        """
        controller = self.controller

        if self.settings['matching_mode'] == 'best_match':
            matching_12, _ = controller.get_best_matching()
        else:
            matching_12, _ = controller.get_matching()
        agreement_scores = controller.get_agreement_scores()

        rows = []
        matched_original2 = set()
        for original_unit_id1 in matching_12.index:
            original_unit_id2 = matching_12[original_unit_id1]
            unit_id1 = controller.get_combined_unit_id(1, original_unit_id1)
            if controller.is_unmatched(original_unit_id2):
                # unmatched unit of analyzer1
                rows.append(dict(unit_id1=unit_id1, unit_id2=None, agreement_score=0.))
            else:
                rows.append(dict(
                    unit_id1=unit_id1,
                    unit_id2=controller.get_combined_unit_id(2, original_unit_id2),
                    agreement_score=float(agreement_scores.at[original_unit_id1, original_unit_id2]),
                ))
                matched_original2.add(original_unit_id2)

        # unmatched units of analyzer2
        for original_unit_id2 in controller.analyzer2.unit_ids:
            if original_unit_id2 in matched_original2:
                continue
            rows.append(dict(
                unit_id1=None,
                unit_id2=controller.get_combined_unit_id(2, original_unit_id2),
                agreement_score=0.,
            ))

        # best matches first, so both backends show the same order. The sort is stable,
        # so the unmatched units keep their own order at the bottom.
        rows.sort(key=lambda row: row['agreement_score'], reverse=True)

        return rows

    def on_agreement_threshold_changed(self):
        # the matching, and therefore the rows, depend on the threshold
        self.refresh()

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT

        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        # shared columns, shown with the "columns" button of the toolbar
        tree = [{'name': str(col), 'type': 'bool', 'value': v} for col, v in self.shared_columns_dict.items()]
        self.qt_shared_columns = pg.parametertree.Parameter.create(name='shared columns', type='group', children=tree)
        self.tree_shared_columns = pg.parametertree.ParameterTree(parent=self.qt_widget)
        self.tree_shared_columns.header().hide()
        self.tree_shared_columns.setParameters(self.qt_shared_columns, showTop=True)
        self.qt_shared_columns.sigTreeStateChanged.connect(self._qt_on_shared_columns_changed)
        self.layout.addWidget(self.tree_shared_columns)
        self.tree_shared_columns.hide()
        but = QT.QPushButton('columns')
        but.clicked.connect(lambda: self.tree_shared_columns.setVisible(not self.tree_shared_columns.isVisible()))
        self.qt_widget.view_toolbar.addWidget(but)

        # Create table widget
        self.table = QT.QTableWidget()
        self.layout.addWidget(self.table)

        # Setup table
        self.table.setSelectionBehavior(QT.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QT.QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._qt_on_selection_changed)

        self.table.setSortingEnabled(True)
        # Sort by Agreement Score column (index 2) by default
        self.table.sortItems(2, QT.Qt.DescendingOrder)

    def _qt_on_shared_columns_changed(self):
        for col in self.shared_columns_dict.keys():
            self.shared_columns_dict[col] = self.qt_shared_columns[col]
        self.refresh()

    def _qt_make_unit_item(self, unit_id):
        """A table item showing the unit id, its spike count and its color"""
        from .myqt import QT

        if unit_id is None:
            item = QT.QTableWidgetItem('')
            item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
            item.unit_id = None
            return item

        num_spikes = self.controller.num_spikes[unit_id]
        item = QT.QTableWidgetItem(f'{unit_id} n={num_spikes}')
        item.setData(QT.Qt.ItemDataRole.UserRole, unit_id)
        item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
        item.setIcon(self.get_unit_icon(unit_id))
        item.unit_id = unit_id
        return item

    def _qt_refresh(self):
        from .myqt import QT

        rows = self.get_rows()

        # Disable sorting while populating, otherwise rows move under us
        self.table.setSortingEnabled(False)
        self.table.clearContents()
        column_names = self.get_column_names()
        self.table.setColumnCount(len(column_names))
        self.table.setHorizontalHeaderLabels(column_names)
        self.table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            self.table.setItem(i, 0, self._qt_make_unit_item(row['unit_id1']))
            self.table.setItem(i, 1, self._qt_make_unit_item(row['unit_id2']))
            # scores are in [0, 1] and always formatted with 3 decimals, so every string
            # has the same width and the lexicographic sort of the column is the numeric one
            score_item = QT.QTableWidgetItem(f"{row['agreement_score']:.3f}")
            score_item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
            self.table.setItem(i, 2, score_item)
            for j, value in enumerate(self.get_shared_values(row)):
                item = QT.QTableWidgetItem()
                if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
                    # numbers as data, so that the column sorts numerically
                    item.setData(QT.Qt.DisplayRole, round(float(value), 4))
                elif value is not None:
                    item.setText(str(value))
                item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
                self.table.setItem(i, 3 + j, item)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self._qt_select_visible_row()

    def _qt_on_selection_changed(self):
        """Handle row selection and update unit visibility"""
        selected_rows = {item.row() for item in self.table.selectedItems()}
        if len(selected_rows) == 0:
            return
        row_idx = min(selected_rows)

        visible_unit_ids = []
        for col in (0, 1):
            item = self.table.item(row_idx, col)
            if item is not None and item.unit_id is not None:
                visible_unit_ids.append(item.unit_id)

        if len(visible_unit_ids) == 0:
            return

        current_visible_units = self.controller.get_visible_unit_ids()
        self.controller.set_visible_unit_ids(visible_unit_ids)
        if set(current_visible_units) != set(self.controller.get_visible_unit_ids()):
            self.notify_unit_and_channel_visibility_changed()

    def _qt_select_visible_row(self):
        """Highlight the row holding the currently visible units, without notifying back"""
        visible_unit_ids = set(self.controller.get_visible_unit_ids())
        if len(visible_unit_ids) == 0:
            return

        for row_idx in range(self.table.rowCount()):
            row_unit_ids = set()
            for col in (0, 1):
                item = self.table.item(row_idx, col)
                if item is not None and item.unit_id is not None:
                    row_unit_ids.add(item.unit_id)
            if visible_unit_ids.issubset(row_unit_ids):
                self.table.blockSignals(True)
                self.table.selectRow(row_idx)
                self.table.blockSignals(False)
                self.table.scrollToItem(self.table.item(row_idx, 0))
                if set(visible_unit_ids) != row_unit_ids:
                    self._qt_on_selection_changed()
                return
        # the visible units are not one row (e.g. a non matched pair): highlight nothing
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.blockSignals(False)

    def _qt_on_unit_visibility_changed(self):
        self._qt_select_visible_row()

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn

        pn.extension("tabulator")

        from .utils_panel import make_toggled_checkboxes

        self.shared_columns_toggle, self.shared_columns_select, shared_columns_box = make_toggled_checkboxes(
            "columns",
            options=list(self.shared_columns_dict.keys()),
            value=self.get_shared_columns(),
            on_change=self._panel_on_shared_columns_changed,
        )

        self._panel_create_table()

        self.layout = pn.Column(
            self.shared_columns_toggle,
            shared_columns_box,
            self.table,
            sizing_mode="stretch_both",
        )

    def _panel_create_table(self):
        import pandas as pd
        import matplotlib.colors as mcolors
        from .utils_panel import unit_formatter, SelectableTabulator

        rows = self.get_rows()

        def cell(unit_id):
            if unit_id is None:
                return None
            return {
                "id": str(unit_id),
                "color": mcolors.to_hex(self.controller.get_unit_color(unit_id)),
                "shape": self.controller.get_unit_shape(unit_id),
                "n": self.controller.num_spikes[unit_id],
            }

        column_names = self.get_column_names()
        unit1_col, unit2_col = column_names[:2]
        data = {
            unit1_col: [cell(row['unit_id1']) for row in rows],
            unit2_col: [cell(row['unit_id2']) for row in rows],
            'Agreement Score': [row['agreement_score'] for row in rows],
        }
        shared_values = [self.get_shared_values(row) for row in rows]
        for j, name in enumerate(column_names[3:]):
            data[name] = pd.Series([values[j] for values in shared_values])
        df = pd.DataFrame(data=data, index=list(range(len(rows))))
        # keep the combined unit ids out of the view, the selection callback needs them.
        # dtype=object is required: a column mixing unit ids and None would be coerced to
        # float, turning the unit ids into floats and the None into NaN
        df['_unit_id1'] = pd.Series([row['unit_id1'] for row in rows], dtype=object)
        df['_unit_id2'] = pd.Series([row['unit_id2'] for row in rows], dtype=object)

        # the comparison table is read only: nothing here can be curated, and an edit
        # from the browser would try to patch a read-only array
        editors = {col: {'type': 'editable', 'value': False} for col in df.columns}

        self.table = SelectableTabulator(
            df,
            formatters={unit1_col: unit_formatter, unit2_col: unit_formatter},
            editors=editors,
            hidden_columns=['_unit_id1', '_unit_id2'],
            sizing_mode="stretch_both",
            layout="fit_data",
            show_index=False,
            selectable=True,
            pagination=None,
            # SelectableTabulator functions
            skip_sort_columns=[unit1_col, unit2_col],
            parent_view=self,
            conditional_shortcut=self.is_view_active,
            on_selection_changed=self._panel_on_selection_changed,
            on_only_function=self._panel_on_selection_changed,
        )

    def _panel_on_shared_columns_changed(self, event):
        for col in self.shared_columns_dict.keys():
            self.shared_columns_dict[col] = col in event.new
        self.refresh()

    def _panel_on_selection_changed(self):
        selected_rows = self.table.selection
        if len(selected_rows) == 0:
            return
        df = self.table.value
        row = df.iloc[selected_rows[0]]

        visible_unit_ids = [
            unit_id for unit_id in (row['_unit_id1'], row['_unit_id2']) if unit_id is not None
        ]
        if len(visible_unit_ids) == 0:
            return

        current_visible_units = self.controller.get_visible_unit_ids()
        self.controller.set_visible_unit_ids(visible_unit_ids)
        # this runs twice when the row is selected from code (directly, then from the selection
        # watcher): notifying twice refreshes the correlograms twice and they render blank
        if set(current_visible_units) != set(self.controller.get_visible_unit_ids()):
            self.notify_unit_and_channel_visibility_changed()

    def _panel_refresh(self):
        # the rows depend on the matching, so the whole table is rebuilt
        old_panel = self.table.__panel__()
        table_index = next(i for i, obj in enumerate(self.layout.objects) if obj is old_panel)
        self._panel_create_table()
        self.layout[table_index] = self.table
        # visibility changes are skipped while the tab is hidden, so re-select on refresh (as in qt)
        self._panel_on_unit_visibility_changed()

    def _panel_on_unit_visibility_changed(self):
        # the rows themselves do not change, only which one is highlighted
        visible_unit_ids = set(self.controller.get_visible_unit_ids())
        if len(visible_unit_ids) == 0:
            return
        df = self.table.value
        for row_index in range(len(df)):
            row = df.iloc[row_index]
            row_unit_ids = {
                unit_id for unit_id in (row['_unit_id1'], row['_unit_id2']) if unit_id is not None
            }
            # subset, like in qt: picking one unit (e.g. from the probe view) selects its row
            if visible_unit_ids.issubset(row_unit_ids):
                if self.table.selection != [row_index]:
                    # the selection watcher then makes the whole pair visible
                    self.table.selection = [row_index]
                if visible_unit_ids != row_unit_ids:
                    self._panel_on_selection_changed()
                return
        # the visible units are not one row (e.g. a non matched pair): highlight nothing
        if self.table.selection != []:
            self.table.selection = []


CompareUnitListView._gui_help_txt = """
## Compare Unit List View

The unit list in comparison mode. One row per pair of matched units, plus one row per unit
that only one of the two sorters found.

The rows are sorted by decreasing agreement score, so the best matches come first and the
units that only one sorter found (score 0) come last.

The matching is done at the agreement threshold shared with the other comparison views
(set it with the slider of the unit Venn view). The table is read only: there is no curation in
comparison mode.

### Settings
- **matching_mode** : "hungarian" gives a one to one matching, "best_match" simply takes
  the best candidate for each unit of the first sorter, so a unit of the second sorter can
  appear on several rows.

### Controls
- **left click on a row** : make the units of this row visible in the other views.
- **columns** : add unit properties that both sorters have (e.g. firing rate or a quality
  label), as one column per sorter.
"""
