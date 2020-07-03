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
    signal_oct_updateplot = pyqtSignal()

    def __init__(self, mainexp, wait_condition=None):
        QThread.__init__(self)
        self.mainexp = mainexp
        self.wait_condition = wait_condition

        if wait_condition is not None:
            self.signal_wait_for_mainexp.connect(wait_condition.wakeAll)

        self.signal_oct_initplot.connect(mainexp.oct_initplot)
        self.signal_oct_updateplot.connect(mainexp.oct_updateplot)

        self.cancel = False

    def wait_for_mainexp(self):
        self.signal_wait_for_mainexp.emit()
        self.mainexp.mutex.lock()
        try:
            self.wait_condition.wait(self.mainexp.mutex)
        finally:
            self.mainexp.mutex.unlock()

    def setup_acquisition(self):
        self.mainexp.cam0.setup_acquisition(False, 1)
        self.mainexp.clk.reset()
        self.mainexp.clk.set_freq(1000)

    def start_acquisition(self):
        # todo: add looping for live feed here -- no we actually need to specify which frame to read
        self.mainexp.cam0.start_acquisition()
        # todo: start trigger
        self.mainexp.clk.start()
        self.wait_for_frame()
        self.mainexp.oct_image = self.read_multiple_images()[0]
        self.stop_acquisition()
        self.clk.stop()
        self.clk.reset()
        print(self.mainexp.oct_image)

    def clear_acquisition(self):
        self.cam0.clear_acquisition()

    def run(self):
        self.cancel = False

        self.signal_oct_initplot.emit()

        self.setup_acquisition()
        self.start_acquitision()
        self.clear_acquisition()

        # t_sleep = self.mainexp.dbl_confocal_acqtime.value()
        # n_steps = self.mainexp.int_confocal_y_numdivs.value()
        #
        # for i in range(n_steps):
        #     if not self.cancel:
        #         time.sleep(t_sleep)
        #         self.signal_oct_updateplot.emit()
        # print('Success')


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
