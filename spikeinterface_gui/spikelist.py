import numpy as np
import time

from .view_base import ViewBase


_columns = ['#', 'unit_id', 'segment_index', 'sample_index', 'channel_index', 'rand_selected']


def get_qt_spike_model():
    # this getter is to protect import QT when using panel

    from .myqt import QT

    class SpikeModel(QT.QAbstractItemModel):

        def __init__(self, parent =None, controller=None, columns=[]):
            QT.QAbstractItemModel.__init__(self,parent)
            self.controller = controller
            self.columns = columns
            # self.refresh_colors()
            
            self.visible_ind = self.controller.get_indices_spike_visible()
        
        def columnCount(self , parentIndex):
            return len(self.columns)
        
        def rowCount(self, parentIndex):
            if not parentIndex.isValid():
                return int(self.visible_ind.size)
            else :
                return 0
        
        def index(self, row, column, parentIndex):
            if not parentIndex.isValid():
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
                    return '{}'.format(spike['rand_selected'])
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
                return  self.columns[section]
            return

        def refresh_colors(self, qcolors):
            self.icons = { }
            for unit_id, qcolor in qcolors.items():
                pix = QT.QPixmap(10,10 )
                pix.fill(qcolor)
                self.icons[unit_id] = QT.QIcon(pix)
        
        def refresh(self):
            self.visible_ind = self.controller.get_indices_spike_visible()
            self.layoutChanged.emit()

        def clear(self):
            self.visible_ind = np.array([])
            self.layoutChanged.emit()

    return SpikeModel



class SpikeListView(ViewBase):
    _supported_backend = ['qt', 'panel']
    _settings = [
            {'name': 'select_change_channel_visibility', 'type': 'bool', 'value': False},
        ]
    
    def __init__(self, controller=None, parent=None, backend="qt"):
        ViewBase.__init__(self, controller=controller, parent=parent,  backend=backend)

    def handle_selection(self, inds):
        self.controller.set_indices_spike_selected(inds)
        self.notify_spike_selection_changed()

        if len(inds) == 1 and self.settings['select_change_channel_visibility']:
            # also change channel for centering trace view.
            sparsity_mask = self.controller.get_sparsity_mask()
            unit_index = self.controller.spikes[inds[0]]['unit_index']
            visible_channel_inds, = np.nonzero(sparsity_mask[unit_index, :])

            # check if channel visibility must be changed
            if not np.all(np.isin(visible_channel_inds, self.controller.visible_channel_inds)):
                self.controller.set_channel_visibility(visible_channel_inds)
                self.notify_channel_visibility_changed()

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT

        # this getter is to protect import QT
        SpikeModel = get_qt_spike_model()
        
        self.layout = QT.QVBoxLayout()
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        
        self.label = QT.QLabel('') 
        h.addWidget(self.label)
        
        # h.addStretch()

        but = QT.QPushButton('↻ spikes')
        # h.addWidget(but)
        tb = self.qt_widget.view_toolbar
        tb.addWidget(but)
        but.clicked.connect(self.refresh)
        
        self.tree = QT.QTreeView(minimumWidth = 100, uniformRowHeights = True,
                    selectionMode= QT.QAbstractItemView.ExtendedSelection, selectionBehavior = QT.QTreeView.SelectRows,
                    contextMenuPolicy = QT.Qt.CustomContextMenu,)

        
        self.layout.addWidget(self.tree)
        
        self.model = SpikeModel(controller=self.controller, columns=_columns)
        qcolors = {unit_id:self.get_unit_color(unit_id) for unit_id in self.controller.unit_ids}
        self.model.refresh_colors(qcolors)

        self.tree.setModel(self.model)
        self.tree.selectionModel().selectionChanged.connect(self._qt_on_tree_selection)

        for i in range(self.model.columnCount(None)):
            self.tree.resizeColumnToContents(i)
        self.tree.setColumnWidth(0,80)
        
    
    def _qt_refresh_label(self):
        n1 = self.controller.spikes.size
        n2 = self.controller.get_indices_spike_visible().size
        n3 = self.controller.get_indices_spike_selected().size
        txt = f'<b>All spikes</b> : {n1} - <b>visible</b> : {n2} - <b>selected</b> : {n3}'
        self.label.setText(txt)
   
    def _qt_refresh(self):
        self._qt_refresh_label()
        qcolors = {unit_id:self.get_unit_color(unit_id) for unit_id in self.controller.unit_ids}
        self.model.refresh_colors(qcolors)
        self.model.refresh()
    
    def _qt_on_tree_selection(self):
        inds = []
        for index in self.tree.selectedIndexes():
            if index.column() == 0:
                ind = self.model.visible_ind[index.row()]
                inds.append(ind)

        self.handle_selection(inds)
        self._qt_refresh_label()
    
    def _qt_on_unit_visibility_changed(self):
        # we cannot refresh this list in real time whil moving channel/unit visibility
        # it is too slow. So the list is clear.
        self._qt_refresh_label()
        self.model.clear()
        qcolors = {unit_id:self.get_unit_color(unit_id) for unit_id in self.controller.unit_ids}
        self.model.refresh_colors(qcolors)

    def _qt_on_unit_color_changed(self):
        # we cannot refresh this list in real time whil moving channel/unit visibility
        # it is too slow. So the list is clear.
        self._qt_refresh_label()
        self.model.clear()
        qcolors = {unit_id:self.get_unit_color(unit_id) for unit_id in self.controller.unit_ids}
        self.model.refresh_colors(qcolors)


    def _qt_on_spike_selection_changed(self):
        from .myqt import QT
        self.tree.selectionModel().selectionChanged.disconnect(self._qt_on_tree_selection)
        
        selected_inds  = self.controller.get_indices_spike_selected()
        visible_inds = self.controller.get_indices_spike_visible()
        row_selected,  = np.nonzero(np.isin(visible_inds, selected_inds))
        
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

        self.tree.selectionModel().selectionChanged.connect(self._qt_on_tree_selection)
        self._qt_refresh_label()

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import pandas as pd
        from .utils_panel import spike_formatter, SelectableTabulator #KeyboardShortcut, KeyboardShortcuts

        # pn.extension('tabulator')

        # Configure columns for tabulator
        df = pd.DataFrame(columns=_columns)
        formatters = {"unit_id": spike_formatter}

        # Create tabulator instance
        self.table = SelectableTabulator(
            df,
            layout="fit_data",
            formatters=formatters,
            frozen_columns=["#", "unit_id"],
            sizing_mode="stretch_both",
            show_index=False,
            selectable=True,
            disabled=True,
            pagination=None,
            # SelectableTabulator functions
            parent_view=self,
            refresh_table_function=self._panel_refresh_table,
            conditional_shortcut=self.is_view_active,
        )
        # Add selection event handler
        self.table.param.watch(self._panel_on_selection_changed, "selection")

        self.refresh_button = pn.widgets.Button(name="↻ spikes", button_type="default", sizing_mode="stretch_width")
        self.refresh_button.on_click(self._panel_on_refresh_click)

        self.clear_button = pn.widgets.Button(name="Clear", button_type="default", sizing_mode="stretch_width")
        self.clear_button.on_click(self._panel_on_clear_click)

        self.info_text = pn.pane.HTML("")

        # Create main layout
        self.layout = pn.Column(
            self.info_text,
            pn.Row(
                self.clear_button,
                self.refresh_button,
            ),
            self.table,
            sizing_mode="stretch_both",
        )

        self.last_clicked = None
        self.last_clicked_row = None
        self.last_selected_row = None

    def _panel_refresh(self):
        pass

    def _panel_refresh_table(self):
        import matplotlib.colors as mcolors
        import pandas as pd

        visible_inds = self.controller.get_indices_spike_visible()
        unit_ids = self.controller.unit_ids
        spikes = self.controller.spikes[visible_inds]

        spike_unit_ids = []
        for i, spike in enumerate(spikes):
            unit_id = unit_ids[spike['unit_index']]
            color = mcolors.to_hex(self.controller.get_unit_color(unit_id))
            spike_unit_ids.append({"id": unit_id, "color": color})

        # Prepare data for tabulator
        data = {
            '#': visible_inds,
            'unit_id': spike_unit_ids,
            'segment_index': spikes['segment_index'],
            'sample_index': spikes['sample_index'],
            'channel_index': spikes['channel_index'],
            'rand_selected': spikes['rand_selected']
        }

        # Update table data
        df = pd.DataFrame(data)
        self.table.value = df

        selected_inds = self.controller.get_indices_spike_selected()
        if len(selected_inds) == 0:
            self.table.selection = []
        else:
            # Find the rows corresponding to the selected indices
            row_selected, = np.nonzero(np.isin(visible_inds, selected_inds))
            self.table.selection = [int(r) for r in row_selected]
            
        self._panel_refresh_label()

    def _panel_on_refresh_click(self, event):
        self._panel_refresh_label()
        self._panel_refresh_table()
        self.notify_active_view_updated()

    def _panel_on_clear_click(self, event):
        self.controller.set_indices_spike_selected([])
        self.table.selection = []
        self.notify_spike_selection_changed()
        self._panel_refresh_label()
        self.notify_active_view_updated()

    def _panel_on_selection_changed(self, event=None):
        selection = event.new
        if len(selection) == 0:
            self.handle_selection([])
        else:
            absolute_indices = self.controller.get_indices_spike_visible()[np.array(selection)]
            self.handle_selection(absolute_indices)
        self._panel_refresh_label()

    def _panel_refresh_label(self):
        n1 = self.controller.spikes.size
        n2 = self.controller.get_indices_spike_visible().size
        n3 = self.controller.get_indices_spike_selected().size
        txt = f"<b>All spikes</b>: {n1} - <b>visible</b>: {n2} - <b>selected</b>: {n3}"
        self.info_text.object = txt

    def _panel_on_unit_visibility_changed(self):
        import pandas as pd
        # Clear the table when visibility changes
        self.table.value = pd.DataFrame(columns=_columns, data=[])
        self._panel_refresh_label()

    def _panel_on_spike_selection_changed(self):
        selected_inds = self.controller.get_indices_spike_selected()
        visible_inds = self.controller.get_indices_spike_visible()
        row_selected, = np.nonzero(np.isin(visible_inds, selected_inds))
        row_selected = [int(r) for r in row_selected]
        # Update the selection in the table
        self.table.selection = row_selected
        self._panel_refresh_label()


SpikeListView._gui_help_txt = """
## Spike list View

Show all spikes of the visible units. When spikes are selected, they are highlighted in the Spike Amplitude View and the ND SCatter View.
When a single spike is selected, the Trace and TraceMap Views are centered on it.

### Controls
* **↻ spikes**: refresh the spike list
* **clear**: clear the selected spikes
* **shift + arrow up/down** : select next/previous spike and make it visible alone
"""
