from .myqt import QT
import pyqtgraph as pg

import numpy as np

from .base import WidgetBase


_columns = ['num', 'unit_id', 'segment', 'sample_index', 'channel_index', 'included_in_pc']

class SpikeModel(QT.QAbstractItemModel):
    def __init__(self, parent =None, controller=None):
        QT.QAbstractItemModel.__init__(self,parent)
        self.controller = controller
        self.refresh_colors()
    
    def columnCount(self , parentIndex):
        return len(_columns)
    
    def rowCount(self, parentIndex):
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
        
        abs_ind = self.visible_ind[row]
        spike = self.controller.spikes[abs_ind]
        unit_id = self.controller.unit_ids[spike['unit_index']]
        
        if role ==QT.Qt.DisplayRole :
            if col == 0:
                return '{}'.format(abs_ind)
            elif col == 1:
                return '{}'.format(unit_id)
            elif col == 2:
                return '{}'.format(spike['segment_index'])
            elif col == 3:
                return '{}'.format(spike['sample_index'])
            elif col == 4:
                return '{}'.format(spike['channel_index'])
            elif col == 5:
                return '{}'.format(spike['included_in_pc'])
            else:
                return None
        elif role == QT.Qt.DecorationRole :
            if col != 0:
                return None
            if unit_id in self.icons:
                return self.icons[unit_id]
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
            return  _columns[section]
        return

    def refresh_colors(self):
        self.icons = { }
        for unit_id, qcolor in self.controller.qcolors.items():
            pix = QT.QPixmap(10,10 )
            pix.fill(qcolor)
            self.icons[unit_id] = QT.QIcon(pix)
    
    def refresh(self):
        self.layoutChanged.emit()


class SpikeListView(WidgetBase):
    def __init__(self,controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        self.controller = controller
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.layout.addWidget(QT.QLabel('<b>All spikes</b>') )
        
        self.tree = QT.QTreeView(minimumWidth = 100, uniformRowHeights = True,
                    selectionMode= QT.QAbstractItemView.ExtendedSelection, selectionBehavior = QT.QTreeView.SelectRows,
                    contextMenuPolicy = QT.Qt.CustomContextMenu,)
        
        self.layout.addWidget(self.tree)
        
        self.model = SpikeModel(controller=self.controller)
        self.tree.setModel(self.model)
        self.tree.selectionModel().selectionChanged.connect(self.on_tree_selection)

        for i in range(self.model.columnCount(None)):
            self.tree.resizeColumnToContents(i)
        self.tree.setColumnWidth(0,80)
    
    def refresh(self):
        self.model.refresh_colors()
        self.model.refresh()
    
    def on_tree_selection(self):
        self.controller.spikes['selected'][:] = False
        for index in self.tree.selectedIndexes():
            if index.column() == 0:
                ind = self.model.visible_ind[index.row()]
                self.controller.spikes['selected'][ind] = True
        self.spike_selection_changed.emit()
    
    def on_unit_visibility_changed(self):
        
        if np.any(self.controller.spikes['selected']):
            self.controller.spikes['selected'][:] = False
            self.spike_selection_changed.emit()
        
        self.refresh()

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

    #~ def change_visible_mode(self, mode):
        #~ self.controller.change_spike_visible_mode(mode)
        #~ self.unit_visibility_changed.emit()
        #~ self.model.refresh()

    def open_context_menu(self):
        pass

