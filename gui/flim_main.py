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
    def __init__(self):
        # constructor from QMainWindow parent class
        super(self.__class__, self).__init__()

        # configure PyQTgraph to use white background
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # setupUi sits in exptdesign, as defined by Qt Designer
        self.setupUi(self)
        self.setFixedSize(self.size())

        # Define yellow-hot colormap
        colors = np.array([[0, 0, 0], [255, 0, 0], [255, 255, 0]])
        cmap_yellowhot = pg.ColorMap([0, 0.5, 1], colors)

        # data = scipy.io.loadmat('Leaf Section.mat')
        data = scipy.io.loadmat('Cockroach Leg.mat')
        print(data.keys())
        print(data['TCSPC'].shape)
        print(data['intensity'].shape)
        print(data['tau'].shape)

        nx = int(np.sqrt(data['TCSPC'].shape[0]))  # todo: make this general for non-squared images

        img_intensity = np.reshape(data['intensity'], (nx, nx))
        img_lifetime = np.reshape(data['tau'], (nx, nx))
        curve_timetrace = np.sum(data['TCSPC'], axis=0)

        # setting configuration options
        pg.setConfigOptions(antialias=True)

        self.grid_main.setRowMinimumHeight(0, 400)

        # Create PlotItem for each graphs
        pi_intensity = pg.PlotItem(title='Intensity Image')
        pi_lifetime = pg.PlotItem(title='FLIM Image')
        pi_gated = pg.PlotItem(title='Gated Image')
        pi_hist2d = pg.PlotItem(title='Intensity vs Lifetime')
        pi_hist1d_intensity = pg.PlotItem(title='Intensity Histogram')
        pi_hist1d_lifetime = pg.PlotItem(title='Lifetime Histogram')
        pi_timetrace = pg.PlotItem(title='Fluorescence Time Trace')
        pi_phasor = pg.PlotItem(title='Phasor')

        # Create ImageView for the images
        imv_intensity = ImageView(view=pi_intensity)
        imv_lifetime = ImageView(view=pi_lifetime)
        imv_gated = ImageView(view=pi_gated)
        imv_hist2d = ImageView(view=pi_hist2d)

        imv_intensity.setColorMap(cmap_yellowhot)
        imv_lifetime.setColorMap(cmap_yellowhot)
        imv_gated.setColorMap(cmap_yellowhot)
        imv_hist2d.setColorMap(cmap_yellowhot)

        # Create PlotWidgets for graphs
        pw_hist1d_intensity = pg.PlotWidget(plotItem=pi_hist1d_intensity)
        pw_hist1d_lifetime = pg.PlotWidget(plotItem=pi_hist1d_lifetime)
        pw_timetrace = pg.PlotWidget(plotItem=pi_timetrace)
        pw_phasor = pg.PlotWidget(plotItem=pi_phasor)

        # Add the widgets onto the QGridLayout
        self.grid_main.addWidget(imv_intensity, 0, 0)
        self.grid_main.addWidget(imv_lifetime, 0, 1)
        self.grid_main.addWidget(imv_gated, 0, 2)
        self.grid_main.addWidget(imv_hist2d, 0, 3)
        self.grid_main.addWidget(pw_hist1d_intensity, 1, 0)
        self.grid_main.addWidget(pw_hist1d_lifetime, 1, 1)
        self.grid_main.addWidget(pw_timetrace, 1, 2)
        self.grid_main.addWidget(pw_phasor, 1, 3)

        # Process Data
        hist1d_intensity_y, hist1d_intensity_x = np.histogram(img_intensity, bins=100)
        hist1d_lifetime_y, hist1d_lifetime_x = np.histogram(img_lifetime, bins=100)
        timetrace_y = np.sum(data['TCSPC'], axis=0)
        img_hist2d, x, y = np.histogram2d(np.squeeze(data['tau']), np.squeeze(data['intensity']), bins=100)

        # Display Data
        imv_intensity.setImage(img_intensity)
        imv_lifetime.setImage(img_lifetime)
        imv_gated.setImage(img_intensity) # todo
        imv_hist2d.setImage(img_hist2d)

        # Plot Graphs
        pi_hist1d_intensity.plot(hist1d_intensity_x, hist1d_intensity_y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))
        pi_hist1d_lifetime.plot(hist1d_lifetime_x, hist1d_lifetime_y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))
        pi_timetrace.plot(timetrace_y)

        # Draw Movable Limits for Gating
        vbar_tmin = pg.InfiniteLine(0, movable=True, angle=90)
        pi_timetrace.addItem(vbar_tmin)
        vbar_tmax = pg.InfiniteLine(len(curve_timetrace), movable=True, angle=90)
        pi_timetrace.addItem(vbar_tmax)

        # Connect Signals
        imv_intensity.ui.roiBtn.clicked.connect(imv_lifetime.ui.roiBtn.click)
        imv_intensity.ui.roiBtn.clicked.connect(imv_gated.ui.roiBtn.click)

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

