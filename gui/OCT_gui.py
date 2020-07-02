from PyQt5 import QtGui, QtCore, QtWidgets

# system imports
import sys, os, struct, scipy.io, warnings, functools, time, datetime
import pyqtgraph as pg
import PyDAQmx
import pdb
import numpy as np
import csv

# user-defined imports
import file_utils
import instruments as instr
import experiments as exp

# import UI files
import OCT as mainwindow
import mainexp_widgets


def my_excepthook(type, value, tback):
    sys.__excepthook__(type, value, tback)


sys.excepthook = my_excepthook


class MainExp_GUI(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, galvo2=False):
        # constructor from QMainWindow parent class
        super(self.__class__,self).__init__()

        # configure PyQTgraph to use white background
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # setupUi sits in exptdesign, as defined by Qt Designer
        self.setupUi(self)

        self.setFixedSize(self.size())

        # this will ensure that the application quits at the right time,
        # and that Qt has a chance to automatically delete all the children of the top-level window
        # before the python garbage-collector gets to work.
        # http://stackoverflow.com/questions/27131294/error-qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qt
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.confocal_mode = 0
        self.confocal_rngx = []
        self.confocal_rngy = []
        self.confocal_rngz = []
        self.confocal_pl = np.array([])

        # Create PyQtGraph plots and histogram for confocal scans
        for name in ['confocal', 'map']:
            setattr(self, 'vb_%s' % name, pg.ViewBox())
            setattr(self, 'plt_%s' % name, pg.PlotItem(viewBox=getattr(self, 'vb_%s' % name)))
            setattr(self, 'qtimg_%s' % name, pg.ImageItem())
            getattr(self, 'vb_%s' % name).addItem(getattr(self, 'qtimg_%s' % name))

        # Define yellow-hot colormap
        colors = np.array([[0, 0, 0, 1], [1, 0, 0, 1], [1, 1, 0, 1.0]])
        cm = pg.ColorMap([0, 0.5, 1], colors)

        '''MAIN PLOTS'''
        self.glw_confocal = pg.GraphicsLayoutWidget()
        self.glw_confocal.addItem(self.plt_confocal, 0, 0)
        self.hlw_confocal = mainexp_widgets.CustomLUTWidget(image=self.qtimg_confocal)
        self.hlw_confocal.gradient.setColorMap(cm)

        self.grid_confocal.addWidget(self.glw_confocal, 0, 0)
        self.grid_confocal.addWidget(self.hlw_confocal, 0, 1)


        '''OCT SPECTRUM & FFT'''
        self.plt_oct_spectrum = self.glw_tracker.addPlot(0, 0)
        self.plt_oct_spectrum.setLabels(left='y axis name', bottom='x axis name')
        self.plt_oct_fft = self.glw_tracker.addPlot(1, 0)
        self.plt_oct_fft.setLabels(left='y axis name', bottom='x axis name')

        self.curve_oct_spectrum = self.plt_oct_spectrum.plot([], [], pen='r')
        self.curve_oct_fft = self.plt_oct_fft.plot([], [], pen='r')

        self.exp_oct = exp.OCT.OCT(self)

        self.btn_confocal_start.clicked.connect(self.oct_start)
        self.btn_confocal_stop.clicked.connect(self.oct_stop)

    def oct_start(self):
        self.exp_oct.start()

    def oct_stop(self):
        self.exp_oct.cancel = True

    def oct_initplot(self):
        start_x = 0
        stop_x = 1
        start_y = 0
        stop_y = 1

        # self.qtimg_confocal.setImage(self.confocal_pl[:, :, 0])
        self.qtimg_confocal.setImage(np.random.rand(10, 10))
        # self.hlw_confocal.setImageItem(self.qtimg_confocal)

        for name in ['confocal']:
            qtimg = getattr(self, 'qtimg_%s' % name)
            qtimg.resetTransform()  # need to call this. otherwise pos and scale are relative to previous
            qtimg.setPos(start_x, start_y)
            scale_x = (stop_x - start_x)/(qtimg.image.shape[0])
            scale_y = (stop_y - start_y)/(qtimg.image.shape[1])
            qtimg.scale(scale_x, scale_y)

        self.plt_confocal.setLabels(bottom='xpos (&mu;m)', left='ypos (&mu;m)')

    def oct_updateplot(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)  # for ignoring warnings when plotting NaNs

            self.qtimg_confocal.setImage(np.random.rand(10, 10))

            xvals = np.linspace(0, 2000, 2001)
            yvals = np.sin((2*np.pi/2000)*10*np.random.normal(10)*xvals)

            fft_x = np.linspace(0, 1/(xvals[1]-xvals[0]), 2001)
            fft_y = np.abs(np.fft.fft(yvals))

            self.curve_oct_spectrum.setData(xvals, yvals)
            self.curve_oct_fft.setData(fft_x, fft_y)
            processEvents()

def processEvents():
    QtGui.QApplication.processEvents()


def main():
    """Packaged main function that launches GUI"""
    app = QtWidgets.QApplication(sys.argv)
    form = MainExp_GUI()
    form.show()

    app.exec_()


if __name__ == '__main__':
    main()
