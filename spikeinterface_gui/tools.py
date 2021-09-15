from .myqt import QT
import pyqtgraph as pg

import numpy as np

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
    def __init__(self,   params, title = '', parent = None):
        QT.QDialog.__init__(self, parent = parent)
        
        self.setWindowTitle(title)
        self.setModal(True)
        
        self.params = pg.parametertree.Parameter.create( name=title, type='group', children = params)
        
        layout = QT.QVBoxLayout()
        self.setLayout(layout)

        self.tree_params = pg.parametertree.ParameterTree(parent  = self)
        self.tree_params.header().hide()
        self.tree_params.setParameters(self.params, showTop=True)
        #self.tree_params.setWindowFlags(QT.Qt.Window)
        layout.addWidget(self.tree_params)

        but = QT.QPushButton('OK')
        layout.addWidget(but)
        but.clicked.connect(self.accept)
        
        but.setFocus()

    def get(self):
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
        self.tree_params = pg.parametertree.ParameterTree(parent  = self)
        self.tree_params.header().hide()
        self.tree_params.setParameters(self.param_method, showTop=True)
        #self.tree_params.setWindowFlags(QT.Qt.Window)
        layout.addWidget(self.tree_params, 1)
        
        
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
        


if __name__=='__main__':
    app = pg.mkQApp()
    #~ timeseeker =TimeSeeker()
    #~ timeseeker.show()
    #~ app.exec_()
    params = [{'name' : 'a', 'value' : 1., 'type' : 'float'}]
    dialog = ParamDialog(params, title = 'yep')
    dialog.exec_()
    print(dialog.get())
    
    


