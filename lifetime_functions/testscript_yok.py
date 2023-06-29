import numpy as np
import basic_functions as lt
import scipy.io
import pandas as pd
import matplotlib.pyplot as plt
from instruments import QuTAG_MC
import time

start = 801
stop = 1200
example = 3

# for testing functions
if example == 1: # CMM one TCSPC row
    # Load fl decay
    file = scipy.io.loadmat(r'C:\Users\natak\Documents\Github\yok3leg_playground\Fluorescein_TCSPC_example.mat')
    var = list(file['TCSPC'])
    TCSPC = pd.DataFrame(np.array(var))
    sum_TCSPC = list(np.sum(TCSPC))
    peak_y = max(sum_TCSPC)
    peak_x = sum_TCSPC.index(peak_y)
    print('Decay Peak position', peak_x)
    TCSPC = np.array(TCSPC)
    # plt.plot(np.sum(TCSPC[:,start:stop], axis = 0)/np.max(np.sum(TCSPC[:,start:stop], axis = 0)))

    # CMM
    [tau, intensity] = lt.calcmm1row(TCSPC[1,:],801,1200,400,0.01,0,0)
    print(tau)

elif example == 2: # CMM matrix
    # Load fl decay
    file = scipy.io.loadmat(r'C:\Users\natak\Documents\Github\yok3leg_playground\Fluorescein_TCSPC_example.mat')
    var = list(file['TCSPC'])
    TCSPC = pd.DataFrame(np.array(var))
    sum_TCSPC = list(np.sum(TCSPC))
    peak_y = max(sum_TCSPC)
    peak_x = sum_TCSPC.index(peak_y)
    print('Decay Peak position', peak_x)
    TCSPC = np.array(TCSPC)
    # plt.plot(np.sum(TCSPC[:,start:stop], axis = 0)/np.max(np.sum(TCSPC[:,start:stop], axis = 0)))

    # CMM
    [tau, intensity] = lt.calcmmmartix(TCSPC,801,1200,400,0.01,0,0)
    print(tau)

elif example == 3:
    qutag = QuTAG_MC.QuTAG() # initialization
    ch_start = 0
    ch_stop = 1
    qutag.addHistogram(ch_start, ch_stop, True)
    qutag.setHistogramParams(25, 4000)
    time.sleep(1)
    rc = qutag.getHistogram(ch_start, ch_stop, True)
    print("Counts inside the histogram: ", rc[1], "| Counts too Small: ", rc[2], "| Counts too Large: ", rc[3],
          "| starts: ", rc[4], "| stops: ", rc[5], "| max exposure time: ", rc[6] / 1000, "ns")
    # Plotting with mathplotlib
    fig = plt.figure()
    fig.set_size_inches(10, 7)
    ax1 = fig.add_subplot(1, 1, 1)
    plt.cla()  # clear old plotting data
    # plot the datapoints
    plt.plot(rc[0])
    ax1.set_title('quTAG Histogram')
    plt.pause(10)
    # Disconnects a connected device and stops the internal event loop.
    qutag.deInitialize()
