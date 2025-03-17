from .myqt import QT
import pyqtgraph as pg


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

