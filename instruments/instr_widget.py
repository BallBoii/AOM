from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtCore import pyqtSignal


class GenericWidget(QtWidgets.QWidget):

    signal_btn_checked = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowStaysOnTopHint)

        self.shortcut_close = QtGui.QShortcut(QtGui.QKeySequence('Alt+W'), self)
        self.shortcut_close.activated.connect(self.close)

    def display(self, disp):
        if disp:
            self.show()
            self.raise_()
        else:
            self.hide()

    def closeEvent(self, *args, **kwargs):
        self.signal_btn_checked.emit(False)
