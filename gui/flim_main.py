from PyQt6 import QtGui, QtCore, QtWidgets

# system imports
import sys, os, struct, scipy.io, warnings, functools, time, datetime
import pyqtgraph as pg
import numpy as np
# import pdb
# import csv
#
# # user-defined imports
# import file_utils
# import instruments as instr
# import experiments as exp

# import UI files
import flim_gui as mainwindow


def my_excepthook(type, value, tback):
    sys.__excepthook__(type, value, tback)


sys.excepthook = my_excepthook


class ImageView(pg.ImageView):

    # constructor which inherit original
    # ImageView
    def __init__(self, *args, **kwargs):
        pg.ImageView.__init__(self, *args, **kwargs)
        self.timeLine.hide()
        self.ui.roiPlot.setVisible(False)

    def roiClicked(self):
        if self.ui.roiBtn.isChecked():
            self.roi.show()
            self.roiChanged()
        else:
            self.roi.hide()


class MainFLIM(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, galvo2=False):
        # constructor from QMainWindow parent class
        super(self.__class__, self).__init__()

        # configure PyQTgraph to use white background
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # setupUi sits in exptdesign, as defined by Qt Designer
        self.setupUi(self)

        self.setFixedSize(self.size())

        # data = scipy.io.loadmat('Leaf Section.mat')
        data = scipy.io.loadmat('Cockroach Leg.mat')
        print(data.keys())
        print(data['TCSPC'].shape)
        print(data['intensity'].shape)
        print(data['tau'].shape)

        img_intensity = np.reshape(data['intensity'], (201,201))
        img_tau = np.reshape(data['tau'], (201,201))
        curve_timetrace = np.sum(data['TCSPC'], axis=0)

        # creating a label
        label = QtWidgets.QLabel("Geeksforgeeks Image View")

        # setting minimum width
        label.setMinimumWidth(130)

        # making label do word wrap
        label.setWordWrap(True)

        # setting configuration options
        pg.setConfigOptions(antialias=True)

        # Create random 3D data set with noisy signals
        img = pg.gaussianFilter(np.random.normal(
            size=(200, 200)), (5, 5)) * 20 + 100

        # Define yellow-hot colormap
        colors = np.array([[0, 0, 0], [255, 0, 0], [255, 255, 0]])
        cmap = pg.ColorMap([0, 0.5, 1], colors)

        '''Fig. 0: Intensity Histogram'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        wgt = pg.PlotWidget(plotItem=plot)
        self.grid_main.addWidget(wgt, 0, 0)


        '''Fig. 1: Intensity Image'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 1: Intensity Image')

        roi = pg.RectROI((0, 0), (10, 10))
        roi.sigRegionChangeFinished.connect(self.newfunction)
        # creating image view object
        imv = ImageView(view=plot, roi=roi)
        imv.setImage(img_intensity)
        imv.setColorMap(cmap)
        # imv.ui.roiBtn.clicked.connect(self.newfunction)

        # adding label in the layout
        self.grid_main.addWidget(imv, 0, 0)

        '''Fig. 2: FLIM Image'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 2: FLIM Image')

        # creating image view object
        imv2 = ImageView(view=plot)
        imv2.setImage(img_tau)
        imv2.setColorMap(cmap)
        imv2.roi.sigRegionChangeFinished.connect(self.newfunction)

        self.grid_main.addWidget(imv2, 0, 1)

        # todo: connect two ROIs
        imv.ui.roiBtn.clicked.connect(imv2.ui.roiBtn.click)
        imv2.ui.roiBtn.hide()
        # imv2.ui.roiBtn.clicked.connect(imv.ui.roiBtn.click) #todo: block signal

        # adding label in the layout

        '''Fig. 3: Gated Image'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 3: Gated Image')

        # creating image view object
        imv2 = ImageView(view=plot)
        imv2.setImage(img_tau)
        imv2.setColorMap(cmap)

        self.grid_main.addWidget(imv2, 0, 2)

        '''Fig. 4: Intensity Histogram'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        wgt = pg.PlotWidget(plotItem=plot)

        y, x = np.histogram(img_intensity, bins=100)
        plot.plot(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))

        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 4: Intensity Histogram')

        # adding label in the layout
        self.grid_main.addWidget(wgt, 1, 0)

        '''Fig. 5: Lifetime Histogram'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        wgt = pg.PlotWidget(plotItem=plot)
        y, x = np.histogram(img_tau, bins=100)
        plot.plot(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))

        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 5: Lifetime Histogram')

        # adding label in the layout
        self.grid_main.addWidget(wgt, 1, 1)

        '''Fig. 6: Fluorescence Time Trace'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        wgt = pg.PlotWidget(plotItem=plot)

        curve_timetrace.shape
        plot.plot(curve_timetrace)

        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 6: Fluorescence Time Trace')

        # adding label in the layout
        self.grid_main.addWidget(wgt, 1, 2)

        '''Fig. 7: Intensity vs Lifetime Histogram'''
        # Add Plot item to show axis labels
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 3: Gated Image')

        H, x, y = np.histogram2d(np.squeeze(data['tau']), np.squeeze(data['intensity']), bins=100)

        # creating image view object
        imv2 = ImageView(view=plot)
        imv2.setImage(H)
        imv2.setColorMap(cmap)

        # adding label in the layout
        self.grid_main.addWidget(imv2, 0, 3)

        '''Fig. 8: Phasor'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        wgt = pg.PlotWidget(plotItem=plot)

        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 8: Phasor')

        # adding label in the layout
        self.grid_main.addWidget(wgt, 1, 3)



        # '''Fig. 5: Lifetime Histogram'''
        # # Add Plot item to show axis labels
        # plot = pg.PlotItem()
        # wgt = pg.PlotWidget(plotItem=plot)
        #
        # plot.setLabel(axis='left', text='Y-axis')
        # plot.setLabel(axis='bottom', text='X-axis')
        # plot.setTitle('Fig. 5: Lifetime Histogram')
        #
        # # adding label in the layout
        # self.grid_main.addWidget(wgt, 0, 0)
        #
        # '''Fig. 5: Lifetime Histogram'''
        # # Add Plot item to show axis labels
        # plot = pg.PlotItem()
        # wgt = pg.PlotWidget(plotItem=plot)
        #
        # plot.setLabel(axis='left', text='Y-axis')
        # plot.setLabel(axis='bottom', text='X-axis')
        # plot.setTitle('Fig. 5: Lifetime Histogram')
        #
        # # adding label in the layout
        # self.grid_main.addWidget(wgt, 1, 2)

    def newfunction(self):
        print('new')


def main():
    """Packaged main function that launches GUI"""
    app = QtWidgets.QApplication(sys.argv)

    form = MainFLIM()
    form.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

