from .myqt import QT
import pyqtgraph as pg

import numpy as np

#~ from .. import labelcodes
from .base import WidgetBase




class UnitListView(WidgetBase):
    """
    Base for ClusterPeakList (catalogue window) and ClusterSpikeList (Peeler window)
    """
    #~ _special_label = [labelcodes.LABEL_UNCLASSIFIED]
    
    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        h.addWidget(QT.QLabel('sort by'))
        self.combo_sort = QT.QComboBox()
        self.combo_sort.addItems(['label', 'extremum_channel', 'extremum_amplitude', 'waveform_rms', 'nb_peak'])
        self.combo_sort.currentIndexChanged.connect(self.refresh)
        h.addWidget(self.combo_sort)
        h.addStretch()
        
        self.table = QT.QTableWidget()
        self.layout.addWidget(self.table)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.cellDoubleClicked.connect(self.on_double_clicked)
        
        self.make_menu()
        
        #~ self.refresh()

    def make_menu(self):
        raise(NotImplementedError)
    
    def refresh(self):
        self.table.itemChanged.disconnect(self.on_item_changed)
        
        self.table.clear()
        labels = ['cluster_label', 'show/hide', 'nb_peaks', 'extremum_channel', 'cell_label', 'tag', 'annotations']
        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        #~ self.table.setMinimumWidth(100)
        #~ self.table.setColumnWidth(0,60)
        self.table.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.setSelectionMode(QT.QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QT.QAbstractItemView.SelectRows)
        
        sort_mode = str(self.combo_sort.currentText())
        
        clusters = self.controller.clusters
        clusters = clusters[clusters['cluster_label']>=0]
        if sort_mode=='label':
            order =np.arange(clusters.size)
        elif sort_mode=='extremum_channel':
            order = np.argsort(clusters['extremum_channel'])
        elif sort_mode=='extremum_amplitude':
            order = np.argsort(np.abs(clusters['extremum_amplitude']))[::-1]
        elif sort_mode=='waveform_rms':
            order = np.argsort(clusters['waveform_rms'])[::-1]
        elif sort_mode=='nb_peak':
            order = np.argsort(clusters['nb_peak'])[::-1]
        
        cluster_labels = self._special_label + self.controller.positive_cluster_labels[order].tolist()
        
        self.table.setRowCount(len(cluster_labels))
        
        for i, k in enumerate(cluster_labels):
            color = self.controller.qcolors.get(k, QT.QColor( 'white'))
            pix = QT.QPixmap(16,16)
            pix.fill(color)
            icon = QT.QIcon(pix)
            
            if k<0:
                name = '{} ({})'.format(k, labelcodes.to_name[k])
            else:
                name = '{}'.format(k)
            item = QT.QTableWidgetItem(name)
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i,0, item)
            item.setIcon(icon)
            
            item = QT.QTableWidgetItem('')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable|QT.Qt.ItemIsUserCheckable)
            
            item.setCheckState({ False: QT.Qt.Unchecked, True : QT.Qt.Checked}[self.controller.cluster_visible.get(k, False)])
            self.table.setItem(i,1, item)
            item.label = k

            item = QT.QTableWidgetItem('{}'.format(self.controller.cluster_count.get(k, 0)))
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table.setItem(i,2, item)
            
            c = self.controller.get_extremum_channel(k)
            if c is not None:
                item = QT.QTableWidgetItem('{}: {}'.format(c, self.controller.channel_names[c]))
                item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                self.table.setItem(i,3, item)
            
            if k>=0:
                clusters = self.controller.clusters
                ## ind = np.searchsorted(clusters['cluster_label'], k) ## wrong because searchsortedmust be ordered
                ind = np.nonzero(clusters['cluster_label'] == k)[0][0]
                
                for c, attr in enumerate(['cell_label', 'tag', 'annotations']):
                    value = clusters[attr][ind]
                    item = QT.QTableWidgetItem('{}'.format(value))
                    item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                    self.table.setItem(i,4+c, item)

            
        for i in range(5):
            self.table.resizeColumnToContents(i)
        self.table.itemChanged.connect(self.on_item_changed)        

    def on_item_changed(self, item):
        if item.column() != 1: return
        sel = {QT.Qt.Unchecked : False, QT.Qt.Checked : True}[item.checkState()]
        #~ k = self.controller.cluster_labels[item.row()]
        k = item.label
        self.controller.cluster_visible[k] = bool(item.checkState())
        self.cluster_visibility_changed.emit()
    
    def on_double_clicked(self, row, col):
        for k in self.controller.cluster_visible:
            self.controller.cluster_visible[k] = False
            
        k = self.table.item(row, 1).label
        self.controller.cluster_visible[k] = True
        self.refresh()
        self.cluster_visibility_changed.emit()
        
    
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
        for k in self.controller.cluster_visible:
            self.controller.cluster_visible[k] = True
        self.refresh()
        self.cluster_visibility_changed.emit()
    
    def hide_all(self):
        for k in self.controller.cluster_visible:
            self.controller.cluster_visible[k] = False
        self.refresh()
        self.cluster_visibility_changed.emit()
    
    

    



    
    
    
    def make_menu(self):
        self.menu = QT.QMenu()
        act = self.menu.addAction('Show all')
        act.triggered.connect(self.show_all)
        act = self.menu.addAction('Hide all')
        act.triggered.connect(self.hide_all)
    
