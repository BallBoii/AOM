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

        self.data = data

        nx = int(np.sqrt(data['TCSPC'].shape[0]))  # todo: make this general for non-squared images

        img_intensity = np.reshape(data['intensity'], (nx, nx))
        img_lifetime = np.reshape(data['tau'], (nx, nx))
        curve_timetrace = np.sum(data['TCSPC'], axis=0)

        # setting configuration options
        pg.setConfigOptions(antialias=True)

        self.grid_main.setRowMinimumHeight(0, 400)

        # Create PlotItem for each graphs
        self.pi_intensity = pg.PlotItem(title='Intensity Image')
        self.pi_lifetime = pg.PlotItem(title='FLIM Image')
        self.pi_gated = pg.PlotItem(title='Gated Image')
        self.pi_hist2d = pg.PlotItem(title='Intensity vs Lifetime')
        self.pi_hist1d_intensity = pg.PlotItem(title='Intensity Histogram')
        self.pi_hist1d_lifetime = pg.PlotItem(title='Lifetime Histogram')
        self.pi_timetrace = pg.PlotItem(title='Fluorescence Time Trace')
        self.pi_phasor = pg.PlotItem(title='Phasor')

        # Create ImageView for the images
        self.imv_intensity = ImageView(view=self.pi_intensity)
        self.imv_lifetime = ImageView(view=self.pi_lifetime)
        self.imv_gated = ImageView(view=self.pi_gated)
        self.imv_hist2d = ImageView(view=self.pi_hist2d)

        self.imv_intensity.setColorMap(cmap_yellowhot)
        self.imv_lifetime.setColorMap(cmap_yellowhot)
        self.imv_gated.setColorMap(cmap_yellowhot)
        self.imv_hist2d.setColorMap(cmap_yellowhot)

        # Create PlotWidgets for graphs
        self.pw_hist1d_intensity = pg.PlotWidget(plotItem=self.pi_hist1d_intensity)
        self.pw_hist1d_lifetime = pg.PlotWidget(plotItem=self.pi_hist1d_lifetime)
        self.pw_timetrace = pg.PlotWidget(plotItem=self.pi_timetrace)
        self.pw_phasor = pg.PlotWidget(plotItem=self.pi_phasor)

        # Add the widgets onto the QGridLayout
        self.grid_main.addWidget(self.imv_intensity, 0, 0)
        self.grid_main.addWidget(self.imv_lifetime, 0, 1)
        self.grid_main.addWidget(self.imv_gated, 0, 2)
        self.grid_main.addWidget(self.imv_hist2d, 0, 3)
        self.grid_main.addWidget(self.pw_hist1d_intensity, 1, 0)
        self.grid_main.addWidget(self.pw_hist1d_lifetime, 1, 1)
        self.grid_main.addWidget(self.pw_timetrace, 1, 2)
        self.grid_main.addWidget(self.pw_phasor, 1, 3)

        # Process Data
        hist1d_intensity_y, hist1d_intensity_x = np.histogram(img_intensity, bins=100)
        hist1d_lifetime_y, hist1d_lifetime_x = np.histogram(img_lifetime, bins=100)
        timetrace_y = np.sum(data['TCSPC'], axis=0)
        img_hist2d, x, y = np.histogram2d(np.squeeze(data['tau']), np.squeeze(data['intensity']), bins=100)

        # Display Data
        self.imv_intensity.setImage(img_intensity)
        self.imv_lifetime.setImage(img_lifetime)
        self.imv_gated.setImage(img_intensity) # todo
        self.imv_hist2d.setImage(img_hist2d)

        # Plot Graphs
        self.pi_hist1d_intensity.plot(hist1d_intensity_x, hist1d_intensity_y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))
        self.pi_hist1d_lifetime.plot(hist1d_lifetime_x, hist1d_lifetime_y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))
        self.pi_timetrace.plot(timetrace_y)

        # Draw Movable Limits for Gating
        self.vbar_tmin = pg.InfiniteLine(0, movable=True, angle=90)
        self.pi_timetrace.addItem(self.vbar_tmin)
        self.vbar_tmax = pg.InfiniteLine(len(curve_timetrace), movable=True, angle=90)
        self.pi_timetrace.addItem(self.vbar_tmax)

        self.vbar_tmin.sigPositionChanged.connect(self.update_gate)
        self.vbar_tmax.sigPositionChanged.connect(self.update_gate)

        # Connect Signals
        self.imv_intensity.ui.roiBtn.clicked.connect(self.imv_lifetime.ui.roiBtn.click)
        self.imv_intensity.ui.roiBtn.clicked.connect(self.imv_gated.ui.roiBtn.click)

    def newfunction(self):
        print('new')

    def update_gate(self):
        imin = round(self.vbar_tmin.getXPos())
        imax = round(self.vbar_tmax.getXPos())

        nx = int(np.sqrt(self.data['TCSPC'].shape[0]))  # todo: make this general for non-squared images

        img_gated = np.reshape(np.sum(self.data['TCSPC'][:, imin:imax], axis=1), (nx, nx))
        self.imv_gated.setImage(img_gated)


def main():
    """Packaged main function that launches GUI"""
    app = QtWidgets.QApplication(sys.argv)

    form = MainFLIM()
    form.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

