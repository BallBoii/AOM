from pylablib.aux_libs.devices import IMAQdx, IMAQdx_lib
from pylablib.core.utils import dictionary, py3, general
from pylablib.core.devio import data_format, interface
from pylablib.core.dataproc import image as image_utils
import numpy as np

IMAQdxError = IMAQdx_lib.IMAQdxGenericError


# todo: This is a stupid wrapper for now, ...
#  but in the future we should dig into what IMAQdxPhotonFocusCamera does in the subclass.
# class CameraGigE(IMAQdx.IMAQdxPhotonFocusCamera):
#     def __init__(self, dev, small_packet_size=False):
#         super().__init__(dev, small_packet_size=small_packet_size)
#         self.set_value('CameraAttributes/AcquisitionControl/AcquisitionMode', 'SingleFrame')
#         self.set_value('CameraAttributes/AcquisitionControl/TriggerSelector', 'Frame Start')
#         self.set_value('CameraAttributes/AcquisitionControl/TriggerMode', 'On')
#         self.set_value('CameraAttributes/AcquisitionControl/TriggerSource', 'Line 2')
#         self.set_value('CameraAttributes/AcquisitionControl/ExposureMode', 'Timed')
#
#     def __del__(self):
#         self.close()


class CameraGigE(IMAQdx.IMAQdxCamera):
    """
    IMAQdx interface to a PhotonFocus camera.

    Args:
        name: interface name (can be learned by :func:`list_cameras`; usually, but not always, starts with ``"cam"``)
        mode: connection mode; can be ``"controller"`` (full control) or ``"listener"`` (only reading)
        default_visibility: default attribute visibility when listing attributes;
            can be ``"simple"``, ``"intermediate"`` or ``"advanced"`` (higher mode exposes more attributes).
        small_packet_size: if ``True``, automatically set up Ethernet packet size to 1500 bytes.
    """
    def __init__(self, name='cam0', mode="controller", default_visibility="simple", small_packet_size=False):
        self.small_packet_size=small_packet_size
        super().__init__(name, mode=mode, default_visibility=default_visibility)
        # self._add_settings_node("exposure", self.get_exposure, self.set_exposure)
        # self._add_status_node("readout_time",self.get_readout_time)
        # self._add_status_node("acq_status",self.get_status)
        self.set_value('CameraAttributes/AcquisitionControl/AcquisitionMode', 'SingleFrame')
        self.set_value('CameraAttributes/AcquisitionControl/TriggerSelector', 'Frame Start')
        self.set_value('CameraAttributes/AcquisitionControl/TriggerMode', 'On')
        self.set_value('CameraAttributes/AcquisitionControl/TriggerSource', 'Line 2')
        self.set_value('CameraAttributes/AcquisitionControl/ExposureMode', 'Timed')

    def post_open(self):
        if self.init_done and self.small_packet_size:
            self.set_value("AcquisitionAttributes/PacketSize", 1500, ignore_missing=True)

    def setup_acquisition(self, continuous, frames):
        """
        Setup acquisition mode.

        `continuous` determines whether acquisition runs continuously, or stops after the given number of frames
        (note that :meth:`IMAQdxCamera.acquisition_in_progress` would still return ``True`` in this case, even though new frames are no longer acquired).
        `frames` sets up number of frame buffers.
        """
        super().setup_acquisition(continuous, frames)
        if continuous:
            self.buffers_num = frames//2  # seems to be the case

    def read_multiple_images(self, rng=None, peek=False, skip=False, missing_frame="skip"):
        """
        Read multiple images specified by `rng` (by default, all un-read images).

        If ``peek==True``, return images but not mark them as read.
        If ``skip==True``, mark frames as read but don't read them (i.e., reading with ``peek==True`` and ``skip==True`` does nothing).
        `missing_frame` determines what to do with frames which are out of range (missing or lost):
        can be ``"none"`` (replacing them with ``None``), ``"zero"`` (replacing them with zero-filled frame),
        or ``"skip"`` (skipping them).
        """
        new_range=self.get_new_images_range()
        if rng is None:
            rng = new_range
            missing_frame="skip"
        elif new_range:
            rng = rng[0], min(rng[1], new_range[1]) if isinstance(rng, (tuple, list)) else new_range[1]-rng, new_range[1]
        else:
            rng = None
        frames = None if skip else []
        if rng is None:
            return frames
        if not skip:
            frame_bytes=self.v["PayloadSize"]
            dim = self.get_data_dimensions()
            for i in range(rng[0],rng[1]+1):
                raw_data, buffer_num = self.read_data_raw(frame_bytes, mode="number", buffer_num=i)
                frame=self._bytes_to_frame(raw_data)
                if buffer_num == i:
                    frames.append(frame)
                elif missing_frame == "none":
                    frames.append(None)
                elif missing_frame == "zero":
                    frames.append(np.zeros(dim))
        if not peek:
            self.frame_counter = max(self.frame_counter, rng[1]+1)
        if missing_frame != "none":
            frames = np.asarray(frames)
        return frames

    def snap(self, timeout=20.):
        """Snap a single image (with preset image read mode parameters)"""
        self.refresh_acquisition()
        self.setup_acquisition(False, 1)
        self.start_acquisition()
        self.wait_for_frame(timeout=timeout)
        frame = self.read_multiple_images()[0]
        self.stop_acquisition()
        self.clear_acquisition()
        return frame

    def _get_bpp(self):
        pform=self.v["PixelFormat"]
        if pform.startswith("Mono"):
            pform = pform[4:]
            if pform.endswith("Packed"):
                raise IMAQdxError("packed pixel format isn't currently supported: {}".format("Mono"+pform))
            try:
                return (int(pform)-1)//8+1
            except ValueError:
                pass
        raise IMAQdxError("unrecognized pixel format: {}".format(pform))

    def _bytes_to_frame(self, raw_data):
        dim = self._get_data_dimensions_rc()
        bpp = self._get_bpp()
        dtype = data_format.DataFormat(bpp,"i","<")
        img = np.fromstring(raw_data,dtype=dtype.to_desc("numpy")).reshape((dim[0],dim[1]))
        return image_utils.convert_image_indexing(img, "rct", self.image_indexing)
