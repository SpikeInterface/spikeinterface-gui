import numpy as np

import pyqtgraph as pg

from .view_base import ViewBase


class CompareUnitListView(ViewBase):
    """
    View for displaying unit comparison between two analyzers.
    Shows matched units, their agreement scores, and spike counts.
    """
    _supported_backend = ['qt']
    _depend_on = ['comparison']
    _gui_help_txt = "Display comparison table between two sorting outputs"
    _settings = [
        {"name": "matching_mode", "type": "list", "value": "hungarian", "options": ["hungarian", "best_match"]},
    ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent, backend=backend)
        self.unit_dtype = self.controller.unit_ids.dtype


    def _qt_make_layout(self):
        from .myqt import QT
        
        self.layout = QT.QVBoxLayout()

        # Create table widget
        self.table = QT.QTableWidget()
        self.layout.addWidget(self.table)

        # Setup table
        self.table.setSelectionBehavior(QT.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QT.QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._qt_on_selection_changed)

        # Setup table structure
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            f'Unit ({self.controller.analyzer1_name})',
            f'Unit ({self.controller.analyzer2_name})',
            'Agreement Score',
        ])
        self.table.setSortingEnabled(True)
        # Sort by Agreement Score column (index 2) by default
        self.table.sortItems(2, QT.Qt.DescendingOrder)
        self.table.setSelectionMode(QT.QAbstractItemView.SingleSelection)

    def _qt_refresh(self):
        """Populate/refresh the comparison table with data"""
        from .myqt import QT

        comp = self.controller.comp
        
        # Get comparison data
        if self.settings['matching_mode'] == 'hungarian':
            matching_12 = comp.hungarian_match_12
        else:
            matching_12 = comp.best_match_12
        matching_12 = comp.hungarian_match_12
        agreement_scores = comp.agreement_scores
        
        # Get all units from both analyzers
        all_units2 = set(self.controller.analyzer2.unit_ids)
        
        # Build rows: matched pairs + unmatched units
        rows = []
        
        # Add matched units
        for unit1_orig in matching_12.index:
            unit2_orig = matching_12[unit1_orig]
            if unit2_orig != -1:
                # Get combined unit_ids
                unit1_idx = list(self.controller.analyzer1.unit_ids).index(unit1_orig)
                unit2_idx = list(self.controller.analyzer2.unit_ids).index(unit2_orig)
                unit1 = self.controller.unit_ids1[unit1_idx]
                unit2 = self.controller.unit_ids2[unit2_idx]
                
                score = agreement_scores.at[unit1_orig, unit2_orig]
                num_spikes1 = self.controller.analyzer1.sorting.get_unit_spike_train(unit1_orig).size
                num_spikes2 = self.controller.analyzer2.sorting.get_unit_spike_train(unit2_orig).size
                
                rows.append(
                    {
                        'unit1': str(unit1),
                        'unit2': str(unit2),
                        'unit1_orig': unit1_orig,
                        'unit2_orig': unit2_orig,
                        'agreement_score': f"{score:.3f}",
                        'num_spikes1': num_spikes1,
                        'num_spikes2': num_spikes2
                    }
                )
                all_units2.discard(unit2_orig)
            else:
                # Unmatched unit from analyzer1
                unit1_idx = list(self.controller.analyzer1.unit_ids).index(unit1_orig)
                unit1 = self.controller.unit_ids1[unit1_idx]
                num_spikes1 = self.controller.analyzer1.sorting.get_unit_spike_train(unit1_orig).size
                
                rows.append({
                    'unit1': str(unit1),
                    'unit2': '',
                    'unit1_orig': unit1_orig,
                    'unit2_orig': '',
                    'agreement_score': '0',
                    'num_spikes1': num_spikes1,
                    'num_spikes2': 0
                })

        # Add unmatched units from analyzer2
        for unit2_orig in all_units2:
            unit2_idx = list(self.controller.analyzer2.unit_ids).index(unit2_orig)
            unit2 = self.controller.unit_ids2[unit2_idx]
            num_spikes2 = self.controller.analyzer2.sorting.get_unit_spike_train(unit2_orig).size
            
            rows.append({
                'unit1': '',
                'unit2': str(unit2),
                'unit1_orig': '',
                'unit2_orig': unit2_orig,
                'agreement_score': '',
                'num_spikes1': 0,
                'num_spikes2': num_spikes2
            })
        
        # Populate rows
        print(len(rows), "rows to display in comparison table")
        # Disable sorting while populating
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        
        for i, row in enumerate(rows):
            # Unit 1 column with color
            if row['unit1'] != '':
                unit1 = np.array([row['unit1']]).astype(self.unit_dtype)[0]
                n = row['num_spikes1']
                name = f'{unit1} n={n}'
                color = self.get_unit_color(unit1)
                pix = QT.QPixmap(16, 16)
                pix.fill(color)
                icon = QT.QIcon(pix)
                item1 = QT.QTableWidgetItem(name)
                item1.setData(QT.Qt.ItemDataRole.UserRole, unit1)
                item1.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
                item1.setIcon(icon)
                item1.unit1 = unit1
            else:
                item1 = QT.QTableWidgetItem('')
                item1.unit1 = ''
            self.table.setItem(i, 0, item1)
            
            # Unit 2 column with color
            if row['unit2'] != '':
                unit2 = np.array([row['unit2']]).astype(self.unit_dtype)[0]
                n = row['num_spikes2']
                name = f'{unit2} n={n}'
                color = self.get_unit_color(unit2)
                pix = QT.QPixmap(16, 16)
                pix.fill(color)
                icon = QT.QIcon(pix)
                item2 = QT.QTableWidgetItem(name)
                item2.setData(QT.Qt.ItemDataRole.UserRole, unit2)
                item2.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
                item2.setIcon(icon)
                item2.unit2 = unit2
            else:
                item2 = QT.QTableWidgetItem('')
                item2.unit2 = ''
            self.table.setItem(i, 1, item2)
            
            # Other columns
            self.table.setItem(i, 2, QT.QTableWidgetItem(row['agreement_score']))

        # Re-enable sorting after populating
        self.table.setSortingEnabled(True)
        # Resize columns
        self.table.resizeColumnsToContents()


    def _qt_on_selection_changed(self):
        """Handle row selection and update unit visibility"""
        selected_rows = []
        for item in self.table.selectedItems():
            if item.column() != 1: continue
            selected_rows.append(item.row())
        
        row_idx = selected_rows[0]
        # Get unit values from table items
        unit1_item = self.table.item(row_idx, 0)
        unit2_item = self.table.item(row_idx, 1)
        unit1 = unit1_item.unit1
        unit2 = unit2_item.unit2

        # Collect units to make visible
        visible_units = []
        
        if unit1 != '':
            visible_units.append(unit1)
        if unit2 != '':
            visible_units.append(unit2)

        # Update visibility
        if visible_units:
            self.controller.set_visible_unit_ids(visible_units)
            self.notify_unit_visibility_changed()

    def on_unit_visibility_changed(self):
        """Handle external unit visibility changes - could highlight selected row"""
        pass