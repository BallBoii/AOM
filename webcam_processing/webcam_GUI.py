import sys, time, os
import cv2
import numpy as np
import pyqtgraph as pg
import imutils
from imutils.perspective import four_point_transform
pg.setConfigOption('background', None)

from functools import partial
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtCore, QtWidgets, QtGui

# Import the compiled UI file
import Draft_GUI as MainWindow
Ui_MainWindow = MainWindow.Ui_MainWindow


def my_excepthook(type, value, tback):
    sys.__excepthook__(type, value, tback)


sys.excepthook = my_excepthook


class EyeTrackingApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        '''Initialize pyqtgraph displays'''
        # Add GraphicsLayout for live camera view
        self.glw_camera = pg.GraphicsLayoutWidget()
        self.vb_camera = pg.ViewBox()
        self.plt_camera = pg.PlotItem(viewBox=self.vb_camera)
        self.qtimg_camera = pg.ImageItem()
        self.vb_camera.addItem(self.qtimg_camera)
        self.vb_camera.setContentsMargins(0.01, 0.01, 0.01, 0.01)
        self.vb_camera.invertY(True)
        self.glw_camera.addItem(self.plt_camera)
        self.plt_camera.hideAxis('bottom')
        self.plt_camera.hideAxis('left')

        # Add GraphicsLayout for answer sheet view
        self.glw_answer = pg.GraphicsLayoutWidget()
        self.vb_answer = pg.ViewBox()
        self.plt_answer = pg.PlotItem(viewBox=self.vb_answer)
        self.qtimg_answer = pg.ImageItem()
        self.vb_answer.addItem(self.qtimg_answer)
        self.vb_answer.setContentsMargins(0.01, 0.01, 0.01, 0.01)
        self.vb_answer.invertY(True)
        self.glw_answer.addItem(self.plt_answer)
        self.plt_answer.hideAxis('bottom')
        self.plt_answer.hideAxis('left')

        # Add center of the frame
        self.center_vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(255, 255, 255, 50))
        self.center_hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(255, 255, 255, 50))
        self.plt_camera.addItem(self.center_vline)
        self.plt_camera.addItem(self.center_hline)

        # Add crosshair to the live camera display for indicating the pupil
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen='r')
        self.hline = pg.InfiniteLine(angle=0, movable=False, pen='r')
        self.plt_camera.addItem(self.vline)
        self.plt_camera.addItem(self.hline)
        self.vline.hide()
        self.hline.hide()

        # Add GraphicsLayout for captured image view
        self.glw_capture = pg.GraphicsLayoutWidget()
        self.vb_capture = pg.ViewBox()
        self.plt_capture = pg.PlotItem(viewBox=self.vb_capture)
        self.qtimg_capture = pg.ImageItem()
        self.vb_capture.addItem(self.qtimg_capture)
        self.vb_capture.setContentsMargins(0.01, 0.01, 0.01, 0.01)
        self.vb_capture.invertY(True)
        self.glw_capture.addItem(self.plt_capture)
        self.plt_capture.hideAxis('bottom')
        self.plt_capture.hideAxis('left')

        # Add GraphicsLayoutWidgets to the appropriate containers
        # todo: add live histogram?
        self.grid_live.addWidget(self.glw_camera, 0, 0)
        self.grid_answer.addWidget(self.glw_answer, 0, 0)
        self.grid_capture.addWidget(self.glw_capture, 0, 0)

        self.btn_reset_contrast.clicked.connect(self.reset_contrast)
        self.btn_reset_brightness.clicked.connect(self.reset_brightness)

        self.btn_snapshot.clicked.connect(self.snapshot)
        self.btn_save.clicked.connect(self.snapshot_save)

        self.img_camera = np.array([])
        self.img_answer = np.array([])
        self.img_capture = np.array([])
        self.start_camera()

    def setImage(self):
        if self.img_camera.size:
            self.qtimg_camera.setImage(np.transpose(self.img_camera))
        if self.img_answer.size:
            self.qtimg_answer.setImage(np.transpose(self.img_answer))

    def snapshot(self):
        self.img_capture = self.img_answer
        self.qtimg_capture.setImage(np.transpose(self.img_capture))

    def snapshot_save(self):
        if not len(self.img_capture):
            self.snapshot()

        dialog = QtGui.QFileDialog(directory=os.path.expanduser(os.path.join('~', 'Documents')))
        dialog.setAcceptMode(1)

        targetfile = dialog.getSaveFileName(filter='PNG image (*.PNG)')[0]
        if targetfile != '':
            cv2.imwrite(targetfile, self.img_capture)

    def start_camera(self):
        # fixme: This is sloppy. Create and store the camera object properly.
        th = Camera(self)
        th.updateCamera.connect(self.setImage)
        th.start()

    def camera_mouse_moved(self, pos):
        if self.plt_camera.sceneBoundingRect().contains(pos):
            p = self.vb_camera.mapSceneToView(pos)
            x = p.x()
            y = p.y()
            if 0 < x < self.img_camera.shape[1] and 0 < y < self.img_camera.shape[0]:
                self.vline.setPos(p.x())
                self.hline.setPos(p.y())

    def camera_mouse_clicked(self, event):
        pos = event.scenePos()
        if self.plt_camera.sceneBoundingRect().contains(pos) and event.button() == 1:
            p = self.vb_camera.mapSceneToView(pos)

            offset_x = p.x() - self.img_camera.shape[1] / 2
            offset_y = p.y() - self.img_camera.shape[0] / 2
            self.camera_drive(offset_x, offset_y)

    def reset_contrast(self):
        self.slider_contrast.setValue(1000)

    def reset_brightness(self):
        self.slider_brightness.setValue(0)

    def closeEvent(self, *args, **kwargs):
        pass
        # todo: fix exit code -1073740791 (0xC0000409)
        # try closing the camera?


class Camera(QtCore.QThread):
    updateCamera = pyqtSignal()

    def run(self):
        time.sleep(0.02)
        cap = cv2.VideoCapture(0)

        ret, frame = cap.read()

        # todo: move calibrated crop somewhere else
        crop_y1 = 0
        crop_y2 = frame.shape[0]
        crop_x1 = 0
        crop_x2 = frame.shape[1]
        self.parent().center_vline.setPos((crop_x2-crop_x1)/2)
        self.parent().center_hline.setPos((crop_y2-crop_y1)/2)


        num_avg = 10
        i = 0
        img_avg = np.zeros(frame.shape[0:2])

        while True:
            ret, frame = cap.read()
            if ret:
                i += 1

                roi = frame[crop_y1:crop_y2, crop_x1:crop_x2]  # dimension of  video (y:y+w,x:x+h)
                rows, cols, _ = roi.shape
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                contrast = self.parent().slider_contrast.value() / 1000
                brightness = self.parent().slider_brightness.value() * 2
                gray_roi = cv2.addWeighted(gray_roi, contrast, gray_roi, 0, brightness)

                img_avg = (img_avg*(i-1) + gray_roi)/i

                # gray_roi = cv2.GaussianBlur(gray_roi, (7, 7), 0)
                self.parent().img_camera = gray_roi
                if i % num_avg == 0:
                    self.parent().img_answer = self.image_process(gray_roi)
                    i = 0
                    # img_avg = np.zeros(frame.shape[0:2])
                self.updateCamera.emit()


    def image_process(self, original):
        blurred = cv2.GaussianBlur(original, (5, 5), 0)
        # edged = cv2.Canny(blurred, 75, 220)  # todo: check number
        edged = cv2.Canny(blurred, self.parent().int_canny_1.value(), self.parent().int_canny_2.value())

        cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        docCnt = None
        # ensure that at least one contour was found
        if len(cnts) > 0:
            # sort the contours according to their size in
            # descending order
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
            # loop over the sorted contours
            for c in cnts:
                # approximate the contour
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                # if our approximated contour has four points,
                # then we can assume we have found the paper
                if len(approx) == 4:
                    docCnt = approx
                    break

        # apply a four point perspective transform to both the
        # original image and grayscale image to obtain a top-down
        # birds eye view of the paper
        # paper = four_point_transform(image, docCnt.reshape(4, 2))
        if docCnt is not None:
            warped = four_point_transform(original, docCnt.reshape(4, 2))
            return warped
        else:
            return edged


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = EyeTrackingApp()
    window.show()
    sys.exit(app.exec())
