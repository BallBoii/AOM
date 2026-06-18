# -*- coding: utf-8 -*-
"""
exp_aom_1.py

AOM performance sweep.

A Rigol DG2102 applies a square wave to the AOM RF driver. The laser passing
through the AOM is detected by a photodiode on oscilloscope CH1. We sweep the
square-wave amplitude (Vpp) over a list of setpoints, measure the photodiode
response (CH1 Vpp) at each, then plot and fit a sigmoid of laser response vs.
drive Vpp -- the classic AOM diffraction-efficiency curve.

Cabling assumption:
    Rigol CH1  -> AOM RF driver control input.
    Photodiode -> scope CH1 (laser signal).
    The laser square is locked to the drive, so the scope self-triggers on CH1
    (sweep=AUTO) -- only two cables, no trigger copy needed.

Usage:
    python exp_aom_1.py
    python exp_aom_1.py --dg-ip 10.0.0.5 --scope-ip 10.0.0.6 --vpp 2,4,6,8
    python exp_aom_1.py --no-show --out aom_run3.png
"""

import os
import sys
import time
import argparse
import warnings

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Make sure the repo root is on the path so `from instruments import ...` works
# regardless of the directory the script is launched from.
REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from instruments.Rigol import DG2102
from instruments.Oscilloscope import DSOX6004A


# ── Defaults (override on the command line, see main()) ──────────────────────
DEFAULT_DG2102_IP = "192.168.68.33"   # Rigol DG2102 LAN IP
DEFAULT_SCOPE_IP = "192.168.68.52"    # Keysight DSO-X 6004A LAN IP

DEFAULT_VPP_LIST = [3, 6, 9, 10]      # drive square-wave Vpp setpoints (V)
DEFAULT_SQUARE_FREQ = 1e3             # square-wave frequency (Hz)
DEFAULT_SCOPE_TIMEOUT = 30000         # scope VISA timeout (ms)
DEFAULT_SETTLE_S = 0.3                # settle time after each amplitude change (s)
DEFAULT_OUT = "aom_sigmoid.png"

DEFAULT_SIGNAL_IMP = "FIFTy"          # CH1 (photodiode) input impedance
DEFAULT_SIGNAL_SCALE = 0.5            # CH1 V/div (override with --signal-scale)

DRIVE_CH = 1                          # Rigol output channel driving the AOM
SIGNAL_CHANNEL = 1                    # scope channel = photodiode (laser)
# The photodiode square is locked to the drive, so CH1 triggers itself --
# no separate trigger channel/cable is needed.
# ────────────────────────────────────────────────────────────────────────────


def connect(dg_visa, scope_visa, scope_timeout):
    """Open both instruments and verify the connection actually succeeded.

    GPIBdev only emits a warning (not an exception) when a device is missing,
    so we check `.connected` explicitly and abort with a clear message.
    """
    print("DG2102 resource :", dg_visa)
    print("Scope  resource :", scope_visa)

    awg = DG2102(dg_visa)
    scope = DSOX6004A(scope_visa, timeout_ms=scope_timeout)

    print("DG2102 connected:", awg.connected)
    print("Scope  connected:", scope.connected)

    if not awg.connected:
        raise SystemExit("ERROR: could not connect to DG2102 at %s." % dg_visa)
    if not scope.connected:
        raise SystemExit("ERROR: could not connect to scope at %s." % scope_visa)

    print("Scope IDN:", scope.idn())
    return awg, scope


def configure(awg, scope, freq, first_vpp,
              signal_imp=DEFAULT_SIGNAL_IMP, signal_scale=DEFAULT_SIGNAL_SCALE):
    """Set up the Rigol square-wave drive and the CH1 self-triggered acquisition."""
    # Rigol: square wave on the drive channel. Amplitude is set per-point in
    # sweep(); here we just establish the waveform shape, frequency and output.
    awg.set_func(DRIVE_CH, "SQU")
    awg.set_freq(DRIVE_CH, freq)
    awg.set_amplitude_wfm(DRIVE_CH, 0.0, float(first_vpp))  # start at first setpoint
    awg.set_output(1)
    err = awg.get_error()
    if err:
        print("Rigol errors after setup:", err)

    # Scope: CH1 = photodiode (laser). The laser square is locked to the drive,
    # so we trigger CH1 on itself -- no second cable needed.
    scope.stop()
    scope.set_channel(
        SIGNAL_CHANNEL,
        scale=signal_scale,         # V/div for the photodiode
        offset=0.0,
        coupling="DC",
        impedance=signal_imp,
        probe=1.0,
        bw_limit=False,
        label="LASER",
        display=True,
    )
    # Hide the other channels.
    for ch in scope.VALID_CHANNELS:
        if ch != SIGNAL_CHANNEL:
            scope.channel_on(ch, False)

    # ~2.5 periods on screen so Vpp measures cleanly.
    scope.set_timebase(time_range=2.5 / freq, position=0.0)

    # Self-trigger on CH1. sweep="AUTO" still acquires when the step is tiny
    # (bottom of the sigmoid), so measure_vpp always returns a value.
    scope.set_edge_trigger(
        source_channel=SIGNAL_CHANNEL,
        level=0.0,
        slope="POSitive",
        sweep="AUTO",
        coupling="DC",
    )
    scope.set_acquire(acquire_type="AVERage", average_count=8)
    scope.run()
    print("Scope configured. Time range:", scope.ask(":TIMebase:RANGe?"))


def sweep(awg, scope, vpp_list, settle_s):
    """Drive each Vpp setpoint and record the photodiode response (CH1 Vpp)."""
    vpp_arr = []
    resp_arr = []

    print("\nStarting sweep over %d setpoints..." % len(vpp_list))
    for vpp in vpp_list:
        # Unipolar square: 0 -> vpp (bypasses the +/-0.354 V limit that
        # set_amplitude() would enable, letting us reach 3-10 V).
        awg.set_amplitude_wfm(DRIVE_CH, 0.0, float(vpp))
        time.sleep(settle_s)

        # measure_vpp re-digitizes internally via the scope's measurement system.
        resp = scope.measure_vpp(channel=SIGNAL_CHANNEL)

        vpp_arr.append(float(vpp))
        resp_arr.append(float(resp))
        print("  Vpp = %5.2f V  ->  CH1 Vpp = %8.2f mV" % (vpp, resp * 1e3))

        err = awg.get_error()
        if err:
            print("    Rigol errors:", err)

    return np.asarray(vpp_arr), np.asarray(resp_arr)


def sigmoid(x, L, k, x0, c):
    """Logistic sigmoid: baseline c plus a saturating step of height L."""
    return c + L / (1.0 + np.exp(-k * (x - x0)))


def fit_sigmoid(x, y):
    """Fit the sigmoid to (x, y). Returns popt or None if the fit fails."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    # Initial guesses from the data spread.
    L0 = max(y.max() - y.min(), 1e-9)
    c0 = y.min()
    x0_0 = float(np.median(x))
    span = max(x.max() - x.min(), 1e-9)
    k0 = 4.0 / span  # ~full transition across the swept range

    try:
        popt, _ = curve_fit(
            sigmoid, x, y,
            p0=[L0, k0, x0_0, c0],
            maxfev=10000,
        )
        return popt
    except (RuntimeError, ValueError) as exc:
        warnings.warn("Sigmoid fit did not converge (%s). Plotting raw data only." % exc)
        return None


def plot(x, y, popt, out_path, show=True):
    """Scatter the measured points and overlay the fitted sigmoid."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(x, y * 1e3, color="C0", zorder=3, label="measured")

    if popt is not None:
        xx = np.linspace(x.min(), x.max(), 300)
        ax.plot(xx, sigmoid(xx, *popt) * 1e3, "C1-", lw=2, label="sigmoid fit")
        L, k, x0, c = popt
        print("\nSigmoid fit:  c + L / (1 + exp(-k*(x - x0)))")
        print("  L  (height)   = %.4g V" % L)
        print("  k  (slope)    = %.4g /V" % k)
        print("  x0 (midpoint) = %.4g V" % x0)
        print("  c  (baseline) = %.4g V" % c)
        ax.text(
            0.05, 0.95,
            "x0 = %.2f V\nk = %.2f /V" % (x0, k),
            transform=ax.transAxes, va="top", ha="left",
            bbox=dict(boxstyle="round", fc="white", alpha=0.8),
        )

    ax.set_xlabel("Drive Vpp (V)")
    ax.set_ylabel("Laser response Vpp (mV)")
    ax.set_title("AOM performance: laser response vs. drive Vpp")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    fig.savefig(out_path, dpi=150)
    print("\nSaved plot to %s" % os.path.abspath(out_path))
    if show:
        plt.show()


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Sweep Rigol square-wave Vpp into an AOM and fit the laser "
                    "response sigmoid.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--dg-ip", default=DEFAULT_DG2102_IP, help="Rigol DG2102 LAN IP.")
    p.add_argument("--scope-ip", default=DEFAULT_SCOPE_IP, help="DSO-X 6004A LAN IP.")
    p.add_argument(
        "--vpp", default=",".join(str(v) for v in DEFAULT_VPP_LIST),
        help="Comma-separated drive Vpp setpoints in volts, e.g. 3,6,9,10.",
    )
    p.add_argument("--freq", type=float, default=DEFAULT_SQUARE_FREQ,
                   help="Square-wave frequency in Hz.")
    p.add_argument("--settle", type=float, default=DEFAULT_SETTLE_S,
                   help="Settle time after each amplitude change, in seconds.")
    p.add_argument("--scope-timeout", type=int, default=DEFAULT_SCOPE_TIMEOUT,
                   help="Scope VISA timeout in ms.")
    p.add_argument("--signal-imp", default=DEFAULT_SIGNAL_IMP,
                   choices=["FIFTy", "ONEMeg"],
                   help="CH1 (photodiode) input impedance.")
    p.add_argument("--signal-scale", type=float, default=DEFAULT_SIGNAL_SCALE,
                   help="CH1 vertical scale in V/div.")
    p.add_argument("--out", default=DEFAULT_OUT, help="Output PNG path.")
    p.add_argument("--no-show", action="store_true",
                   help="Do not open an interactive plot window (headless runs).")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        vpp_list = [float(v) for v in args.vpp.split(",") if v.strip() != ""]
    except ValueError:
        raise SystemExit("ERROR: --vpp must be a comma-separated list of numbers, "
                         "e.g. 3,6,9,10. Got: %r" % args.vpp)
    if not vpp_list:
        raise SystemExit("ERROR: --vpp produced an empty list.")

    dg_visa = "TCPIP0::%s::INSTR" % args.dg_ip
    scope_visa = "TCPIP0::%s::INSTR" % args.scope_ip

    awg, scope = connect(dg_visa, scope_visa, args.scope_timeout)
    try:
        configure(awg, scope, args.freq, vpp_list[0],
                  signal_imp=args.signal_imp, signal_scale=args.signal_scale)
        x, y = sweep(awg, scope, vpp_list, args.settle)
        popt = fit_sigmoid(x, y)
        plot(x, y, popt, args.out, show=not args.no_show)
    finally:
        # Always leave the bench in a safe, free-running state.
        try:
            awg.set_output(0)
        finally:
            scope.run()
        print("\nDone. Rigol output OFF, scope in RUN.")


if __name__ == "__main__":
    main()
