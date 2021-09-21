from .myqt import QT
import pyqtgraph as pg

import numpy as np
import  itertools

from .base import WidgetBase
from .tools import ParamDialog



class PairListView(WidgetBase):
    """
    """
    _params = [{'name': 'threshold_similarity', 'type': 'float', 'value' :.9, 'step' : 0.01},
                    {'name': 'threshold_ratio_similarity', 'type': 'float', 'value' :.8, 'step' : 0.01},
                ]

    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)

        #~ h = QT.QHBoxLayout()
        #~ self.layout.addLayout(h)
        self.combo_select = QT.QComboBox()
        #~ h.addWidget(QT.QLabel('Select'))
        #~ h.addWidget(self.combo_select)
        self.combo_select.addItems(['all pairs', 'high similarity']) #
        #~ self.combo_select.currentTextChanged.connect(self.refresh)
        #~ h.addStretch()

        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        h.addWidget(QT.QLabel('Sort by'))
        self.combo_sort = QT.QComboBox()
        self.combo_sort.addItems(['label', 'similarity', 'ratio_similarity'])
        self.combo_sort.currentIndexChanged.connect(self.refresh)
        h.addWidget(self.combo_sort)
        h.addStretch()
        
        
        #~ but = QT.QPushButton('settings')
        #~ self.layout.addWidget(but)
        #~ but.clicked.connect(self.open_settings)
        
        self.table = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                                        selectionBehavior=QT.QAbstractItemView.SelectRows)
        self.table.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.layout.addWidget(self.table)
        self.table.itemSelectionChanged.connect(self.on_item_selection_changed)
        #~ self.table.customContextMenuRequested.connect(self.open_context_menu)
        
        #~ self.menu = QT.QMenu()
        #~ act = self.menu.addAction('Merge')
        #~ act.triggered.connect(self.do_merge)

        #~ act = self.menu.addAction('Tag same cell')
        #~ act.triggered.connect(self.do_tag_same_cell)
        
        self.refresh()
    
    def on_item_selection_changed(self):
        inds = self.table.selectedIndexes()
        if len(inds)!=self.table.columnCount():
            return
        k1, k2 = self.pairs[inds[0].row()]
        for k in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[k] = k in (k1, k2)
        
        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()

    def open_context_menu(self):
        self.menu.popup(self.cursor().pos())
    
    def do_merge(self):
        if len(self.table.selectedIndexes())==0:
            return
        ind = self.table.selectedIndexes()[0].row()
        
        label_to_merge = list(self.pairs[ind])
        self.controller.merge_cluster(label_to_merge)
        self.refresh()
        self.spike_label_changed.emit()
    
    def do_tag_same_cell(self):
        if len(self.table.selectedIndexes())==0:
            return
        ind = self.table.selectedIndexes()[0].row()
        
        label_to_merge = list(self.pairs[ind])
        self.controller.tag_same_cell(label_to_merge)
        self.refresh()
        self.cluster_tag_changed.emit()
        
    
    def refresh(self):
        self.table.clear()
        labels = ['unit_id1', 'unit_id2', 'similarity',]
        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 100)
        
        #select
        mode = self.combo_select.currentText()
        if mode == 'all pairs':
            unit_ids = self.controller.unit_ids
            self.pairs = list(itertools.combinations(unit_ids, 2))
        elif mode == 'high similarity':
            self.pairs = self.controller.detect_high_similarity(threshold=self.params['threshold_similarity'])
        
        #sort
        mode = self.combo_sort.currentText()
        order = np.arange(len(self.pairs))
        if mode == 'label':
            pass
        elif mode == 'similarity':
            if self.controller.cluster_similarity is not None:
                order = []
                for r in range(len(self.pairs)):
                    k1, k2 = self.pairs[r]
                    ind1 = self.controller.positive_cluster_labels.tolist().index(k1)
                    ind2 = self.controller.positive_cluster_labels.tolist().index(k2)
                    order.append(self.controller.cluster_similarity[ind1, ind2])
                order = np.argsort(order)[::-1]
        #~ elif mode == 'ratio_similarity':
            #~ if self.controller.cluster_ratio_similarity is not None:
                #~ order = []
                #~ for r in range(len(self.pairs)):
                    #~ k1, k2 = self.pairs[r]
                    #~ ind1 = self.controller.positive_cluster_labels.tolist().index(k1)
                    #~ ind2 = self.controller.positive_cluster_labels.tolist().index(k2)
                    #~ order.append(self.controller.cluster_ratio_similarity[ind1, ind2])
                #~ order = np.argsort(order)[::-1]
        self.pairs = [self.pairs[i] for i in order ]
        
        self.table.setRowCount(len(self.pairs))
        
        for r in range(len(self.pairs)):
            unit_id1, unit_id2 = self.pairs[r]
            ind1 = self.controller.unit_ids.tolist().index(unit_id1)
            ind2 = self.controller.unit_ids.tolist().index(unit_id2)
            
            for c, unit_id in enumerate((unit_id1, unit_id2)):
                color = self.controller.qcolors.get(unit_id, QT.QColor( 'white'))
                pix = QT.QPixmap(16,16)
                pix.fill(color)
                icon = QT.QIcon(pix)
                
                # TODO
                # name = '{} (n={})'.format(k, self.controller.cluster_count[k])
                name = f'{unit_id} (n=??)'
                item = QT.QTableWidgetItem(name)
                item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                self.table.setItem(r,c, item)
                item.setIcon(icon)
                
                #~ cell_label = self.controller.cell_labels[self.controller.cluster_labels==k][0]
                #~ name = '{}'.format(cell_label)
                #~ item = QT.QTableWidgetItem(name)
                #~ item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                #~ self.table.setItem(r,c+2, item)
        
            #~ if self.controller.cluster_similarity is not None:
                #~ if self.controller.cluster_similarity.shape[0] == self.controller.positive_cluster_labels.size:
                    #~ name = '{}'.format(self.controller.cluster_similarity[ind1, ind2])
                    #~ item = QT.QTableWidgetItem(name)
                    #~ item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                    #~ self.table.setItem(r,4, item)

            #~ if self.controller.cluster_ratio_similarity is not None:
                #~ if self.controller.cluster_ratio_similarity.shape[0] == self.controller.positive_cluster_labels.size:
                    #~ name = '{}'.format(self.controller.cluster_ratio_similarity[ind1, ind2])
                    #~ item = QT.QTableWidgetItem(name)
                    #~ item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                    #~ self.table.setItem(r,5, item)
        
    def on_spike_selection_changed(self):
        pass

    def on_colors_changed(self):
        self.refresh()
    
    def on_unit_visibility_changed(self):
        pass

