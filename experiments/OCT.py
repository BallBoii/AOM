from PyQt6.QtCore import QThread, pyqtSignal
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

        self.cam = self.mainexp.cam0
        self.clk = self.mainexp.clk
        self.ao = self.mainexp.ao0

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
        ao_start = self.mainexp.dbl_confocal_x_start.value()
        ao_stop = self.mainexp.dbl_confocal_x_stop.value()
        ao_numsteps = self.mainexp.int_confocal_x_numsteps.value()
        exp_time_us = self.mainexp.dbl_confocal_acqtime.value()*1000
        frame_rate = self.mainexp.int_oct_frame_rate.value()

        self.mainexp.oct_rngx = np.linspace(ao_start, ao_stop, ao_numsteps)

        self.ao.set_int_clock(1000000/exp_time_us, ao_numsteps)
        self.ao.set_start_trigger('PFI12', PyDAQmx.Val_Rising)
        self.ao.set_retriggerable(True)
        self.ao.set_voltages(self.mainexp.oct_rngx)

        self.cam.set_value('Height', ao_numsteps)
        self.cam.set_value('CameraAttributes/AcquisitionControl/ExposureTime', exp_time_us)
        self.cam.setup_acquisition(False, 1)
        self.clk.reset()
        self.clk.set_freq(frame_rate)

    def start_acquisition(self):
        self.clk.start()
        self.ao.start()
        # todo: OCT doesn't really care if there are multiple sweeps before the camera takes picture?
        while not self.cancel:
            self.cam.start_acquisition()
            # todo: start trigger
            self.cam.wait_for_frame()
            self.mainexp.oct_raw = self.cam.read_multiple_images()[0]
            self.signal_oct_updateplot.emit()
            self.cam.stop_acquisition()

        self.ao.stop()
        self.ao.reset()
        self.clk.stop()
        self.clk.reset()
        # print(self.mainexp.oct_image)

    def clear_acquisition(self):
        self.mainexp.cam0.clear_acquisition()

    def run(self):
        self.cancel = False

        # self.signal_oct_initplot.emit()

        self.setup_acquisition()
        self.start_acquisition()
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
