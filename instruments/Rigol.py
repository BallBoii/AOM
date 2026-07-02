import numpy as np

if __name__ == '__main__':
    import GPIBdev # use when running this as a main
    import instr_widget
    import GPIBdev_gui
else:
    from instruments import GPIBdev
    from instruments import GPIBdev_gui
    from instruments import instr_widget


class DSG836A(GPIBdev.GPIBdev):
    def __init__(self, dev):
        super().__init__(dev)

        self.pow_min = -110
        self.pow_max = 20
        self.freq_min = 9e3
        self.freq_max = 3.6e9

        self.set_mod(0)
        self.set_iqmod(0)
        self.set_output(0)

    def set_freq(self, freq):
        # set generator frequency in Hz
        if (freq < self.freq_min) or (freq > self.freq_max):
            print('Freq Range Error! Tried to set to %d' % freq)
        else:
            self.gpib_write(':FREQ %.6fHz' % freq)

    def get_freq(self):
        return float(self.gpib_query(':FREQ?'))

    def set_pow(self, pow):
        # set generator power in dBm
        if (pow < self.pow_min) or (pow > self.pow_max):
            print('Power Range Error! Tried to set to %f' % pow)
        else:
            self.gpib_write(':LEV %f' % pow)

    def get_pow(self):
        return float(self.gpib_query(':LEV?'))

    def set_mod(self, b):
        self.gpib_write(':MOD:STAT %d' % b)

    def get_mod(self):
        return int(self.gpib_query(':MOD:STAT?'))

    def set_output(self, b):
        self.gpib_write(':OUTP %d' % b)

    def get_output(self):
        return int(self.gpib_query(':OUTP?'))

    def set_alc(self, b):
        self.gpib_write(':CORR:FLAT %d' % b)

    def set_pulsemod(self, b):
        self.gpib_write(':PULM:STAT %d' % b)

    def set_pulsemod_src(self, src):
        self.gpib_write(':PULM:SOUR %s' % src)

    def set_iqmod(self, b):
        self.gpib_write(':IQ:MOD:STAT %d' % b)
        if b:
            self.gpib_write(':IQ:MOD EXT')
        self.set_mod(b)

    def get_iqmod(self):
        return int(self.gpib_query(':IQ:MOD:STAT?'))

class DG2102(GPIBdev.GPIBdev):
    'Function/Arbitrary Waveform Generator'

    def __init__(self, dev, timeout=10000, vmin=-0.354, vmax=+0.354):
        super().__init__(dev)
        self.inst.timeout = timeout
        self.alias = ''  # alias is pb channel name

        # limits of the device
        self.vmin = vmin
        self.vmax = vmax

    def set_func(self, ch, fun):
        self.gpib_write('SOUR%d:FUNC %s' % (ch, fun))  #set the waveform

    def set_alias(self, pb_chan):
        self.alias = pb_chan

    def set_freq(self, ch, freq):
        self.gpib_write('SOUR%d:FREQ %.3f' % (ch, freq))

    def set_amplitude(self, ch, amp):
        self.set_limits()
        self.gpib_write('SOUR%d:VOLT %.3f' % (ch, amp))

    def set_dc(self, ch, v):
        self.gpib_write('SOUR%d:VOLT:OFFS %.3f' % (ch, v)) #set offset voltage

    def set_duty_cycle(self, ch, duty):
        # set square wave duty cycle in percent (0-100)
        if (duty < 0) or (duty > 100):
            print('Duty Cycle Range Error! Tried to set to %f' % duty)
        else:
            self.gpib_write('SOUR%d:FUNC:SQU:DCYC %.3f' % (ch, duty))

    def get_duty_cycle(self, ch):
        return float(self.gpib_query('SOUR%d:FUNC:SQU:DCYC?' % ch))

    def set_amplitude_wfm(self, ch, low, high): #set limit ofthe waveform
        # self.set_limits()
        if low == 0 and high == 0:
            self.gpib_write('SOUR%d:VOLT:LOW MIN' % (ch))
            self.gpib_write('SOUR%d:VOLT:HIGH MAX' % (ch))
        else:
            self.gpib_write('SOUR%d:VOLT:LOW %.3f' % (ch, low))
            self.gpib_write('SOUR%d:VOLT:HIGH %.3f' % (ch, high))

    def set_output(self, b):
        self.gpib_write('OUTP1 %d' % b) #ON or OFF
        self.gpib_write('OUTP2 %d' % b)
    
    def set_output_ch(self, ch, b):
        self.gpib_write('OUTP%d %d' % (ch, b)) #ON or OFF

    def set_gated(self, ch, b):
        self.gpib_write('SOUR%d:BURS:STAT %d' % (ch, b)) #ON or OFF (Burst mode = pulse modulation)
        if bool(b):
            self.gpib_write('SOUR%d:BURS:MODE GAT' % ch)  #Gated burst mode: control waveform output according to the level of external signal input
            self.gpib_write('SOUR%d:BURS:SOUR EXT' % ch)

    def set_triggered(self, ch, b):
        self.gpib_write('SOUR%d:BURS:STAT %d' % (ch, b))
        if bool(b):
            self.gpib_write('SOUR%d:BURS:MODE TRIG' % ch) #Triggered (N cycle) burst mode: no. cycles output waveforms after receiving trigger signal
            self.gpib_write('SOUR%d:BURS:NCYC 1' % ch) #1 cycle
            self.gpib_write('TRIG%d:SOUR EXT' % ch)

    def set_wfm(self, ch, wfm, sampl=250e6):
        self.set_func(ch, 'ARB')
        self.gpib_write('SOUR%d:FUNC:ARB:SRAT %d' % (ch, sampl)) #sample rate: number of points per second
        self.gpib_write('SOUR%d:FUNC:ARB:FILT OFF' % ch) #steps from point to point at the sample rate todo
        self.set_triggered(ch, 1)

        self.gpib_write('SOUR%d:DATA:VOL:CLE' % ch) #clears volatile waveform memory todo

        wfm_array = np.array(wfm)

        header = 'SOUR%d:DATA:ARB wfm%d, ' % (ch, ch) #todo

        self.gpib_write('FORMat:BORDer SWAP') #Sets the byte order used in binary data point transfers in the block mode todo

        # this function takes care of the binary block header by itself
        self.inst.write_binary_values(header, wfm_array)

        self.gpib_write('SOUR%d:FUNC:ARB wfm%d' % (ch, ch)) #todo

    def set_wfm_dual(self, wfm1, wfm2, sampl=250e6):
        # wfm is a list of float, normalized to 1
        self.set_wfm(1, wfm1, sampl)
        self.set_wfm(2, wfm2, sampl)

    def set_limits(self):
        #self.gpib_write('SOUR1:VOLT:LIM:STAT 1')    #todo
        #self.gpib_write('SOUR1:VOLT:LIM:LOW %f' % self.vmin)
        #self.gpib_write('SOUR1:VOLT:LIM:HIGH %f' % self.vmax)
        #self.gpib_write('SOUR2:VOLT:LIM:STAT 1')
        #self.gpib_write('SOUR2:VOLT:LIM:LOW %f' % self.vmin)
        #self.gpib_write('SOUR2:VOLT:LIM:HIGH %f' % self.vmax)
        self.gpib_write('OUTP1:VOLLimit:STAT 1')    #todo
        self.gpib_write('OUTP1:VOLLimit:LOW %f' % self.vmin)
        self.gpib_write('OUTP1:VOLLimit:HIGH %f' % self.vmax)
        self.gpib_write('OUTP2:VOLLimit:STAT 1')
        self.gpib_write('OUTP2:VOLLimit:LOW %f' % self.vmin)
        self.gpib_write('OUTP2:VOLLimit:HIGH %f' % self.vmax)

    def set_sequence(self, wfm_list, reps_list, name): #todo
        # writes a sequence and set a proper command
        seq_cmd = '"%s"' % name

        if len(wfm_list) != len(reps_list):
            print('error')  # todo
        else:
            self.gpib_write('DATA:VOLatile:CLE')

            for seq in range(len(wfm_list)):
                # <arb name>,<repeat count>,<play control>,<marker mode>,<marker point>
                wfm = wfm_list[seq]
                rep_count = reps_list[seq]
                play_control = 'repeat'
                # this shouldn't matter
                marker_mode = 'maintain'
                marker_point = 10

                # load waveform into memory
                self.gpib_write('MMEM:LOAD:DATA "%s"' % wfm)
                seq_cmd += ',"%s",%d,%s,%s,%d' % (wfm, rep_count, play_control, marker_mode, marker_point)

            char_count = len(seq_cmd)
            n_digits = len(str(char_count))

            self.gpib_write('DATA:SEQ #%d%d%s' % (n_digits, char_count, seq_cmd)) #combines previously loaded arbitrary waveforms into a sequence

    def get_error(self):
        err = self.gpib_query('SYST:ERR?') #Queries and clears an error message from the error queue

        if '+0' in err:
            return ''
        else:
            error_all = ''
            max_err = 20  # maximum number of errors to read - prevent infinite loop
            itr = 0
            while '+0' not in err and itr < max_err:
                error_all += err
                err = self.gpib_query('SYST:ERR?')
                itr += 1
            if itr >= max_err:
                print('More than %d error messages occurred. You are probably doing something stupid...' % max_err)
            return error_all

    def set_view(self, mode):
        # mode: STANdard|TEXT|GRAPh|DUAL
        self.gpib_write('DISP:VIEW %s' % mode) #todo

class DSG836(GPIBdev.GPIBdev):
    def __init__(self, dev):
        super().__init__(dev)

        self.pow_min = -110
        self.pow_max = 20
        self.freq_min = 9e3
        self.freq_max = 3.6e9

        self.set_mod(0)
        self.set_iqmod(0)
        self.set_output(0)

    def set_freq(self, freq):
        # set generator frequency in Hz
        if (freq < self.freq_min) or (freq > self.freq_max):
            print('Freq Range Error! Tried to set to %d' % freq)
        else:
            self.gpib_write(':FREQ %.6fHz' % freq)

    def get_freq(self):
        return float(self.gpib_query(':FREQ?'))

    def set_pow(self, pow):
        # set generator power in dBm
        if (pow < self.pow_min) or (pow > self.pow_max):
            print('Power Range Error! Tried to set to %f' % pow)
        else:
            self.gpib_write(':LEV %f' % pow)

    def get_pow(self):
        return float(self.gpib_query(':LEV?'))

    def set_mod(self, b):
        self.gpib_write(':MOD:STAT %d' % b)

    def get_mod(self):
        return int(self.gpib_query(':MOD:STAT?'))

    def set_output(self, b):
        self.gpib_write(':OUTP %d' % b)

    def get_output(self):
        return int(self.gpib_query(':OUTP?'))

    def set_alc(self, b):
        self.gpib_write(':CORR:FLAT %d' % b)

    def set_pulsemod(self, b):
        self.gpib_write(':PULM:STAT %d' % b)

    def set_pulsemod_src(self, src):
        self.gpib_write(':PULM:SOUR %s' % src)

    def set_iqmod(self, b):
        self.gpib_write(':IQ:MOD:STAT %d' % b)
        self.set_mod(b)

    def get_iqmod(self):
        return int(self.gpib_query(':IQ:MOD:STAT?'))

    # ── System / utility ────────────────────────────────────────────────
    def idn(self):
        return self.gpib_query('*IDN?').strip()

    def reset(self):
        self.gpib_write('*RST')

    def clear_status(self):
        self.gpib_write('*CLS')

    def get_error(self):
        # Reads and clears the error queue, returning all pending messages.
        err = self.gpib_query(':SYST:ERR?')

        if '+0' in err or '0,' in err.split(',')[0]:
            return ''
        else:
            error_all = ''
            max_err = 20  # maximum number of errors to read - prevent infinite loop
            itr = 0
            while '+0' not in err and itr < max_err:
                error_all += err
                err = self.gpib_query(':SYST:ERR?')
                itr += 1
            if itr >= max_err:
                print('More than %d error messages occurred. You are probably doing something stupid...' % max_err)
            return error_all

    # ── Frequency / level offsets ───────────────────────────────────────
    def set_freq_offset(self, offs):
        # frequency offset in Hz (display-only shift)
        self.gpib_write(':FREQ:OFFS %.6fHz' % offs)

    def get_freq_offset(self):
        return float(self.gpib_query(':FREQ:OFFS?'))

    def set_pow_offset(self, offs):
        # level offset in dB (display-only shift)
        self.gpib_write(':LEV:OFFS %f' % offs)

    def get_pow_offset(self):
        return float(self.gpib_query(':LEV:OFFS?'))

    # ── Amplitude modulation (AM) ───────────────────────────────────────
    def set_am(self, b):
        self.gpib_write(':AM:STAT %d' % b)

    def get_am(self):
        return int(self.gpib_query(':AM:STAT?'))

    def set_am_depth(self, depth):
        # modulation depth in percent (0-100)
        self.gpib_write(':AM:DEPT %f' % depth)

    def get_am_depth(self):
        return float(self.gpib_query(':AM:DEPT?'))

    def set_am_source(self, src):
        # src: INT | EXT | INT,EXT
        self.gpib_write(':AM:SOUR %s' % src)

    def set_am_int_freq(self, freq):
        # internal modulating frequency in Hz
        self.gpib_write(':AM:INT:FREQ %.6fHz' % freq)

    def get_am_int_freq(self):
        return float(self.gpib_query(':AM:INT:FREQ?'))

    def set_am_waveform(self, wfm):
        # wfm: SINE | SQUare | TRIangle | RAMP
        self.gpib_write(':AM:INT:FUNC %s' % wfm)

    # ── Frequency modulation (FM) ───────────────────────────────────────
    def set_fm(self, b):
        self.gpib_write(':FM:STAT %d' % b)

    def get_fm(self):
        return int(self.gpib_query(':FM:STAT?'))

    def set_fm_dev(self, dev):
        # frequency deviation in Hz
        self.gpib_write(':FM:DEV %.6fHz' % dev)

    def get_fm_dev(self):
        return float(self.gpib_query(':FM:DEV?'))

    def set_fm_source(self, src):
        self.gpib_write(':FM:SOUR %s' % src)

    def set_fm_int_freq(self, freq):
        self.gpib_write(':FM:INT:FREQ %.6fHz' % freq)

    def get_fm_int_freq(self):
        return float(self.gpib_query(':FM:INT:FREQ?'))

    def set_fm_waveform(self, wfm):
        self.gpib_write(':FM:INT:FUNC %s' % wfm)

    # ── Phase modulation (PM) ───────────────────────────────────────────
    def set_pm(self, b):
        self.gpib_write(':PM:STAT %d' % b)

    def get_pm(self):
        return int(self.gpib_query(':PM:STAT?'))

    def set_pm_dev(self, dev):
        # phase deviation in radians
        self.gpib_write(':PM:DEV %f' % dev)

    def get_pm_dev(self):
        return float(self.gpib_query(':PM:DEV?'))

    def set_pm_source(self, src):
        self.gpib_write(':PM:SOUR %s' % src)

    def set_pm_int_freq(self, freq):
        self.gpib_write(':PM:INT:FREQ %.6fHz' % freq)

    def get_pm_int_freq(self):
        return float(self.gpib_query(':PM:INT:FREQ?'))

    # ── Pulse modulation (extended) ─────────────────────────────────────
    def get_pulsemod(self):
        return int(self.gpib_query(':PULM:STAT?'))

    def set_pulsemod_mode(self, mode):
        # mode: SINGle | DOUBle
        self.gpib_write(':PULM:MODE %s' % mode)

    def set_pulse_period(self, period):
        # pulse period in seconds
        self.gpib_write(':PULM:PERiod %.9f' % period)

    def get_pulse_period(self):
        return float(self.gpib_query(':PULM:PERiod?'))

    def set_pulse_width(self, width):
        # pulse width in seconds
        self.gpib_write(':PULM:WIDTh %.9f' % width)

    def get_pulse_width(self):
        return float(self.gpib_query(':PULM:WIDTh?'))

    def set_pulse_polarity(self, pol):
        # pol: NORMal | INVerted
        self.gpib_write(':PULM:POL %s' % pol)

    # ── Frequency / level sweep ─────────────────────────────────────────
    def set_sweep(self, b):
        # b: 0 = OFF, 1 = sweep enabled (use set_sweep_type to select)
        self.gpib_write(':SWE:STAT %d' % b)

    def get_sweep(self):
        return self.gpib_query(':SWE:STAT?').strip()

    def set_sweep_type(self, typ):
        # typ: FREQuency | LEVel | LEVFRE (level & frequency)
        self.gpib_write(':SWE:TYPE %s' % typ)

    def set_sweep_mode(self, mode):
        # mode: SINGle | CONTinuous
        self.gpib_write(':SWE:MODE %s' % mode)

    def set_sweep_spacing(self, spacing):
        # spacing: LINear | LOGarithmic
        self.gpib_write(':SWE:SPAC %s' % spacing)

    def set_sweep_points(self, points):
        self.gpib_write(':SWE:STEP:POIN %d' % points)

    def set_sweep_dwell(self, dwell):
        # dwell time per step in seconds
        self.gpib_write(':SWE:STEP:DWEL %.6f' % dwell)

    def set_sweep_start_freq(self, freq):
        self.gpib_write(':SWE:STEP:STAR:FREQ %.6fHz' % freq)

    def set_sweep_stop_freq(self, freq):
        self.gpib_write(':SWE:STEP:STOP:FREQ %.6fHz' % freq)

    def sweep_execute(self):
        # trigger a single sweep
        self.gpib_write(':SWE:EXEC')

    # ── Low-frequency (LF) output ───────────────────────────────────────
    def set_lf(self, b):
        self.gpib_write(':LFO:STAT %d' % b)

    def get_lf(self):
        return int(self.gpib_query(':LFO:STAT?'))

    def set_lf_freq(self, freq):
        self.gpib_write(':LFO:FREQ %.6fHz' % freq)

    def get_lf_freq(self):
        return float(self.gpib_query(':LFO:FREQ?'))

    def set_lf_level(self, level):
        # LF output level in volts
        self.gpib_write(':LFO:LEV %f' % level)

    def get_lf_level(self):
        return float(self.gpib_query(':LFO:LEV?'))

    def set_lf_waveform(self, wfm):
        # wfm: SINE | SQUare | TRIangle | RAMP
        self.gpib_write(':LFO:SHAP %s' % wfm)

    # ── Reference oscillator / clock ────────────────────────────────────
    def set_ref_source(self, src):
        # src: INTernal | EXTernal
        self.gpib_write(':ROSC:SOUR %s' % src)

    def get_ref_source(self):
        return self.gpib_query(':ROSC:SOUR?').strip()

    def set_ref_ext_freq(self, freq):
        # expected external reference frequency in Hz
        self.gpib_write(':ROSC:EXT:FREQ %.6fHz' % freq)

    def get_ref_ext_freq(self):
        return float(self.gpib_query(':ROSC:EXT:FREQ?'))
