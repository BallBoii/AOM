def pb_nuclear_rabi_params(self):
    self.params = self.default_params()
    self.params.update(
        {'weak_pi': 56e-9, 'pi_l': 500e-9, 'time_green': 500e-9, 'tau': 100e-9, 'n': 1})

def pb_nuclear_rabi(self):
    for i in range(np.uint32(self.params['n'])):
        self.add_inst(['mw1'], self.inst_set.CONTINUE, 0, self.params['weak_pi'])
        self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['pi_l'])
        self.add_inst(['green'], self.inst_set.CONTINUE, 0, self.params['time_green'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['tau'])
    self.add_inst(['mw1'], self.inst_set.CONTINUE, 0, self.params['weak_pi'])

def pb_nuclear_ramsey_params(self):
    self.params = self.default_params()
    self.params.update(
        {'weak_pi': 56e-9, 'pi_l': 200e-9, 'strong_pi': 56e-9, 'time_green': 500e-9, 'tau': 100e-9, 'n': 1})

def pb_nuclear_ramsey(self):
    for i in range(np.uint32(self.params['n'])):
        self.add_inst(['mw1'], self.inst_set.CONTINUE, 0, self.params['weak_pi'])
        self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['pi_l'])
        self.add_inst(['green'], self.inst_set.CONTINUE, 0, self.params['time_green'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['pi_l']/2)
    self.add_inst(['mw2'], self.inst_set.CONTINUE, 0, self.params['strong_pi'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['tau'])
    self.add_inst(['mw2'], self.inst_set.CONTINUE, 0, self.params['strong_pi'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['pi_l'] / 2)
    self.add_inst(['mw1'], self.inst_set.CONTINUE, 0, self.params['weak_pi'])

def pb_nuclear_echo_params(self):
    self.params = self.default_params()
    self.params.update(
        {'weak_pi': 56e-9, 'pi_l': 200e-9, 'strong_pi': 500e-9, 'time_green': 500e-9, 'tau': 100e-9, 'n': 1, 'time_wait': 56e-9})

def pb_nuclear_echo(self):
    for i in range(np.uint32(self.params['n'])):
        self.add_inst(['mw1'], self.inst_set.CONTINUE, 0, self.params['weak_pi'])
        self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['pi_l'])
        self.add_inst(['green'], self.inst_set.CONTINUE, 0, self.params['time_green'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['tau'])
    self.add_inst(['mw2'], self.inst_set.CONTINUE, 0, self.params['strong_pi'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['time_wait'])
    self.add_inst(['mw2'], self.inst_set.CONTINUE, 0, self.params['strong_pi'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['tau'])
    self.add_inst(['mw1'], self.inst_set.CONTINUE, 0, self.params['weak_pi'])

def pb_notramsey_params(self):
    self.params = self.default_params()
    self.params.update(
        {'pulsewidth_pi2': 28e-9, 'pulsewidth_pi32': 84e-9, 'tau': 100e-9, 'inv': 1})

def pb_notramsey(self):
    self.add_inst(['mw2'], self.inst_set.CONTINUE, 0, self.params['pulsewidth_pi2'])
    self.add_inst([''], self.inst_set.CONTINUE, 0, self.params['tau'])
    self.add_inst(['mw1'], self.inst_set.CONTINUE, 0, self.params['pulsewidth_pi32'])

