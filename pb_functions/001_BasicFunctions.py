def pb_odmr_params(self):
    self.params = self.default_params()
    self.params.update({'pulsewidth': 100e-6, 'tau': 100e-6})
    self.custom_readout = True


def pb_odmr(self):
    loop_start = self.add_inst(['green', 'ctr1'], self.inst_set.LOOP, self.params['reps'], self.params['tau'])
    self.add_inst(['green', 'mw1', 'ctr0'], self.inst_set.END_LOOP, loop_start, self.params['pulsewidth'])
    self.add_inst(['green'], self.inst_set.STOP, 0, 1e-6)


def pb_odmr2_params(self):
    self.params = self.default_params()
    self.params.update({'pulsewidth': 100e-6, 'tau': 100e-6})
    self.custom_readout = True


def pb_odmr2(self):
    loop_start = self.add_inst(['green', 'ctr1'], self.inst_set.LOOP, self.params['reps'], self.params['tau'])
    self.add_inst(['green', 'mw2', 'ctr0'], self.inst_set.END_LOOP, loop_start, self.params['pulsewidth'])
    self.add_inst(['green'], self.inst_set.STOP, 0, 1e-6)


def pb_rabi_params(self):
    self.params = self.default_params()
    self.params.update({'pulsewidth': 20e-9, 'reps': 1e5, 'tau': 0.0})


def pb_rabi(self):
    self.add_inst(['mw1'], self.inst_set.CONTINUE, 0, self.params['pulsewidth'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['tau'])


def pb_rabi2_params(self):
    self.params = self.default_params()
    self.params.update({'pulsewidth': 20e-9, 'reps': 1e5, 'tau': 0.0})


def pb_rabi2(self):
    self.add_inst(['mw2'], self.inst_set.CONTINUE, 0, self.params['pulsewidth'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['tau'])