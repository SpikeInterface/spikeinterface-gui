from .myqt import QT
import pyqtgraph as pg

import numpy as np
import itertools

from .base import WidgetBase
from .tools import ParamDialog, get_dict_from_group_param, CustomItem


class CurationView(WidgetBase):
    """
    """

    _need_compute = False

    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)

        self.merge_info = {}
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QT.QLabel("Merge"))
        self.table_merge = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        # self.table_merge.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.layout.addWidget(self.table_merge)
        # self.table.itemSelectionChanged.connect(self.on_item_selection_changed)


        self.layout.addWidget(QT.QLabel("Delete"))
        self.table_delete = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        # self.table_delete.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.layout.addWidget(self.table_delete)


        self.refresh()

    def _refresh(self):
        print("curation refresh")
        print(self.controller.manual_curation_data)
        pass

    def on_manual_curation_updated(self):
        self._refresh()


CurationView._gui_help_txt = """
"""
