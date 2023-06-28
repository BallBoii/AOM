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

        # todo: cleanup
        # data = scipy.io.loadmat('Leaf Section.mat')
        data = scipy.io.loadmat('Cockroach Leg.mat')
        # print(data.keys())
        # print(data['TCSPC'].shape)
        # print(data['intensity'].shape)
        # print(data['tau'].shape)

        self.data = data
        self.img_shape = (int(np.sqrt(data['TCSPC'].shape[0])), int(np.sqrt(data['TCSPC'].shape[0])))
        self.nbins = data['TCSPC'].shape[1]

        self.img_intensity = np.reshape(data['intensity'], self.img_shape)
        self.img_lifetime = np.reshape(data['tau'], self.img_shape)
        self.img_timetrace = np.reshape(data['TCSPC'], (self.img_shape[0], self.img_shape[1], self.nbins))
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
        hist1d_intensity_y, hist1d_intensity_x = np.histogram(self.img_intensity, bins=100)
        hist1d_lifetime_y, hist1d_lifetime_x = np.histogram(self.img_lifetime, bins=100)
        timetrace_y = np.sum(data['TCSPC'], axis=0)
        img_hist2d, x, y = np.histogram2d(np.squeeze(data['tau']), np.squeeze(data['intensity']), bins=100)

        # Initialize Parameters for Gating and Filtering
        self.gated_imin = 0
        self.gated_imax = self.nbins
        self.filter_intensity_min = hist1d_intensity_x[0]
        self.filter_intensity_max = hist1d_intensity_x[-1]
        self.filter_lifetime_min = hist1d_lifetime_x[0]
        self.filter_lifetime_max = hist1d_lifetime_x[-1]

        # Display Data
        self.imv_intensity.setImage(self.img_intensity)
        self.imv_lifetime.setImage(self.img_lifetime)
        self.imv_gated.setImage(self.img_intensity)
        self.imv_hist2d.setImage(img_hist2d)

        # Plot Graphs
        self.plt_hist1d_intensity = self.pi_hist1d_intensity.plot(hist1d_intensity_x, hist1d_intensity_y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))
        self.plt_hist1d_lifetime = self.pi_hist1d_lifetime.plot(hist1d_lifetime_x, hist1d_lifetime_y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))
        self.plt_timetrace = self.pi_timetrace.plot(timetrace_y, pen='b')
        self.plt_hist1d_intensity_roi = self.pi_hist1d_intensity.plot([], [], stepMode=True, fillLevel=0, brush=(0, 255, 0, 80))
        self.plt_hist1d_lifetime_roi = self.pi_hist1d_lifetime.plot([], [], stepMode=True, fillLevel=0, brush=(0, 255, 0, 80))
        self.plt_timetrace_roi = self.pi_timetrace.plot([], pen='g')

        # Draw Movable Limits for Time Gating
        self.vbar_tmin = pg.InfiniteLine(0, movable=True, angle=90, pen='r')
        self.vbar_tmax = pg.InfiniteLine(len(curve_timetrace), movable=True, angle=90, pen='r')
        self.pi_timetrace.addItem(self.vbar_tmin)
        self.pi_timetrace.addItem(self.vbar_tmax)

        # Draw Movable Limits for Intensity and Lifetime Filtering
        self.vbar_intensity_min = pg.InfiniteLine(self.filter_intensity_min, movable=True, angle=90, pen='r')
        self.vbar_intensity_max = pg.InfiniteLine(self.filter_intensity_max, movable=True, angle=90, pen='r')
        self.pi_hist1d_intensity.addItem(self.vbar_intensity_min)
        self.pi_hist1d_intensity.addItem(self.vbar_intensity_max)

        self.vbar_lifetime_min = pg.InfiniteLine(self.filter_lifetime_min, movable=True, angle=90, pen='r')
        self.vbar_lifetime_max = pg.InfiniteLine(self.filter_lifetime_max, movable=True, angle=90, pen='r')
        self.pi_hist1d_lifetime.addItem(self.vbar_lifetime_min)
        self.pi_hist1d_lifetime.addItem(self.vbar_lifetime_max)

        # Connect Signals
        self.imv_intensity.ui.roiBtn.clicked.connect(lambda: self.roiClicked(self.imv_intensity))
        self.imv_lifetime.ui.roiBtn.clicked.connect(lambda: self.roiClicked(self.imv_lifetime))
        self.imv_gated.ui.roiBtn.clicked.connect(lambda: self.roiClicked(self.imv_gated))

        self.imv_intensity.roi.sigRegionChangeStarted.connect(lambda: self.roiChangeStarted(self.imv_intensity))
        self.imv_intensity.roi.sigRegionChanged.connect(lambda: self.roiChanged(self.imv_intensity))
        self.imv_intensity.roi.sigRegionChangeFinished.connect(lambda: self.roiChangeFinished(self.imv_intensity))

        self.imv_lifetime.roi.sigRegionChangeStarted.connect(lambda: self.roiChangeStarted(self.imv_lifetime))
        self.imv_lifetime.roi.sigRegionChanged.connect(lambda: self.roiChanged(self.imv_lifetime))
        self.imv_lifetime.roi.sigRegionChangeFinished.connect(lambda: self.roiChangeFinished(self.imv_lifetime))

        self.imv_gated.roi.sigRegionChangeStarted.connect(lambda: self.roiChangeStarted(self.imv_gated))
        self.imv_gated.roi.sigRegionChanged.connect(lambda: self.roiChanged(self.imv_gated))
        self.imv_gated.roi.sigRegionChangeFinished.connect(lambda: self.roiChangeFinished(self.imv_gated))

        self.vbar_tmin.sigPositionChanged.connect(self.update_tgate)
        self.vbar_tmin.sigPositionChangeFinished.connect(self.update_gate_tmin)
        self.vbar_tmax.sigPositionChanged.connect(self.update_tgate)
        self.vbar_tmax.sigPositionChangeFinished.connect(self.update_gate_tmax)

        self.vbar_intensity_min.sigPositionChanged.connect(self.update_filter_intensity)
        self.vbar_intensity_max.sigPositionChanged.connect(self.update_filter_intensity)

        self.vbar_lifetime_min.sigPositionChanged.connect(self.update_filter_lifetime)
        self.vbar_lifetime_max.sigPositionChanged.connect(self.update_filter_lifetime)

        self.chkbx_filter_intensity.setChecked(False)
        self.vbar_intensity_min.setVisible(False)
        self.vbar_intensity_max.setVisible(False)
        self.chkbx_filter_intensity.stateChanged.connect(self.vbar_intensity_min.setVisible)
        self.chkbx_filter_intensity.stateChanged.connect(self.vbar_intensity_max.setVisible)
        self.chkbx_filter_intensity.stateChanged.connect(self.update_gated)

        self.chkbx_filter_lifetime.setChecked(False)
        self.vbar_lifetime_min.setVisible(False)
        self.vbar_lifetime_max.setVisible(False)
        self.chkbx_filter_lifetime.stateChanged.connect(self.vbar_lifetime_min.setVisible)
        self.chkbx_filter_lifetime.stateChanged.connect(self.vbar_lifetime_max.setVisible)
        self.chkbx_filter_lifetime.stateChanged.connect(self.update_gated)

        self.chkbx_filter_time.setChecked(True)
        self.vbar_tmin.setVisible(True)
        self.vbar_tmax.setVisible(True)
        self.chkbx_filter_time.stateChanged.connect(self.vbar_tmin.setVisible)
        self.chkbx_filter_time.stateChanged.connect(self.vbar_tmax.setVisible)
        self.chkbx_filter_time.stateChanged.connect(self.update_gated)

    def roiClicked(self, imv):
        if not self.imv_intensity == imv: self.imv_intensity.ui.roiBtn.blockSignals(True)
        if not self.imv_lifetime == imv: self.imv_lifetime.ui.roiBtn.blockSignals(True)
        if not self.imv_gated == imv: self.imv_gated.ui.roiBtn.blockSignals(True)

        if not self.imv_intensity == imv:
            self.imv_intensity.ui.roiBtn.click()
            self.imv_intensity.roiClicked()
        if not self.imv_lifetime == imv:
            self.imv_lifetime.ui.roiBtn.click()
            self.imv_lifetime.roiClicked()
        if not self.imv_gated == imv:
            self.imv_gated.ui.roiBtn.click()
            self.imv_gated.roiClicked()

        self.imv_intensity.ui.roiBtn.blockSignals(False)
        self.imv_lifetime.ui.roiBtn.blockSignals(False)
        self.imv_gated.ui.roiBtn.blockSignals(False)

    def roiChangeStarted(self, imv):
        if not self.imv_intensity == imv: self.imv_intensity.roi.blockSignals(True)
        if not self.imv_lifetime == imv: self.imv_lifetime.roi.blockSignals(True)
        if not self.imv_gated == imv: self.imv_gated.roi.blockSignals(True)

    def roiChanged(self, imv, force_update=True):
        state = imv.roi.getState()
        if not self.imv_intensity == imv: self.imv_intensity.roi.setState(state)
        if not self.imv_lifetime == imv: self.imv_lifetime.roi.setState(state)
        if not self.imv_gated == imv: self.imv_gated.roi.setState(state)

        img_intensity = imv.roi.getArrayRegion(self.img_intensity, imv.imageItem)
        hist1d_intensity_y, hist1d_intensity_x = np.histogram(img_intensity, bins=100)
        self.plt_hist1d_intensity_roi.setData(hist1d_intensity_x, hist1d_intensity_y)

        img_lifetime = imv.roi.getArrayRegion(self.img_lifetime, imv.imageItem)
        hist1d_lifetime_y, hist1d_lifetime_x = np.histogram(img_lifetime, bins=100)
        self.plt_hist1d_lifetime_roi.setData(hist1d_lifetime_x, hist1d_lifetime_y)

        # # todo: this works but is very slow, move to roiChangeFinished?
        # img_timetrace = self.imv_intensity.roi.getArrayRegion(self.img_timetrace, imv.imageItem)
        # self.plt_timetrace_roi.setData(np.sum(img_timetrace, axis=(0, 1)))

    def roiChangeFinished(self, imv):
        self.roiChanged(imv, force_update=True)
        self.imv_intensity.roi.blockSignals(False)
        self.imv_lifetime.roi.blockSignals(False)
        self.imv_gated.roi.blockSignals(False)

        img_timetrace = imv.roi.getArrayRegion(self.img_timetrace, imv.imageItem)
        self.plt_timetrace_roi.setData(np.sum(img_timetrace, axis=(0, 1)))

    def update_tgate(self):
        self.gated_imin = round(self.vbar_tmin.getXPos())
        self.gated_imax = round(self.vbar_tmax.getXPos())

        self.update_gated()

    def update_gate_tmin(self):
        self.vbar_tmax.setBounds((self.gated_imin, self.data['TCSPC'].shape[1]))

    def update_gate_tmax(self):
        self.vbar_tmin.setBounds((0, self.gated_imax))

    def update_filter_intensity(self):
        self.filter_intensity_min = round(self.vbar_intensity_min.getXPos())
        self.filter_intensity_max = round(self.vbar_intensity_max.getXPos())

        self.update_gated()

    def update_filter_lifetime(self):
        self.filter_lifetime_min = round(self.vbar_lifetime_min.getXPos())
        self.filter_lifetime_max = round(self.vbar_lifetime_max.getXPos())
        self.update_gated()

    def update_gated(self):
        if self.chkbx_filter_time.isChecked():
            img_gated = np.reshape(np.sum(self.data['TCSPC'][:, self.gated_imin:self.gated_imax], axis=1), self.img_shape)
        else:
            img_gated = self.img_intensity[:]
        img_gated = img_gated.astype('float64')

        if self.chkbx_filter_intensity.isChecked():
            img_gated[self.img_intensity < self.filter_intensity_min] = np.nan
            img_gated[self.img_intensity > self.filter_intensity_max] = np.nan

        if self.chkbx_filter_lifetime.isChecked():
            img_gated[self.img_lifetime < self.filter_lifetime_min] = np.nan
            img_gated[self.img_lifetime > self.filter_lifetime_max] = np.nan

        self.imv_gated.setImage(img_gated) #, autoLevels=False)


def main():
    """Packaged main function that launches GUI"""
    app = QtWidgets.QApplication(sys.argv)

    form = MainFLIM()
    form.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

