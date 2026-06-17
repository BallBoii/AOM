# -*- coding: utf-8 -*-
"""
Oscilloscope.py

Minimal Keysight InfiniiVision 6000 X-Series / DSO-X 6004A control file.

Use case:
    CH1 = analog APD fluorescence signal
    CH2 = PulseBlaster trigger signal
    Trigger = rising edge on CH2
    Acquisition = capture CH1 waveform after PulseBlaster trigger

This file intentionally includes only the SCPI needed for QDS/NV pulse experiments,
but keeps the class general enough for other oscilloscope usage.
"""

import time
import numpy as np

if __name__ == "__main__":
    import GPIBdev
    import instr_widget
    import GPIBdev_gui
else:
    from instruments import GPIBdev
    from instruments import GPIBdev_gui
    from instruments import instr_widget


class DSOX6004A(GPIBdev.GPIBdev):
    """
    Keysight / Agilent InfiniiVision DSO-X 6004A oscilloscope.

    Important default experiment mapping:
        CH1: APD analog fluorescence
        CH2: PulseBlaster trigger for scope
    """

    VALID_CHANNELS = (1, 2, 3, 4)

    def __init__(self, dev, timeout_ms=60000):
        super().__init__(dev, timeout_ms=timeout_ms)

        # self.name = "DSO-X 6004A"

        # Conservative software-side limits.
        # Real allowed range depends on probe, impedance, and hardware option.
        self.time_range_min = 1e-9
        self.time_range_max = 50.0

        self.volt_scale_min = 1e-3
        self.volt_scale_max = 10.0

        self.points_min = 100
        self.points_max = 8_000_000

        self.default_signal_channel = 1
        self.default_trigger_channel = 2

        self.write("*CLS")
        self.set_remote_header(False)

    # ------------------------------------------------------------------
    # Low-level wrappers
    # ------------------------------------------------------------------

    def write(self, cmd):
        """Send one SCPI command."""
        self.gpib_write(cmd)

    def ask(self, cmd):
        """Send query and read response."""
        if hasattr(self, "gpib_query"):
            return self.gpib_query(cmd)

        raise AttributeError("No ask method found in GPIBdev. Check GPIBdev.py.")

    def ask_float(self, cmd):
        return float(str(self.ask(cmd)).strip())

    def ask_int(self, cmd):
        return int(float(str(self.ask(cmd)).strip()))

    def set_remote_header(self, state=False):
        """
        OFF gives simpler query responses.
        """
        self.write(":SYSTem:HEADer %s" % ("ON" if state else "OFF"))

    def idn(self):
        return str(self.ask("*IDN?")).strip()

    def reset(self):
        """
        Full reset. Use only when you really want to clear front-panel settings.
        """
        self.write("*RST")
        self.write("*CLS")
        time.sleep(0.5)

    def clear_errors(self):
        self.write("*CLS")

    def get_error(self):
        return str(self.ask(":SYSTem:ERRor?")).strip()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _check_channel(self, channel):
        if channel not in self.VALID_CHANNELS:
            raise ValueError("Invalid channel %r. Use 1, 2, 3, or 4." % channel)

    def _check_positive(self, value, name):
        if value <= 0:
            raise ValueError("%s must be positive, got %r." % (name, value))

    # ------------------------------------------------------------------
    # Channel setup
    # ------------------------------------------------------------------

    def channel_on(self, channel, state=True):
        self._check_channel(channel)
        self.write(":CHANnel%d:DISPlay %s" % (channel, "ON" if state else "OFF"))

    def set_channel(
        self,
        channel,
        scale=0.5,
        offset=0.0,
        coupling="DC",
        impedance="FIFTy",
        probe=1.0,
        bw_limit=False,
        label=None,
        display=True,
    ):
        """
        Configure one analog channel.

        scale:
            V/div.
        offset:
            Vertical offset in V.
        coupling:
            "DC" or "AC".
        impedance:
            "ONEMeg" or "FIFTy".
            Use ONEMeg unless you know your signal/source is meant for 50 ohm.
        probe:
            Probe attenuation ratio. For direct BNC usually 1.0.
        """
        self._check_channel(channel)
        self._check_positive(scale, "scale")
        self._check_positive(probe, "probe")

        coupling = coupling.upper()
        if coupling not in ("DC", "AC"):
            raise ValueError("coupling must be 'DC' or 'AC'.")

        impedance = impedance.upper()
        if impedance in ("1M", "1MEG", "ONEMEG"):
            impedance = "ONEMeg"
        elif impedance in ("50", "50OHM", "FIFTY"):
            impedance = "FIFTy"
        else:
            raise ValueError("impedance must be 'ONEMeg' or 'FIFTy'.")

        self.write(":CHANnel%d:DISPlay %s" % (channel, "ON" if display else "OFF"))
        self.write(":CHANnel%d:COUPling %s" % (channel, coupling))
        self.write(":CHANnel%d:IMPedance %s" % (channel, impedance))
        self.write(":CHANnel%d:PROBe %g" % (channel, probe))
        self.write(":CHANnel%d:SCALe %g" % (channel, scale))
        self.write(":CHANnel%d:OFFSet %g" % (channel, offset))
        self.write(":CHANnel%d:BWLimit %s" % (channel, "ON" if bw_limit else "OFF"))

        if label is not None:
            self.write(':CHANnel%d:LABel "%s"' % (channel, str(label)[:32]))

    # ------------------------------------------------------------------
    # Timebase and trigger
    # ------------------------------------------------------------------

    def set_timebase(self, time_range, position=0.0):
        """
        Set horizontal acquisition window.

        time_range:
            Full screen time range in seconds.
            Example: 10 us total window -> time_range=10e-6

        position:
            Trigger position/time offset in seconds.
            Usually 0.0 is fine for pulse-triggered acquisition.
        """
        self._check_positive(time_range, "time_range")

        if not (self.time_range_min <= time_range <= self.time_range_max):
            print("WARNING: requested time_range may be outside practical range: %g s" % time_range)

        self.write(":TIMebase:MODE MAIN")
        self.write(":TIMebase:RANGe %g" % time_range)
        self.write(":TIMebase:POSition %g" % position)

    def set_edge_trigger(
        self,
        source_channel=2,
        level=1.0,
        slope="POSitive",
        sweep="NORMal",
        coupling="DC",
    ):
        """
        Configure edge trigger.

        For your setup:
            source_channel = 2
            slope = POSitive
            level maybe 1.0 V to 2.5 V depending on PulseBlaster TTL level.
        """
        self._check_channel(source_channel)

        slope = slope.upper()
        if slope in ("POS", "POSITIVE", "RISE", "RISING"):
            slope = "POSitive"
        elif slope in ("NEG", "NEGATIVE", "FALL", "FALLING"):
            slope = "NEGative"
        else:
            raise ValueError("slope must be POSitive or NEGative.")

        sweep = sweep.upper()
        if sweep in ("NORM", "NORMAL"):
            sweep = "NORMal"
        elif sweep in ("AUTO",):
            sweep = "AUTO"
        else:
            raise ValueError("sweep must be NORMal or AUTO.")

        coupling = coupling.upper()
        if coupling not in ("DC", "AC"):
            raise ValueError("trigger coupling must be DC or AC.")

        self.write(":TRIGger:MODE EDGE")
        self.write(":TRIGger:EDGE:SOURce CHANnel%d" % source_channel)
        self.write(":TRIGger:EDGE:SLOPe %s" % slope)
        self.write(":TRIGger:EDGE:LEVel %g" % level)
        self.write(":TRIGger:EDGE:COUPling %s" % coupling)
        self.write(":TRIGger:SWEep %s" % sweep)

    # ------------------------------------------------------------------
    # Acquisition setup
    # ------------------------------------------------------------------

    def set_acquire(self, acquire_type="NORMal", average_count=8):
        """
        acquire_type:
            NORMal, AVERage, HRESolution, or PEAK.

        For APD fluorescence traces:
            NORMal = raw single acquisition
            AVERage = useful when repeating same pulse sequence many times
        """
        acquire_type = acquire_type.upper()

        if acquire_type in ("NORM", "NORMAL"):
            acquire_type = "NORMal"
        elif acquire_type in ("AVG", "AVERAGE"):
            acquire_type = "AVERage"
        elif acquire_type in ("HRES", "HRESOLUTION"):
            acquire_type = "HRESolution"
        elif acquire_type == "PEAK":
            acquire_type = "PEAK"
        else:
            raise ValueError("Invalid acquire_type.")

        self.write(":ACQuire:TYPE %s" % acquire_type)

        if acquire_type == "AVERage":
            if average_count < 2:
                average_count = 2
            self.write(":ACQuire:COUNt %d" % int(average_count))
            self.write(":ACQuire:COMPlete 100")

    def set_waveform_readout(self, source_channel=1, points=1000, fmt="ASCii"):
        """
        Prepare waveform transfer.

        fmt="ASCii" is slower but simple and robust because it returns comma-separated floats.
        BYTE/WORD is faster but requires binary block parsing and scaling.
        """
        self._check_channel(source_channel)

        if points < self.points_min:
            points = self.points_min
        if points > self.points_max:
            points = self.points_max

        fmt = fmt.upper()
        if fmt in ("ASCII", "ASC"):
            fmt = "ASCii"
        elif fmt == "BYTE":
            fmt = "BYTE"
        elif fmt == "WORD":
            fmt = "WORD"
        else:
            raise ValueError("fmt must be ASCii, BYTE, or WORD.")

        self.write(":WAVeform:SOURce CHANnel%d" % source_channel)
        self.write(":WAVeform:FORMat %s" % fmt)
        self.write(":WAVeform:POINts %d" % int(points))

    # ------------------------------------------------------------------
    # QDS / PulseBlaster experiment helpers
    # ------------------------------------------------------------------

    def setup_qds_apd_triggered_acquisition(
        self,
        signal_channel=1,
        trigger_channel=2,
        time_range=20e-6,
        time_position=0.0,
        trigger_level=1.0,
        signal_scale=0.5,
        signal_offset=0.0,
        trigger_scale=1.0,
        trigger_offset=0.0,
        signal_impedance="FIFTy",
        trigger_impedance="FIFTy",
        points=1000,
        acquire_type="NORMal",
        average_count=8,
    ):
        """
        One-call setup for your experiment.

        CH1:
            APD analog fluorescence.
        CH2:
            PulseBlaster rising edge trigger.
        """
        self.write(":STOP")

        self.set_channel(
            signal_channel,
            scale=signal_scale,
            offset=signal_offset,
            coupling="DC",
            impedance=signal_impedance,
            probe=1.0,
            bw_limit=False,
            label="APD",
            display=True,
        )

        self.set_channel(
            trigger_channel,
            scale=trigger_scale,
            offset=trigger_offset,
            coupling="DC",
            impedance=trigger_impedance,
            probe=1.0,
            bw_limit=False,
            label="PB_TRIG",
            display=True,
        )

        # Hide unused channels, but do not fail if user later wants them.
        for ch in self.VALID_CHANNELS:
            if ch not in (signal_channel, trigger_channel):
                self.channel_on(ch, False)

        self.set_timebase(time_range=time_range, position=time_position)

        self.set_edge_trigger(
            source_channel=trigger_channel,
            level=trigger_level,
            slope="POSitive",
            sweep="NORMal",
            coupling="DC",
        )

        self.set_acquire(acquire_type=acquire_type, average_count=average_count)
        print("Scope acquire type =", self.ask(":ACQuire:TYPE?"))
        print("Scope average count =", self.ask(":ACQuire:COUNt?"))
        self.set_waveform_readout(source_channel=signal_channel, points=points, fmt="ASCii")

    def digitize(self, source_channel=1, wait=True):
        """
        Start single acquisition.

        With wait=True, uses :DIGitize ...;*OPC? so Python waits until scope is done.
        """
        self._check_channel(source_channel)

        if wait:
            return self.ask(":DIGitize CHANnel%d;*OPC?" % source_channel)
        else:
            self.write(":DIGitize CHANnel%d" % source_channel)
            return None

    def read_waveform_ascii(self, source_channel=1, points=1000, digitize_first=True):
        """
        Return time array and voltage array from one channel.

        This uses ASCii waveform format, so the voltage values are read directly
        as comma-separated floating values.
        """
        self.set_waveform_readout(source_channel=source_channel, points=points, fmt="ASCii")

        if digitize_first:
            self.digitize(source_channel=source_channel, wait=True)

        # Read preamble for time axis.
        pre = str(self.ask(":WAVeform:PREamble?")).strip()
        pre_vals = [float(x) for x in pre.split(",")]

        # Preamble:
        # format,type,points,count,xincrement,xorigin,xreference,yincrement,yorigin,yreference
        n_points = int(pre_vals[2])
        x_increment = pre_vals[4]
        x_origin = pre_vals[5]
        x_reference = pre_vals[6]

        raw = str(self.ask(":WAVeform:DATA?")).strip()

        payload = self._strip_ieee_block_header(raw)

        # Keysight ASCII waveform data may be comma-separated, space-separated,
        # or comma+space separated after the block header.
        payload = payload.replace("\n", " ").replace("\r", " ")
        payload = payload.replace(",", " ")

        y = np.fromstring(payload, sep=" ", dtype=float)

        if y.size == 0:
            raise RuntimeError(
                "No waveform points parsed from :WAVeform:DATA?. "
                "Raw response begins with: %r" % raw[:120]
            )

        # Use actual received length, not only preamble length.
        idx = np.arange(len(y), dtype=float)
        t = ((idx - x_reference) * x_increment) + x_origin

        if len(y) != n_points:
            print("WARNING: preamble points = %d, received points = %d" % (n_points, len(y)))

        return t, y

    def _strip_ieee_block_header(self, raw):
        """
        Strip SCPI definite-length block header.

        Example:
            #800013789 6.69456e-001,...
            #8 means the next 8 digits give payload byte count.
            00013789 means payload has 13789 bytes.
        """
        if raw is None:
            return ""

        raw = str(raw).strip()

        if not raw.startswith("#"):
            return raw

        if len(raw) < 2:
            return raw

        n_digits = int(raw[1])

        if n_digits == 0:
            # Indefinite block. Rare here; remove "#0" only.
            return raw[2:].strip()

        count_start = 2
        count_end = count_start + n_digits

        if len(raw) < count_end:
            raise RuntimeError("Bad IEEE block header: %r" % raw[:40])

        try:
            n_bytes = int(raw[count_start:count_end])
        except ValueError:
            raise RuntimeError("Cannot parse IEEE block length from: %r" % raw[:40])

        payload = raw[count_end:]

        # In your returned string, payload begins with a space:
        # "#800013789 6.69456e-001,..."
        payload = payload.lstrip()

        # Usually this is enough. Do not strictly require length match because
        # pyvisa/string decoding can alter newline handling.
        return payload

    def acquire_apd_trace(self, points=1000):
        """
        Convenience method for your default setup:
            trigger on CH2,
            read APD waveform from CH1.
        """
        return self.read_waveform_ascii(
            source_channel=self.default_signal_channel,
            points=points,
            digitize_first=True,
        )

    # ------------------------------------------------------------------
    # Simple automatic measurements, optional but useful for debugging
    # ------------------------------------------------------------------

    def measure_vpp(self, channel=1):
        self._check_channel(channel)
        return self.ask_float(":MEASure:VPP? CHANnel%d" % channel)

    def measure_vavg(self, channel=1):
        self._check_channel(channel)
        return self.ask_float(":MEASure:VAVerage? CHANnel%d" % channel)

    def measure_frequency(self, channel=2):
        self._check_channel(channel)
        return self.ask_float(":MEASure:FREQuency? CHANnel%d" % channel)

    def run(self):
        self.write(":RUN")

    def stop(self):
        self.write(":STOP")

    def single(self):
        self.write(":SINGle")


# class DSOX6004AWidget(instr_widget.Instr_Widget):
#     def __init__(self, instr=None, parent=None):
#         super().__init__(instr, parent)


if __name__ == "__main__":
    # Example only. Change address to your real GPIB/VISA device name.
    scope = DSOX6004A("DSOX6004A")

    print(scope.idn())

    scope.setup_qds_apd_triggered_acquisition(
        signal_channel=1,
        trigger_channel=2,
        time_range=20e-6,
        trigger_level=1.0,
        signal_scale=0.5,
        signal_offset=0.0,
        trigger_scale=1.0,
        trigger_offset=0.0,
        points=1000,
        acquire_type="NORMal",
    )

    t, apd = scope.acquire_apd_trace(points=1000)
    print(t[:5])
    print(apd[:5])