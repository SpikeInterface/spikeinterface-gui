# -*- coding: utf-8 -*-
"""
Helper for importing Qt bindings library
see
http://mikeboers.com/blog/2015/07/04/static-libraries-in-a-dynamic-world#the-fold
"""


class ModuleProxy(object):

    def __init__(self, prefixes, modules):
        self.prefixes = prefixes
        self.modules = modules

    def __getattr__(self, name):
        
        if QT_MODE == 'PySide6' and name == 'pyqtSignal':
            name = 'Signal'
        
        for prefix in self.prefixes:
            fullname = prefix + name
            for module in self.modules:
                obj = getattr(module, fullname, None)
                if obj is not None:
                    setattr(self, name, obj) # cache it
                    return obj
        raise AttributeError(name)

QT_MODE = None


if QT_MODE is None:
    try:
        import PySide6
        from PySide6 import QtCore, QtGui, QtWidgets
        QT_MODE = 'PySide6'
    except ImportError:
        pass

if QT_MODE is None:
    try:
        import PyQt6
        from PyQt6 import QtCore, QtGui, QtWidgets
        QT_MODE = 'PyQt6'
    except ImportError:
        pass

if QT_MODE is None:
    try:
        import PyQt5
        from PyQt5 import QtCore, QtGui, QtWidgets
        QT_MODE = 'PyQt5'
    except ImportError:
        pass

#~ print(QT_MODE)

if QT_MODE == 'PySide6':
    QT = ModuleProxy(['', 'Q', 'Qt'], [QtCore.Qt, QtCore, QtGui, QtWidgets])
elif QT_MODE == 'PyQt6':
    QT = ModuleProxy(['', 'Q', 'Qt'], [QtCore.Qt, QtCore, QtGui, QtWidgets])
elif QT_MODE == 'PyQt5':
    QT = ModuleProxy(['', 'Q', 'Qt'], [QtCore.Qt, QtCore, QtGui, QtWidgets])
else:
    QT = None

if QT is not None:
    from pyqtgraph import mkQApp
