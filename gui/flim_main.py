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


class MainExp_GUI(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, galvo2=False):
        # constructor from QMainWindow parent class
        super(self.__class__, self).__init__()

        # configure PyQTgraph to use white background
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # setupUi sits in exptdesign, as defined by Qt Designer
        self.setupUi(self)

        self.setFixedSize(self.size())

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

        '''Fig. 1: Intensity Image'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 1: Intensity Image')

        roi = pg.RectROI((0, 0), (10, 10))
        roi.sigRegionChanged.connect(self.newfunction)
        # creating image view object
        imv = pg.ImageView(view=plot, roi=roi)
        imv.setImage(img)
        imv.setColorMap(cmap)

        # adding label in the layout
        self.grid_main.addWidget(imv, 0, 0)

        '''Fig. 2: FLIM Image'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 2: FLIM Image')

        # creating image view object
        imv = pg.ImageView(view=plot)
        imv.setImage(img)
        imv.setColorMap(cmap)

        # adding label in the layout
        self.grid_main.addWidget(imv, 0, 1)

        '''Fig. 3: Gated Image'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 3: Gated Image')

        # creating image view object
        imv = pg.ImageView(view=plot)
        imv.setImage(img)
        imv.setColorMap(cmap)

        # adding label in the layout
        self.grid_main.addWidget(imv, 0, 2)

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
        # self.grid_main.addWidget(wgt, 1, 0)
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
        # self.grid_main.addWidget(wgt, 1, 1)

        '''Fig. 6: Histogram Image'''
        # Add Plot item to show axis labels
        plot = pg.PlotItem()
        plot.setLabel(axis='left', text='Y-axis')
        plot.setLabel(axis='bottom', text='X-axis')
        plot.setTitle('Fig. 6: Histogram Image')

        # creating image view object
        imv = pg.ImageView(view=plot)
        imv.setImage(img)
        imv.setColorMap(cmap)

        # adding label in the layout
        self.grid_main.addWidget(imv, 1, 2)

    def newfunction(self):
        print('new')


def main():
    """Packaged main function that launches GUI"""
    app = QtWidgets.QApplication(sys.argv)

    form = MainExp_GUI()
    form.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

