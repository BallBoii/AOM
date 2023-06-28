import numpy as np
import basic_functions as lt
import scipy.io
import pandas as pd
import matplotlib.pyplot as plt

start = 801
stop = 1200
example = 2

# Load fl decay
file = scipy.io.loadmat(r'C:\Users\natak\Documents\Github\yok3leg_playground\Fluorescein_TCSPC_example.mat')
var = list(file['TCSPC'])
TCSPC = pd.DataFrame(np.array(var))
sum_TCSPC = list(np.sum(TCSPC))
peak_y = max(sum_TCSPC)
peak_x = sum_TCSPC.index(peak_y)
print('Decay Peak position', peak_x)
TCSPC = np.array(TCSPC)
#plt.plot(np.sum(TCSPC[:,start:stop], axis = 0)/np.max(np.sum(TCSPC[:,start:stop], axis = 0)))

# for testing functions
if example == 1: # CMM one TCSPC row
    [tau, intensity] = lt.calcmm1row(TCSPC[1,:],801,1200,400,0.01,0,0)
    print(tau)

elif example == 2: # CMM matrix
    [tau, intensity] = lt.calcmmmartix(TCSPC,801,1200,400,0.01,0,0)
    print(tau)
