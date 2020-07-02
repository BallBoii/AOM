from PyQt5.QtCore import QThread, pyqtSignal
import PyDAQmx, time, datetime
import numpy as np
import warnings

from . import ExpThread


class OCT(QThread):
    '''MODIFIED TO USE ANALOG SIGNAL FROM PHOTODIODE INSTEAD'''
    # Define signals for communicating with mainexp
    signal_wait_for_mainexp = pyqtSignal()
    signal_log = pyqtSignal(str)
    signal_log_clear = pyqtSignal()

    signal_oct_grab_screenshots = pyqtSignal()
    signal_oct_initplot = pyqtSignal()
    signal_oct_updateplot = pyqtSignal(int)

    def __init__(self, mainexp, wait_condition=None):
        QThread.__init__(self)
        self.mainexp = mainexp
        self.wait_condition = wait_condition

        if wait_condition is not None:
            self.signal_wait_for_mainexp.connect(wait_condition.wakeAll)

        self.signal_oct_initplot.connect(mainexp.oct_initplot)

        self.cancel = False

    def wait_for_mainexp(self):
        self.signal_wait_for_mainexp.emit()
        self.mainexp.mutex.lock()
        try:
            self.wait_condition.wait(self.mainexp.mutex)
        finally:
            self.mainexp.mutex.unlock()

    def run(self):
        self.cancel = False

        self.signal_oct_initplot.emit()
        print('Success')
        # self.prep_mainexp()
        # self.update()
        #
        # self.prepsweep()
        # self.initplots()
        #
        # self.sweep2d()
        # self.cleanup()
        # self.isLive = False

    def __del__(self):
        self.wait()
