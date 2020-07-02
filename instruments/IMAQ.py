from pylablib.aux_libs.devices import IMAQdx


# todo: This is a stupid wrapper for now, ...
#  but in the future we should dig into what IMAQdxPhotonFocusCamera does in the subclass.
class CameraGigE(IMAQdx.IMAQdxPhotonFocusCamera):
    def __init__(self, dev, small_packet_size=False):
        super().__init__(dev, small_packet_size=small_packet_size)
        self.set_value('CameraAttributes/AcquisitionControl/AcquisitionMode', 'SingleFrame')
        self.set_value('CameraAttributes/AcquisitionControl/TriggerSelector', 'Frame Start')
        self.set_value('CameraAttributes/AcquisitionControl/TriggerMode', 'On')
        self.set_value('CameraAttributes/AcquisitionControl/TriggerSource', 'Line 2')
        self.set_value('CameraAttributes/AcquisitionControl/ExposureMode', 'Timed')

    def __del__(self):
        self.close()