from .myqt import QT
import pyqtgraph as pg

import numpy as np

from .base import WidgetBase

#~ from .peelercontroller import spike_visible_modes
#~ from .tools import ParamDialog

#~ from .. import labelcodes

class SpikeModel(QT.QAbstractItemModel):
    def __init__(self, parent =None, controller=None):
        QT.QAbstractItemModel.__init__(self,parent)
        self.controller = controller
        self.refresh_colors()
    
    def columnCount(self , parentIndex):
        return 6
    
    def rowCount(self, parentIndex):
        return 0
        #~ if not parentIndex.isValid() and self.cc.peak_label is not None:
        if not parentIndex.isValid():
            self.visible_ind, = np.nonzero(self.controller.spikes['visible'])
            return self.visible_ind.size
            
        else :
            return 0
    
    def index(self, row, column, parentIndex):
        if not parentIndex.isValid():
            if column==0:
                childItem = row
            return self.createIndex(row, column, None)
        else:
            return QT.QModelIndex()
    
    def parent(self, index):
        return QT.QModelIndex()
    
    def data(self, index, role):
        if not index.isValid():
            return None
        
        if role not in (QT.Qt.DisplayRole, QT.Qt.DecorationRole):
            return
        
        col = index.column()
        row = index.row()
        
        #~ t_start = 0.
        
        abs_ind = self.visible_ind[row]
        spike = self.controller.spikes[abs_ind]
        
        if np.isnan(spike['jitter']):
            spike_time = (spike['index'])/self.controller.dataio.sample_rate
        else:
            spike_time = (spike['index']+ spike['jitter'])/self.controller.dataio.sample_rate
        
        if role ==QT.Qt.DisplayRole :
            if col == 0:
                return '{}'.format(abs_ind)
            elif col == 1:
                return '{}'.format(spike['segment'])
            elif col == 2:
                return '{}'.format(spike['index'])
            elif col == 3:
                return '{:.2f}'.format(spike['jitter'])
            elif col == 4:
                return '{:.4f}'.format(spike_time)
            elif col == 5:
                return '{}'.format(spike['cluster_label'])
            else:
                return None
        elif role == QT.Qt.DecorationRole :
            if col != 0: return None
            if spike['cluster_label'] in self.icons:
                return self.icons[spike['cluster_label']]
            else:
                return None
        else :
            return None
    
    def flags(self, index):
        if not index.isValid():
            return QT.Qt.NoItemFlags
        return QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable #| Qt.ItemIsDragEnabled

    def headerData(self, section, orientation, role):
        if orientation == QT.Qt.Horizontal and role == QT.Qt.DisplayRole:
            return  ['num', 'seg_num', 'index', 'jitter', 'time', 'cluster_label'][section]
        return
    
    def refresh_colors(self):
        pass
        #~ self.icons = { }
        #~ for k, color in self.controller.qcolors.items():
            #~ pix = QT.QPixmap(10,10 )
            #~ pix.fill(color)
            #~ self.icons[k] = QT.QIcon(pix)
        #~ self.refresh()
    
    def refresh(self):
        self.layoutChanged.emit()


class SpikeListView(WidgetBase):
    def __init__(self,controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        self.controller = controller
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.layout.addWidget(QT.QLabel('<b>All spikes</b>') )
        
        #~ self.combo = QT.QComboBox()
        #~ self.layout.addWidget(self.combo)
        #~ self.combo.addItems(spike_visible_modes)
        #~ self.combo.currentTextChanged.connect(self.change_visible_mode)
        
        self.tree = QT.QTreeView(minimumWidth = 100, uniformRowHeights = True,
                    selectionMode= QT.QAbstractItemView.ExtendedSelection, selectionBehavior = QT.QTreeView.SelectRows,
                    contextMenuPolicy = QT.Qt.CustomContextMenu,)
        
        self.layout.addWidget(self.tree)
        #~ self.tree.customContextMenuRequested.connect(self.open_context_menu)
        
        self.model = SpikeModel(controller=self.controller)
        self.tree.setModel(self.model)
        self.tree.selectionModel().selectionChanged.connect(self.on_tree_selection)

        for i in range(self.model.columnCount(None)):
            self.tree.resizeColumnToContents(i)
        self.tree.setColumnWidth(0,80)
    
    def refresh(self):
        self.model.refresh_colors()
    
    def on_tree_selection(self):
        self.controller.spikes['selected'][:] = False
        for index in self.tree.selectedIndexes():
            if index.column() == 0:
                ind = self.model.visible_ind[index.row()]
                self.controller.spikes['selected'][ind] = True
        self.spike_selection_changed.emit()
    
    def on_spike_selection_changed(self):
        self.tree.selectionModel().selectionChanged.disconnect(self.on_tree_selection)
        
        row_selected, = np.nonzero(self.controller.spikes['selected'][self.model.visible_ind])
        
        if row_selected.size>100:#otherwise this is verry slow
            row_selected = row_selected[:10]
        
        # change selection
        self.tree.selectionModel().clearSelection()
        flags = QT.QItemSelectionModel.Select #| QItemSelectionModel.Rows
        itemsSelection = QT.QItemSelection()
        for r in row_selected:
            for c in range(2):
                index = self.tree.model().index(r,c,QT.QModelIndex())
                ir = QT.QItemSelectionRange( index )
                itemsSelection.append(ir)
        self.tree.selectionModel().select(itemsSelection , flags)

        # set selection visible
        if len(row_selected)>=1:
            index = self.tree.model().index(row_selected[0],0,QT.QModelIndex())
            self.tree.scrollTo(index)

        self.tree.selectionModel().selectionChanged.connect(self.on_tree_selection)        

    def change_visible_mode(self, mode):
        self.controller.change_spike_visible_mode(mode)
        self.cluster_visibility_changed.emit()
        self.model.refresh()

    def open_context_menu(self):
        pass

