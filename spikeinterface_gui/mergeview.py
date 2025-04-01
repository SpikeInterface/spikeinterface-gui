import numpy as np
import itertools

from .view_base import ViewBase

from .curation_tools import adding_group


class MergeView(ViewBase):
    _supported_backend = ['qt']

    _automerge_params = [
        {'name': 'preset', 'type': 'list', 'limits': [
            'similarity_correlograms', 'temporal_splits', 'x_contaminations', 'feature_neighbors'
            ]
        },
    ]

    _similarity_params = [
        {'name': 'threshold_similarity', 'type': 'float', 'value': .9, 'step': 0.01},
        {'name': 'method', 'type': 'list', 'limits': ['l1', 'l2', 'cosine']},
    ]

    _need_compute = True

    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)


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
        self.table.itemSelectionChanged.connect(self.on_item_selection_changed)
        self.table.itemDoubleClicked.connect(self._qt_on_double_click)

        shortcut_merge = QT.QShortcut(self.qt_widget)
        shortcut_merge.setKey(QT.QKeySequence('m'))
        shortcut_merge.activated.connect(self.on_merge_shorcut)
        self.proposed_merge_unit_groups = [] # self.controller.get_merge_list()

        self.refresh()

    def _get_selected_row(self):
        inds = self.table.selectedIndexes()
        if len(inds) != self.table.columnCount():
            return
        return inds[0].row()

    def _get_selected_group_ids(self):
        row_ix = self._get_selected_row()
        if row_ix is None:
            return None, None
        item = self.table.item(row_ix, 0)
        group_ids = item.group_ids
        return row_ix, group_ids

    def _qt_on_double_click(self, item):
        self.accept_group_merge(item.group_ids)
    
    def on_merge_shorcut(self):
        row_ix, group_ids = self._get_selected_group_ids()
        if group_ids is None:
            return
        self.accept_group_merge(group_ids)
        n_rows = self.table.rowCount()
        self.table.setCurrentCell(min(n_rows - 1, row_ix + 1), 0)

    def accept_group_merge(self, group_ids):
        self.controller.make_manual_merge_if_possible(group_ids)
        self.notify_manual_curation_updated()
        self.refresh()

    def on_item_selection_changed(self):
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

    def open_context_menu(self):
        self.menu.popup(self.cursor().pos())

    def _qt_refresh(self):
        from .myqt import QT
        from .utils_qt import CustomItem
        

        self.table.clear()
        self.table.setSortingEnabled(False)

        if self.proposed_merge_unit_groups is None or len(self.proposed_merge_unit_groups) == 0:
            self.table.setColumnCount(0)
            self.table.setRowCount(0)
            return


        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 100)


        max_group_size = max(len(g) for g in self.proposed_merge_unit_groups)

        potential_labels = {'similarity', 'correlogram_diff', 'templates_diff'}
        more_labels = []
        for lbl in self.merge_info.keys():
            if lbl in potential_labels:
                if max_group_size == 2:
                    more_labels.append(lbl)
                else:
                    more_labels.append([lbl+"_min", lbl+"_max"])

        labels = [f'unit_id{i}' for i in range(max_group_size)] + more_labels

        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)

        self.table.setRowCount(len(self.proposed_merge_unit_groups))
        
        print("self.proposed_merge_unit_groups", self.proposed_merge_unit_groups)

        for r in range(len(self.proposed_merge_unit_groups)):
            group_ids = self.proposed_merge_unit_groups[r]

            for c, unit_id in enumerate(group_ids):
                color = self.get_unit_color(unit_id)
                pix = QT.QPixmap(16, 16)
                pix.fill(color)
                icon = QT.QIcon(pix)

                # TODO
                #  name = '{} (n={})'.format(k, self.controller.cluster_count[k])
                n = self.controller.num_spikes[unit_id]
                name = f'{unit_id} n={n}'
                item = QT.QTableWidgetItem(name)
                item.setData(QT.Qt.ItemDataRole.UserRole, unit_id)
                item.setFlags(QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable)
                self.table.setItem(r, c, item)
                item.setIcon(icon)
                item.group_ids = group_ids

            # TODO similarity

            unit_ids = list(self.controller.unit_ids)
            for c_ix, info_name in enumerate(more_labels):
                # take all values in group and make min max
                values = []
                for unit_id1, unit_id2 in itertools.combinations(group_ids, 2):
                    unit_ind1 = unit_ids.index(unit_id1)
                    unit_ind2 = unit_ids.index(unit_id2)
                    values.append(self.merge_info[info_name][unit_ind1][unit_ind2])
                
                if max_group_size == 2:
                    # only pair, display value
                    value = values[0]
                    item = CustomItem(f'{value:.2f}')
                    self.table.setItem(r, c_ix + max_group_size, item)
                else:
                    # display mix max
                    min_, max_ = min(values), max(values)
                    item = CustomItem(f'{min_:.2f}')
                    self.table.setItem(r, c_ix//2 + max_group_size, item)
                    item = CustomItem(f'{min_:.2f}')
                    self.table.setItem(r, c_ix//2 + 1 + max_group_size, item)
                

        for i in range(self.table.columnCount()):
            self.table.resizeColumnToContents(i)
        self.table.setSortingEnabled(True)

    def on_spike_selection_changed(self):
        pass

    def on_colors_changed(self):
        self.refresh()

    def on_unit_visibility_changed(self):
        pass

    def compute(self):
        from .utils_qt import ParamDialog
        # First we choose the method

        methods = {'name': 'method', 'type': 'list', 'limits': ['similarity', 'automerge']}
        ch_method_d = ParamDialog([methods], title='Choose your method').get()
        if ch_method_d is None:
            return
        ch_method = ch_method_d['method']

        # Depending on the method we set the parameters
        if ch_method == 'automerge':
            params = ParamDialog(self._automerge_params, title='Automerge parameters').get()
            self.proposed_merge_unit_groups, self.merge_info = self.controller.compute_auto_merge(**params)
            # print(self.proposed_merge_unit_groups, self.merge_info)

        elif ch_method == 'similarity':
            
            params = ParamDialog(self._similarity_params, title='Similarity parameters').get()
            similarity = self.controller.get_similarity(params['method'])
            if similarity is None:
                similarity = self.controller.compute_similarity(params['method'])
            th_sim = similarity > params['threshold_similarity']
            unit_ids = self.controller.unit_ids
            self.proposed_merge_unit_groups = [[unit_ids[i], unit_ids[j]] for i, j in zip(*np.nonzero(th_sim)) if i < j]
            self.merge_info = {'similarity': similarity}

        self.refresh()





MergeView._gui_help_txt = """Merge proposal.
Click "compute" button to select similarity or to use the `get_potential_auto_merges` function
Click on a row to make visible a unique pair of unit.
To accept the merge : double click one onr row  or press "m" key.
"""
