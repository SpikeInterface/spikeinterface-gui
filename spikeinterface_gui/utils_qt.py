from .myqt import QT
import pyqtgraph as pg

import numpy as np


# TODO make a cm to px scaling

qt_style = """
QPushButton {
    min-width: 30px;
    max-width: 70px;
    min-height: 20px;
    max-height: 20px;

    font-size: 10px;
}

QComboBox{
    min-width: 100px;
    max-width: 120px;
    min-height: 20px;
    max-height: 20px;

    font-size: 10px;
}

QSpinBox{
    min-width: 100px;
    max-width: 120px;
    min-height: 20px;
    max-height: 20px;

    font-size: 10px;
}

"""


def add_stretch_to_qtoolbar(tb):
    # add an expending widget + a seprator
    empty = QT.QWidget()
    empty.setSizePolicy(QT.QSizePolicy.Expanding, QT.QSizePolicy.Preferred)
    tb.addWidget(empty)
    tb.addSeparator()

class ViewBoxHandlingLasso(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    lasso_drawing = QT.pyqtSignal(object)
    lasso_finished = QT.pyqtSignal(object)
    
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.drag_points = []
        self.lasso_active = False
    
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    
    def mouseDragEvent(self, ev):
        if not self.lasso_active:
            pg.ViewBox.mouseDragEvent(self, ev)
        else:
            ev.accept()
            if ev.button() != QT.MouseButton.LeftButton:
                return
            
            if ev.isStart():
                self.drag_points = []
            
            pos = self.mapToView(ev.pos())
            self.drag_points.append([pos.x(), pos.y()])
            
            if ev.isFinish():
                self.lasso_finished.emit(self.drag_points)
            else:
                self.lasso_drawing.emit(self.drag_points)
    
    def raiseContextMenu(self, ev):
        pass

class ViewBoxHandlingDoubleClick(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass


class ViewBoxHandlingDoubleClickToPosition(pg.ViewBox):
    doubleclicked = QT.pyqtSignal(float, float)
    ctrl_doubleclicked = QT.pyqtSignal(float, float)
    
    def mouseDoubleClickEvent(self, ev):
        pos = self.mapToView(ev.pos())
        x, y = pos.x(), pos.y()
        if ev.modifiers() == QT.ControlModifier:
            self.ctrl_doubleclicked.emit(x, y)
        else:
            self.doubleclicked.emit(x, y)
        ev.accept()

    # # this is not working because of the ROI that take it
    # def mouseClickEvent(self, ev):
    #     print('mouseClickEvent', ev.modifiers(), QT.ControlModifier, ev.modifiers() == QT.ControlModifier)
    #     pos = self.mapToView(ev.pos())
    #     x, y = pos.x(), pos.y()
    #     if ev.modifiers() == QT.ControlModifier:
    #         self.ctrl_doubleclicked.emit(x, y)
    #     else:
    #         self.doubleclicked.emit(x, y)
    #     ev.accept()
    
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass


class ViewBoxHandlingLassoAndGain(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    gain_zoom = QT.pyqtSignal(float)
    lasso_drawing = QT.pyqtSignal(object)
    lasso_finished = QT.pyqtSignal(object)
    
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.disableAutoRange()
        self.drag_points = []
        
    def mouseClickEvent(self, ev):
        ev.accept()
        
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
        
    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() == QT.Qt.ControlModifier:
            z = 10 if ev.delta()>0 else 1/10.
        else:
            z = 1.3 if ev.delta()>0 else 1/1.3
        self.gain_zoom.emit(z)
        ev.accept()
        
    def mouseDragEvent(self, ev):
        ev.accept()
        if ev.button() != QT.MouseButton.LeftButton:
            return
        
        if ev.isStart():
            self.drag_points = []
        
        pos = self.mapToView(ev.pos())
        self.drag_points.append([pos.x(), pos.y()])
        
        if ev.isFinish():
            self.lasso_finished.emit(self.drag_points)
        else:
            self.lasso_drawing.emit(self.drag_points)
        

class ViewBoxHandlingClickToPositionWithCtrl(pg.ViewBox):
    clicked = QT.pyqtSignal(float, float, bool)
    doubleclicked = QT.pyqtSignal()
    def mouseClickEvent(self, ev):
        pos = self.mapToView(ev.pos())
        x, y = pos.x(), pos.y()
        if ev.modifiers() == QT.ControlModifier:
            self.clicked.emit(x, y, False)
        else:
            self.clicked.emit(x, y, True)

        ev.accept()
        
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass


class ViewBoxHandlingDoubleclickAndGain(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    gain_zoom = QT.pyqtSignal(float)
    widen_narrow = QT.pyqtSignal(float)
    limit_zoom = QT.pyqtSignal(float)
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() == QT.Qt.AltModifier:
            z = 1.3 if ev.delta()>0 else 1/1.3
            self.widen_narrow.emit(z)
        elif ev.modifiers() == QT.Qt.ShiftModifier:
            z = 1.3 if ev.delta()<0 else 1/1.3
            self.limit_zoom.emit(z)
        elif ev.modifiers() == QT.Qt.ControlModifier:
            z = 10 if ev.delta()>0 else 1/10.
            self.gain_zoom.emit(z)
        else:
            z = 1.3 if ev.delta()>0 else 1/1.3
            self.gain_zoom.emit(z)
        ev.accept()
    def raiseContextMenu(self, ev):
        #for some reasons enableMenu=False is not taken (bug ????)
        pass


class ViewBoxForTrace(pg.ViewBox):
    doubleclicked = QT.pyqtSignal(float, float)
    gain_zoom = QT.pyqtSignal(float)
    xsize_zoom = QT.pyqtSignal(float)
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
    def mouseClickEvent(self, ev):
        ev.accept()
    def mouseDoubleClickEvent(self, ev):
        pos = self.mapToView(ev.pos())
        x, y = pos.x(), pos.y()
        self.doubleclicked.emit(x, y)
        ev.accept()
    def mouseDragEvent(self, ev):
        ev.ignore()
    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() == QT.Qt.ControlModifier:
            z = 10 if ev.delta()>0 else 1/10.
        else:
            z = 1.3 if ev.delta()>0 else 1/1.3
        self.gain_zoom.emit(z)
        ev.accept()
    def mouseDragEvent(self, ev):
        ev.accept()
        self.xsize_zoom.emit((ev.pos()-ev.lastPos()).x())







class TimeSeeker(QT.QWidget) :
    
    time_changed = QT.pyqtSignal(float)
    
    def __init__(self, parent = None, show_slider = True, show_spinbox = True) :
        QT.QWidget.__init__(self, parent)
        
        self.layout = QT.QHBoxLayout()
        self.setLayout(self.layout)
        
        if show_slider:
            self.slider = QT.QSlider(orientation=QT.Qt.Horizontal, minimum=0, maximum=999)
            self.layout.addWidget(self.slider)
            self.slider.valueChanged.connect(self.slider_changed)
        else:
            self.slider = None
            
        if show_spinbox:
            self.spinbox = pg.SpinBox(decimals = 4, bounds=[-np.inf, np.inf], suffix = 's', siPrefix = True, 
                            step = 0.1, dec = True, minStep = 0.001)
            self.layout.addWidget(self.spinbox)
            self.spinbox.valueChanged.connect(self.spinbox_changed)
        else:
            self.spinbox = None

        self.t = 0 #  s
        self.set_start_stop(0., 10.)

    def set_start_stop(self, t_start, t_stop, seek = True):
        if np.isnan(t_start) or np.isnan(t_stop): return
        assert t_stop>t_start
        self.t_start = t_start
        self.t_stop = t_stop
        
        if seek:
            self.seek(self.t_start)
        
        if self.spinbox is not None:
            self.spinbox.setMinimum(t_start)
            self.spinbox.setMaximum(t_stop)

    def slider_changed(self, pos):
        t = pos/1000.*(self.t_stop - self.t_start)+self.t_start
        self.seek(t, set_slider = False)
    
    def spinbox_changed(self, val):
        self.seek(val, set_spinbox = False)
        
    def seek(self, t, set_slider = True, set_spinbox = True, emit = True):
        self.t = t
        
        if self.slider is not None and set_slider:
            self.slider.valueChanged.disconnect(self.slider_changed)
            pos = int((self.t - self.t_start)/(self.t_stop - self.t_start)*1000.)
            self.slider.setValue(pos)
            self.slider.valueChanged.connect(self.slider_changed)
        
        if self.spinbox is not None and set_spinbox:
            self.spinbox.valueChanged.disconnect(self.spinbox_changed)
            self.spinbox.setValue(t)
            self.spinbox.valueChanged.connect(self.spinbox_changed)
        
        if emit:
            self.time_changed.emit(float(self.t))

def get_dict_from_group_param(param, cascade = False):
    assert param.type() == 'group'
    d = {}
    for p in param.children():
        if p.type() == 'group':
            if cascade:
                d[p.name()] = get_dict_from_group_param(p, cascade = True)
            continue
        else:
            d[p.name()] = p.value()
    return d


def set_group_param_from_dict(param, d, cascade=False):
    assert param.type() == 'group'
    for p in param.children():
        k = p.name()
        if p.type() == 'group':
            if cascade:
                set_group_param_from_dict(p, d[k], cascade=True)
            continue
        else:
            if k in d:
                if d[k] is None and p.type() == 'float':
                    param[k] = np.nan
                else:
                    param[k] = d[k]
    return d
    

class ParamDialog(QT.QDialog):
    def __init__(self, params, title = '', parent = None):
        QT.QDialog.__init__(self, parent = parent)
        
        self.setWindowTitle(title)
        self.setModal(True)
        
        self.params = pg.parametertree.Parameter.create( name=title, type='group', children = params)
        
        layout = QT.QVBoxLayout()
        self.setLayout(layout)

        self.tree_settings = pg.parametertree.ParameterTree(parent  = self)
        self.tree_settings.header().hide()
        self.tree_settings.setParameters(self.params, showTop=True)
        #self.tree_settings.setWindowFlags(QT.Qt.Window)
        layout.addWidget(self.tree_settings)

        but = QT.QPushButton('OK')
        layout.addWidget(but)
        but.clicked.connect(self.accept)
        
        but.setFocus()

    def get(self):
        if self.exec_():
            return get_dict_from_group_param(self.params, cascade=True)
    
    def set(self, d):
        set_group_param_from_dict(self.params, d, cascade=True)


class MethodDialog(QT.QDialog):
    def __init__(self,   params_by_method, title = '', parent = None, selected_method=None):
        QT.QDialog.__init__(self, parent = parent)
        
        self.setWindowTitle(title)
        self.setModal(True)

        layout = QT.QVBoxLayout()
        self.setLayout(layout)
        
        methods = list(params_by_method.keys())
        if selected_method is not None:
            assert selected_method in methods
        self.methods = methods
        
        params = [{'name' : 'method', 'type' : 'list', 'values' : methods}]
        self.param_method = pg.parametertree.Parameter.create( name=title, type='group', children = params)
        self.tree_settings = pg.parametertree.ParameterTree(parent  = self)
        self.tree_settings.header().hide()
        self.tree_settings.setParameters(self.param_method, showTop=True)
        #self.tree_settings.setWindowFlags(QT.Qt.Window)
        layout.addWidget(self.tree_settings, 1)
        
        
        self.all_params = {}
        self.all_tree_params = {}
        for method in methods:
            params = params_by_method[method]
            self.all_params[method] =  pg.parametertree.Parameter.create(name='params', type='group', children=params)
            tree = pg.parametertree.ParameterTree(parent=self)
            tree.header().hide()
            tree.setParameters(self.all_params[method], showTop=True)
            layout.addWidget(tree, 5)
            tree.hide()
            self.all_tree_params[method] = tree

        but = QT.QPushButton('OK')
        layout.addWidget(but)
        but.clicked.connect(self.accept)
        but.setFocus()
        
        if selected_method is None:
            selected_method = methods[0]
        
        self.param_method.sigTreeStateChanged.connect(self.on_method_change)
        self.param_method['method'] = selected_method
        self.all_tree_params[selected_method].show()
    
    def on_method_change(self):
        #~ print('on_method_change')
        for tree in self.all_tree_params.values():
            tree.hide()
        
        method =  self.param_method['method']
        #~ print(method)
        self.all_tree_params[method].show()
    
    def set_method(self, method, d):
        self.param_method['method'] = method
        set_group_param_from_dict(self.all_params[method], d, cascade=True)
    
    
    def get(self):
        method = self.param_method['method']
        d = get_dict_from_group_param(self.all_params[method], cascade=True)
        return method, d

def open_dialog_methods(params_by_method, parent, title='Which method ?', selected_method=None):
        
        dia = MethodDialog(params_by_method, parent=parent, title=title, selected_method=selected_method)
        
        if dia.exec_():
            method = dia.param_method['method']
            kargs = get_dict_from_group_param(dia.all_params[method], cascade=True)
            return method, kargs
        else:
            return None, None


class CustomItem(QT.QTableWidgetItem):
    def __lt__(self, other):
        try:
            comp = float(self.text()) < float(other.text())
            return comp
        except ValueError:
            return self.text().lower() < other.text().lower()

class CustomItemUnitID(QT.QTableWidgetItem):
    # special case for ordering unit_ids in the original order
    def __init__(self, unit_ids, *args, **kwargs):
        QT.QTableWidgetItem.__init__(self, *args, **kwargs)
        self.unit_ids = [f"{u}" for u in unit_ids]

    def __lt__(self, other):
        ind = self.unit_ids.index(self.text())
        other_ind = self.unit_ids.index(other.text())
        return ind < other_ind

class OrderableCheckItem(QT.QTableWidgetItem):
    # special case for checkbox
    def is_checked(self):
        checked = {QT.Qt.Unchecked : False, QT.Qt.Checked : True}[self.checkState()]
        return checked

    def __lt__(self, other):
        comp = float(self.is_checked()) < float(other.is_checked())
        return comp


class LabelOptionsDelegate(QT.QItemDelegate):
    remove_clicked = QT.pyqtSignal()

    def __init__(self, label_options, parent=None):
        super().__init__(parent)
        self.label_options = label_options

    def editorEvent(self, event, model, option, index):
        if index.row() == index.model().rowCount() - 1 and event.type() == QT.QEvent.Type.MouseButtonPress:
            # Emit a signal when the button is clicked
            self.remove_clicked.emit()
            return True
        return super().editorEvent(event, model, option, index)

    def paint(self, painter, option, index):
        if index.row() == len(self.label_options) - 1:
            # This is the last row, draw a button
            button_option = QT.QStyleOptionButton()
            button_option.rect = option.rect
            button_option.text = index.data()
            button_option.state = QT.QStyle.State_Enabled | QT.QStyle.State_Raised
            QT.QApplication.style().drawControl(QT.QStyle.ControlElement.CE_PushButton,
                                                button_option,
                                                painter)
        else:
            super().paint(painter, option, index)

class UnitTableDelegate(QT.QItemDelegate):
    def __init__(self, parent=None, label_definitions=None, label_columns=None):
        super().__init__(parent)
        self.label_definitions = label_definitions
        self.label_columns = label_columns

        self.label_definitions_by_cols = {}
        for ix, (category, label_def) in enumerate(label_definitions.items()):
            col = self.label_columns[ix]
            self.label_definitions_by_cols[col] = category

    def createEditor(self, parent, option, index):
        col = index.column()
        if col in self.label_definitions_by_cols:
            category = self.label_definitions_by_cols[col]
            label_options = [''] + self.label_definitions[category]['label_options']
            combobox = QT.QComboBox(parent=parent)
            combobox.addItems(label_options)
            editor = combobox
            return editor
        else:
            return None
        
    # def paint(self, painter, option, index):
    #     super().paint(painter, option, index)
    
    # def editorEvent(self, event, model, option, index):
    #     print('editorEvent')
    #     # return super(TableDelegate, self).editorEvent(event, model, option, index)
    #     return super().editorEvent(event, model, option, index)





# class LabelComboBox(QT.QComboBox):
#     remove_label_clicked = QT.pyqtSignal(int, str)
#     label_changed = QT.pyqtSignal(int, str, str)

#     def __init__(self, unit_index, category, label_options, parent=None):
#         super().__init__(parent)
#         self.unit_index = unit_index
#         self.category = category
#         self._origin_labels = label_options
#         self.label_options = [''] + label_options
#         # self.label_options = label_options + ['Remove']
#         # delegate = LabelOptionsDelegate(self.label_options, self)
#         # delegate.remove_clicked.connect(self.on_remove)
#         self.currentTextChanged.connect(self.on_label_changed)
#         # self.setItemDelegate(delegate)
#         self.addItems(self.label_options)

#     def set_label(self, label):
#         if label is None:
#             ind = 0
#         elif label in self._origin_labels:
#             ind = self._origin_labels.index(label) + 1
#         else:
#             ind = 0
#         self.setCurrentIndex(ind)

#     # def on_remove(self):
#     #     self.remove_label_clicked.emit(self.my_row, self.my_col)

#     def on_label_changed(self, current_label):
#         # if self.currentIndex() >= len(self._origin_labels):
#         #     return
#         # self.label_changed.emit(self.my_row, self.my_col, current_label)

#         if self.currentIndex() == 0:
#             self.remove_label_clicked.emit(self.unit_index, self.category)
#         else:
#             self.label_changed.emit(self.unit_index, self.category, current_label)



def find_category(categories, category):
    """
    Find a category, and its index, by its name

    Parameters
    ----------
    categories: List[Dict[str, List]]
    category: str

    Returns
    -------
    ix: int
    cat: Category
    """
    for ix, cat in enumerate(categories):
        if cat['name'] == category:
            return ix, cat
    return None





if __name__=='__main__':
    app = pg.mkQApp()
    #~ timeseeker =TimeSeeker()
    #~ timeseeker.show()
    #~ app.exec_()
    params = [{'name' : 'a', 'value' : 1., 'type' : 'float'}]
    dialog = ParamDialog(params, title = 'yep')
    dialog.exec_()
    print(dialog.get())
