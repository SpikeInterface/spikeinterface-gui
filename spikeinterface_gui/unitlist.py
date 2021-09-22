from .myqt import QT
import pyqtgraph as pg

import numpy as np

from .base import WidgetBase


class UnitListView(WidgetBase):
    """
    """
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        h.addWidget(QT.QLabel('sort by'))
        self.combo_sort = QT.QComboBox()
        self.combo_sort.addItems(['unit_id', 'num_spikes', 'depth'])
        self.combo_sort.currentIndexChanged.connect(self.refresh)
        h.addWidget(self.combo_sort)
        h.addStretch()
        
        self.table = QT.QTableWidget()
        self.layout.addWidget(self.table)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.cellDoubleClicked.connect(self.on_double_clicked)
        
        self.make_menu()
        
        self.refresh()

    def make_menu(self):
        self.menu = QT.QMenu()
        act = self.menu.addAction('Show all')
        act.triggered.connect(self.show_all)
        act = self.menu.addAction('Hide all')
        act.triggered.connect(self.hide_all)

    
    def refresh(self):
        self.table.itemChanged.disconnect(self.on_item_changed)
        
        self.table.clear()
        #~ labels = ['unit_id', 'show/hide', 'nb_peaks', 'extremum_channel', 'cell_label', 'tag', 'annotations']
        labels = ['unit_id', 'visible', 'num_spikes', 'channel_id']
        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        #~ self.table.setMinimumWidth(100)
        #~ self.table.setColumnWidth(0,60)
        self.table.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.setSelectionMode(QT.QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QT.QAbstractItemView.SelectRows)
        
        sort_mode = str(self.combo_sort.currentText())
        
        unit_ids = self.controller.unit_ids

        if sort_mode=='unit_id':
            order =np.arange(unit_ids.size)
        elif sort_mode=='num_spikes':
            order = np.argsort([self.controller.num_spikes[u] for u in unit_ids])[::-1]
        elif sort_mode=='depth':
            depths = self.controller.unit_positions[:, 1]
            order = np.argsort(depths)[::-1]
        
        unit_ids = unit_ids[order]
        
        #~ cluster_labels = self._special_label + self.controller.positive_cluster_labels[order].tolist()
        #~ cluster_labels = self._special_label + self.controller.positive_cluster_labels[order].tolist()
        
        self.table.setRowCount(len(unit_ids))
        
        for i, unit_id in enumerate(unit_ids):
            color = self.controller.qcolors.get(unit_id, QT.QColor( 'black'))
            pix = QT.QPixmap(16,16)
            pix.fill(color)
            icon = QT.QIcon(pix)
            
            item = QT.QTableWidgetItem( f'{unit_id}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i,0, item)
            item.setIcon(icon)
            
            item = QT.QTableWidgetItem('')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable|QT.Qt.ItemIsUserCheckable)
            item.setCheckState({ False: QT.Qt.Unchecked, True : QT.Qt.Checked}[self.controller.unit_visible_dict.get(unit_id, False)])
            self.table.setItem(i,1, item)
            item.unit_id = unit_id
            
            num_spike = self.controller.num_spikes[unit_id]
            item = QT.QTableWidgetItem(f'{num_spike}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i, 2, item)
            
            channel_index = self.controller.get_extremum_channel(unit_id)
            channel_id = self.controller.channel_ids[channel_index]
            item = QT.QTableWidgetItem(f'{channel_id}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i, 3, item)


            
            #~ c = self.controller.get_extremum_channel(k)
            #~ if c is not None:
                #~ item = QT.QTableWidgetItem('{}: {}'.format(c, self.controller.channel_names[c]))
                #~ item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                #~ self.table.setItem(i,3, item)
            
            #~ if k>=0:
                #~ clusters = self.controller.clusters
                ## ind = np.searchsorted(clusters['cluster_label'], k) ## wrong because searchsortedmust be ordered
                #~ ind = np.nonzero(clusters['cluster_label'] == k)[0][0]
                
                #~ for c, attr in enumerate(['cell_label', 'tag', 'annotations']):
                    #~ value = clusters[attr][ind]
                    #~ item = QT.QTableWidgetItem('{}'.format(value))
                    #~ item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                    #~ self.table.setItem(i,4+c, item)
                #~ item = QT.QTableWidgetItem('{}'.format(value))
                #~ item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                #~ self.table.setItem(i,4+c, item)
            
        for i in range(5):
            self.table.resizeColumnToContents(i)
        self.table.itemChanged.connect(self.on_item_changed)        

    def on_item_changed(self, item):
        if item.column() != 1: return
        sel = {QT.Qt.Unchecked : False, QT.Qt.Checked : True}[item.checkState()]
        #~ k = self.controller.cluster_labels[item.row()]
        unit_id = item.unit_id
        self.controller.unit_visible_dict[unit_id] = bool(item.checkState())

        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()
    
    def on_double_clicked(self, row, col):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = False
            
        unit_id = self.table.item(row, 1).unit_id
        self.controller.unit_visible_dict[unit_id] = True
        self.refresh()

        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()
    
    def selected_cluster(self):
        selected = []
        #~ for index in self.table.selectedIndexes():
        for item in self.table.selectedItems():
            #~ if index.column() !=1: continue
            if item.column() != 1: continue
            #~ selected.append(self.controller.cluster_labels[index.row()])
            selected.append(item.label)
        return selected
    
    
    def open_context_menu(self):
        self.menu.popup(self.cursor().pos())
        #~ menu.exec_(self.cursor().pos())
    
    def show_all(self):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = True
        self.refresh()

        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()
    
    def hide_all(self):
        for unit_id in self.controller.unit_visible_dict:
            self.controller.unit_visible_dict[unit_id] = False
        self.refresh()

        self.controller.update_visible_spikes()
        self.unit_visibility_changed.emit()
