import numpy as np
import pandas as pd
import scipy.signal as ss

def calcmm1row(TCSPC_row, start, stop, T, h, threshold, bg):

    # no IRF calibration (suitable for tail fit)

    # input
    # TCSPC_row 1 row
    # T = measurement window
    # start = start bin of T
    # stop = stop bin of T
    # h = bin width
    # threshold = intensity threshold (below -> tau = 0)
    # bg = background subtraction value

    # loading LUT
    LUT = pd.read_csv(r'LUT.csv')
    LUT_CM = np.array(pd.DataFrame(LUT, columns=['CM']))
    LUT_tau = np.array(pd.DataFrame(LUT, columns=['tau']))

    # define variables
    tau = [] # for storage
    t = list(range(0,stop-start))
    t[:] = [x+0.5 for x in t]
    LUT_CM = list(LUT_CM)

    # CMM
    hist = TCSPC_row[start:stop]
    hist = ss.savgol_filter(hist,5,3) - bg # noise reduction
    intensity = np.sum(hist)
    if intensity < threshold:
        tau = 0
    else:
        CM = np.sum(np.transpose(hist)*np.transpose(t))/np.sum(hist) # CM point
        CM2 = CM/T # CM compart to measurement window
        if CM2 < 0.03 or CM2 > 0.498: # follow the LUT
            tau = 0
        else:
            CM2 = round(CM2, 2)
            tau = LUT_tau[LUT_CM.index(CM2)]*T*h # retrive vlue from the sample position in LUT 2nd col
    return tau, intensity

def calcmmmartix(TCSPC, start, stop, T, h, threshold, bg):

    # no IRF calibration (suitable for tail fit)

    # input
    # TCSPC (row = pixel, col = time bin)
    # T = measurement window
    # start = start bin of T
    # stop = stop bin of T
    # h = bin width
    # threshold = intensity threshold (below -> tau = 0)
    # bg = background subtraction value

    # loading LUT
    LUT = pd.read_csv(r'LUT.csv')
    LUT_CM = np.array(pd.DataFrame(LUT, columns=['CM']))
    LUT_tau = np.array(pd.DataFrame(LUT, columns=['tau']))

    # define variables
    tau = [] # for storage
    t = list(range(0,stop-start))
    t[:] = [x+0.5 for x in t]
    LUT_CM = list(LUT_CM)
    intensity_img = []
    tau_img = []
    pixel = len(TCSPC)

    # CMM
    print(str(pixel)+' pixels to be calculated')
    for i in range(0, pixel):  # main loop
        hist = TCSPC[i,start:stop]
        hist = ss.savgol_filter(hist,5,3) - bg # noise reduction
        intensity = np.sum(hist)
        if intensity < threshold:
            tau = 0
        else:
            CM = np.sum(np.transpose(hist)*np.transpose(t))/np.sum(hist) # CM point
            CM2 = CM/T # CM compart to measurement window
            if CM2 < 0.03 or CM2 > 0.498: # follow the LUT
                tau = 0
            else:
                CM2 = round(CM2, 2)
                tau = LUT_tau[LUT_CM.index(CM2)]*T*h # retrive vlue from the sample position in LUT 2nd col
        intensity_img.append(intensity)
        tau_img.append(tau)

        if i%1000 == 0:
            print(i) # show the calculation progress
    return tau_img, intensity_img
