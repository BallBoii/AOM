# -*- coding: utf-8 -*-
"""
ScopePanel.py

Minimal, dark-themed control panel + live channel display for the
Keysight DSO-X 6004A oscilloscope and the Rigol DSG836 signal generator.

Display:
    A plotly figure (template "plotly_dark") rendered inside a QWebEngineView.
    One trace per enabled scope channel, plus an optional fit overlay.

Fitting:
    Reuses the GenericFit models in fitters.py (Gaussian, Lorentzian, exp,
    exp_offset, sin, linear). Selecting a model regenerates one initial-guess
    field per model parameter; leaving them blank uses each model's auto-guess.

Hardware only: instruments are created on Connect. If the VISA device is not
found, the panel stays usable but acquisition produces no data.

Run from the repo root:
    uv run python -m gui.ScopePanel
or directly:
    python gui/ScopePanel.py
"""

import os
import sys
import tempfile

# Allow running directly from the gui/ folder as well as `python -m gui.ScopePanel`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import plotly.graph_objects as go

from PyQt6 import QtWidgets
from PyQt6.QtCore import QThread, QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView

from instruments.Oscilloscope import DSOX6004A
from instruments.Rigol import DSG836
from fitters import (
    fit_Gaussian,
    fit_Lorentzian,
    fit_exp,
    fit_exp_offset,
    fit_sin,
    fit_linear,
)


# Common subset of fit models exposed in the panel.
FIT_MODELS = {
    "Gaussian": fit_Gaussian,
    "Lorentzian": fit_Lorentzian,
    "exp": fit_exp,
    "exp_offset": fit_exp_offset,
    "sin": fit_sin,
    "linear": fit_linear,
}

# Bright colors for CH1-CH4 against the dark plot.
CHANNEL_COLORS = {1: "#f5f542", 2: "#42f5f5", 3: "#f542f5", 4: "#7CFC00"}


# ----------------------------------------------------------------------
# Acquisition worker
# ----------------------------------------------------------------------

class AcquireWorker(QThread):
    """Continuously read enabled channels and emit (channel, t, y)."""

    data_ready = pyqtSignal(int, object, object)
    error = pyqtSignal(str)

    def __init__(self, scope, channels, points, interval_s=0.3, parent=None):
        super().__init__(parent)
        self.scope = scope
        self.channels = list(channels)
        self.points = int(points)
        self.interval_s = float(interval_s)
        self._running = False

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            for ch in self.channels:
                if not self._running:
                    break
                try:
                    t, y = self.scope.read_waveform_ascii(
                        source_channel=ch, points=self.points, digitize_first=True
                    )
                    self.data_ready.emit(ch, t, y)
                except Exception as exc:  # keep the loop alive on a bad read
                    self.error.emit("CH%d read failed: %s" % (ch, exc))
            # Coarse sleep between sweeps; plotly redraw is heavier than a canvas.
            for _ in range(int(self.interval_s * 20)):
                if not self._running:
                    break
                self.msleep(50)


# ----------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------

class ScopePanel(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scope + Rigol Control Panel")
        self.resize(1200, 720)

        self.scope = None
        self.rigol = None
        self.worker = None

        # Latest data per channel and current fit overlay.
        self.traces = {}            # ch -> (t, y)
        self.fit_overlay = None     # (x, y, label)

        # Temp dir for the plotly html (plotly.js written via 'directory').
        self._html_dir = tempfile.mkdtemp(prefix="scopepanel_")
        self._html_path = os.path.join(self._html_dir, "plot.html")

        self._build_ui()
        self.update_plot()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)

        # Left: scrollable control panel.
        panel = QtWidgets.QWidget()
        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setSpacing(6)
        panel_layout.addWidget(self._build_connection_group())
        panel_layout.addWidget(self._build_channels_group())
        panel_layout.addWidget(self._build_horiz_trig_group())
        panel_layout.addWidget(self._build_acquire_group())
        panel_layout.addWidget(self._build_run_group())
        panel_layout.addWidget(self._build_rigol_group())
        panel_layout.addWidget(self._build_fit_group())
        panel_layout.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(380)
        root.addWidget(scroll)

        # Right: plotly view + measurement readout.
        right = QtWidgets.QVBoxLayout()
        self.view = QWebEngineView()
        right.addWidget(self.view, 1)
        self.lbl_meas = QtWidgets.QLabel("Vpp / Vavg: --")
        right.addWidget(self.lbl_meas)
        root.addLayout(right, 1)

        self.status = self.statusBar()
        self.status.showMessage("Not connected.")

    def _build_connection_group(self):
        box = QtWidgets.QGroupBox("Connection (LAN)")
        form = QtWidgets.QFormLayout(box)
        # Instruments are on the LAN; enter the IP and the VISA resource string
        # TCPIP0::<IP>::INSTR is built automatically (see test_instruments_lan.ipynb).
        self.ed_scope_ip = QtWidgets.QLineEdit("192.168.68.52")
        self.ed_rigol_ip = QtWidgets.QLineEdit("192.168.68.33")
        self.ed_scope_ip.setPlaceholderText("e.g. 192.168.68.52")
        self.ed_rigol_ip.setPlaceholderText("e.g. 192.168.68.33")
        form.addRow("Scope IP", self.ed_scope_ip)
        form.addRow("Rigol IP", self.ed_rigol_ip)
        btn = QtWidgets.QPushButton("Connect")
        btn.clicked.connect(self.on_connect)
        form.addRow(btn)
        self.lbl_idn = QtWidgets.QLabel("IDN: --")
        self.lbl_idn.setWordWrap(True)
        form.addRow(self.lbl_idn)
        return box

    @staticmethod
    def _visa_resource(ip):
        """Build a LAN VISA resource string from an IP (or pass through a full
        resource string if the user typed one)."""
        ip = ip.strip()
        if not ip:
            return ""
        if "::" in ip:  # already a full VISA resource string
            return ip
        return "TCPIP0::%s::INSTR" % ip

    def _build_channels_group(self):
        box = QtWidgets.QGroupBox("Channels")
        grid = QtWidgets.QGridLayout(box)
        headers = ["", "V/div", "Offset", "Coupling", "Imp"]
        for col, text in enumerate(headers):
            grid.addWidget(QtWidgets.QLabel(text), 0, col)

        self.ch_widgets = {}
        for row, ch in enumerate((1, 2, 3, 4), start=1):
            chk = QtWidgets.QCheckBox("CH%d" % ch)
            chk.setChecked(ch in (1, 2))
            scale = QtWidgets.QDoubleSpinBox()
            scale.setDecimals(3)
            scale.setRange(0.001, 10.0)
            scale.setValue(0.5)
            offset = QtWidgets.QDoubleSpinBox()
            offset.setDecimals(3)
            offset.setRange(-10.0, 10.0)
            offset.setValue(0.0)
            coupling = QtWidgets.QComboBox()
            coupling.addItems(["DC", "AC"])
            imp = QtWidgets.QComboBox()
            imp.addItems(["FIFTy", "ONEMeg"])
            grid.addWidget(chk, row, 0)
            grid.addWidget(scale, row, 1)
            grid.addWidget(offset, row, 2)
            grid.addWidget(coupling, row, 3)
            grid.addWidget(imp, row, 4)
            self.ch_widgets[ch] = dict(
                enable=chk, scale=scale, offset=offset, coupling=coupling, imp=imp
            )
        return box

    def _build_horiz_trig_group(self):
        box = QtWidgets.QGroupBox("Timebase / Trigger")
        form = QtWidgets.QFormLayout(box)
        self.sb_time_range = QtWidgets.QDoubleSpinBox()
        self.sb_time_range.setDecimals(9)
        self.sb_time_range.setRange(1e-9, 50.0)
        self.sb_time_range.setValue(20e-6)
        self.sb_time_pos = QtWidgets.QDoubleSpinBox()
        self.sb_time_pos.setDecimals(9)
        self.sb_time_pos.setRange(-50.0, 50.0)
        self.sb_time_pos.setValue(0.0)
        self.sb_trig_src = QtWidgets.QSpinBox()
        self.sb_trig_src.setRange(1, 4)
        self.sb_trig_src.setValue(2)
        self.sb_trig_level = QtWidgets.QDoubleSpinBox()
        self.sb_trig_level.setDecimals(3)
        self.sb_trig_level.setRange(-10.0, 10.0)
        self.sb_trig_level.setValue(1.0)
        self.cb_slope = QtWidgets.QComboBox()
        self.cb_slope.addItems(["POSitive", "NEGative"])
        self.cb_sweep = QtWidgets.QComboBox()
        self.cb_sweep.addItems(["NORMal", "AUTO"])
        form.addRow("Time range (s)", self.sb_time_range)
        form.addRow("Position (s)", self.sb_time_pos)
        form.addRow("Trig source CH", self.sb_trig_src)
        form.addRow("Trig level (V)", self.sb_trig_level)
        form.addRow("Slope", self.cb_slope)
        form.addRow("Sweep", self.cb_sweep)
        return box

    def _build_acquire_group(self):
        box = QtWidgets.QGroupBox("Acquire")
        form = QtWidgets.QFormLayout(box)
        self.cb_acq_type = QtWidgets.QComboBox()
        self.cb_acq_type.addItems(["NORMal", "AVERage", "HRESolution", "PEAK"])
        self.sb_avg = QtWidgets.QSpinBox()
        self.sb_avg.setRange(2, 65536)
        self.sb_avg.setValue(8)
        self.sb_points = QtWidgets.QSpinBox()
        self.sb_points.setRange(100, 8_000_000)
        self.sb_points.setValue(1000)
        form.addRow("Type", self.cb_acq_type)
        form.addRow("Average count", self.sb_avg)
        form.addRow("Points", self.sb_points)
        btn = QtWidgets.QPushButton("Apply scope settings")
        btn.clicked.connect(self.apply_scope_settings)
        form.addRow(btn)
        return box

    def _build_run_group(self):
        box = QtWidgets.QGroupBox("Run control")
        h = QtWidgets.QHBoxLayout(box)
        self.btn_single = QtWidgets.QPushButton("Single")
        self.btn_single.clicked.connect(self.on_single)
        self.btn_live = QtWidgets.QPushButton("Live")
        self.btn_live.setCheckable(True)
        self.btn_live.toggled.connect(self.on_live_toggled)
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_save = QtWidgets.QPushButton("Save")
        self.btn_save.clicked.connect(self.on_save)
        for b in (self.btn_single, self.btn_live, self.btn_stop, self.btn_save):
            h.addWidget(b)
        return box

    def _build_rigol_group(self):
        box = QtWidgets.QGroupBox("Rigol DSG836 generator")
        form = QtWidgets.QFormLayout(box)
        self.sb_rg_freq = QtWidgets.QDoubleSpinBox()
        self.sb_rg_freq.setDecimals(3)
        self.sb_rg_freq.setRange(9e3, 3.6e9)
        self.sb_rg_freq.setValue(1e9)
        self.sb_rg_pow = QtWidgets.QDoubleSpinBox()
        self.sb_rg_pow.setDecimals(2)
        self.sb_rg_pow.setRange(-110.0, 20.0)
        self.sb_rg_pow.setValue(-30.0)
        self.chk_rg_out = QtWidgets.QCheckBox("Output ON")
        form.addRow("Frequency (Hz)", self.sb_rg_freq)
        form.addRow("Power (dBm)", self.sb_rg_pow)
        form.addRow(self.chk_rg_out)
        btn = QtWidgets.QPushButton("Apply generator")
        btn.clicked.connect(self.apply_rigol_settings)
        form.addRow(btn)
        return box

    def _build_fit_group(self):
        box = QtWidgets.QGroupBox("Fit")
        v = QtWidgets.QVBoxLayout(box)
        form = QtWidgets.QFormLayout()
        self.cb_fit_ch = QtWidgets.QComboBox()
        self.cb_fit_ch.addItems(["CH1", "CH2", "CH3", "CH4"])
        self.cb_fit_model = QtWidgets.QComboBox()
        self.cb_fit_model.addItems(list(FIT_MODELS.keys()))
        self.cb_fit_model.currentTextChanged.connect(self._rebuild_param_fields)
        form.addRow("Channel", self.cb_fit_ch)
        form.addRow("Model", self.cb_fit_model)
        v.addLayout(form)

        # Container whose form layout holds one guess field per parameter.
        self.param_box = QtWidgets.QWidget()
        self.param_form = QtWidgets.QFormLayout(self.param_box)
        self.param_form.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.param_box)
        self.param_edits = {}

        btn = QtWidgets.QPushButton("Fit")
        btn.clicked.connect(self.on_fit)
        v.addWidget(btn)
        btn_clear = QtWidgets.QPushButton("Clear fit")
        btn_clear.clicked.connect(self.on_clear_fit)
        v.addWidget(btn_clear)
        self.lbl_fit = QtWidgets.QLabel("No fit yet.")
        self.lbl_fit.setWordWrap(True)
        v.addWidget(self.lbl_fit)

        self._rebuild_param_fields(self.cb_fit_model.currentText())
        return box

    def _rebuild_param_fields(self, model_name):
        # Clear previous fields.
        while self.param_form.rowCount():
            self.param_form.removeRow(0)
        self.param_edits = {}
        model_cls = FIT_MODELS[model_name]
        for pname in model_cls().params:
            edit = QtWidgets.QLineEdit()
            edit.setPlaceholderText("auto")
            self.param_form.addRow(pname, edit)
            self.param_edits[pname] = edit

    # ------------------------------------------------------------------
    # Connection / settings
    # ------------------------------------------------------------------

    def on_connect(self):
        scope_addr = self._visa_resource(self.ed_scope_ip.text())
        rigol_addr = self._visa_resource(self.ed_rigol_ip.text())

        if scope_addr:
            self.scope = DSOX6004A(scope_addr)
            if self.scope.connected:
                try:
                    self.lbl_idn.setText("IDN: " + self.scope.idn())
                except Exception as exc:
                    self.lbl_idn.setText("IDN query failed: %s" % exc)
            else:
                self.lbl_idn.setText("IDN: scope not found")

        if rigol_addr:
            self.rigol = DSG836(rigol_addr)

        scope_ok = self.scope is not None and self.scope.connected
        rigol_ok = self.rigol is not None and self.rigol.connected
        self.status.showMessage(
            "Scope %s | Rigol %s"
            % ("connected" if scope_ok else "not found",
               "connected" if rigol_ok else "not found")
        )

    def apply_scope_settings(self):
        if not self._scope_ready():
            return
        for ch, w in self.ch_widgets.items():
            if w["enable"].isChecked():
                self.scope.set_channel(
                    ch,
                    scale=w["scale"].value(),
                    offset=w["offset"].value(),
                    coupling=w["coupling"].currentText(),
                    impedance=w["imp"].currentText(),
                    display=True,
                )
            else:
                self.scope.channel_on(ch, False)

        self.scope.set_timebase(
            time_range=self.sb_time_range.value(), position=self.sb_time_pos.value()
        )
        self.scope.set_edge_trigger(
            source_channel=self.sb_trig_src.value(),
            level=self.sb_trig_level.value(),
            slope=self.cb_slope.currentText(),
            sweep=self.cb_sweep.currentText(),
        )
        self.scope.set_acquire(
            acquire_type=self.cb_acq_type.currentText(),
            average_count=self.sb_avg.value(),
        )
        self.status.showMessage("Scope settings applied.")

    def apply_rigol_settings(self):
        if self.rigol is None or not self.rigol.connected:
            self.status.showMessage("Rigol not connected.")
            return
        self.rigol.set_freq(self.sb_rg_freq.value())
        self.rigol.set_pow(self.sb_rg_pow.value())
        self.rigol.set_output(1 if self.chk_rg_out.isChecked() else 0)
        self.status.showMessage("Generator updated.")

    def _scope_ready(self):
        if self.scope is None or not self.scope.connected:
            self.status.showMessage("Scope not connected.")
            return False
        return True

    def _enabled_channels(self):
        return [ch for ch, w in self.ch_widgets.items() if w["enable"].isChecked()]

    # ------------------------------------------------------------------
    # Acquisition
    # ------------------------------------------------------------------

    def on_single(self):
        if not self._scope_ready():
            return
        channels = self._enabled_channels()
        if not channels:
            self.status.showMessage("No channel enabled.")
            return
        self.status.showMessage("Acquiring single...")
        QtWidgets.QApplication.processEvents()
        try:
            for ch in channels:
                t, y = self.scope.read_waveform_ascii(
                    source_channel=ch, points=self.sb_points.value(), digitize_first=True
                )
                self.traces[ch] = (t, y)
            self._update_measurements(channels[0])
            self.update_plot()
            self.status.showMessage("Single acquisition done.")
        except Exception as exc:
            self.status.showMessage("Single failed: %s" % exc)

    def on_live_toggled(self, checked):
        if checked:
            if not self._scope_ready():
                self.btn_live.setChecked(False)
                return
            channels = self._enabled_channels()
            if not channels:
                self.status.showMessage("No channel enabled.")
                self.btn_live.setChecked(False)
                return
            self._set_controls_enabled(False)
            self.worker = AcquireWorker(self.scope, channels, self.sb_points.value())
            self.worker.data_ready.connect(self.on_data_ready)
            self.worker.error.connect(self.status.showMessage)
            self.worker.start()
            self.status.showMessage("Live acquisition running.")
        else:
            self._stop_worker()
            self._set_controls_enabled(True)
            self.status.showMessage("Live stopped.")

    def on_stop(self):
        if self.btn_live.isChecked():
            self.btn_live.setChecked(False)  # triggers on_live_toggled(False)
        if self._scope_ready():
            self.scope.stop()
        self.status.showMessage("Stopped.")

    def on_data_ready(self, ch, t, y):
        self.traces[ch] = (t, y)
        # Redraw once per sweep: update only after the last enabled channel.
        enabled = self._enabled_channels()
        if enabled and ch == enabled[-1]:
            self.update_plot()

    def _stop_worker(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait()
            self.worker = None

    def _set_controls_enabled(self, enabled):
        # While live, lock settings/single to keep VISA single-threaded.
        self.btn_single.setEnabled(enabled)
        for w in self.ch_widgets.values():
            for key in ("enable", "scale", "offset", "coupling", "imp"):
                w[key].setEnabled(enabled)

    def _update_measurements(self, ch):
        try:
            vpp = self.scope.measure_vpp(ch)
            vavg = self.scope.measure_vavg(ch)
            self.lbl_meas.setText("CH%d  Vpp=%.4g V  Vavg=%.4g V" % (ch, vpp, vavg))
        except Exception:
            self.lbl_meas.setText("Vpp / Vavg: --")

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def update_plot(self):
        fig = go.Figure()
        for ch, (t, y) in sorted(self.traces.items()):
            fig.add_trace(
                go.Scatter(
                    x=np.asarray(t), y=np.asarray(y), mode="lines",
                    name="CH%d" % ch,
                    line=dict(color=CHANNEL_COLORS.get(ch, "#ffffff")),
                )
            )
        if self.fit_overlay is not None:
            fx, fy, label = self.fit_overlay
            fig.add_trace(
                go.Scatter(
                    x=fx, y=fy, mode="lines", name=label,
                    line=dict(color="#ff4136", dash="dash"),
                )
            )
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=50, r=20, t=30, b=40),
            xaxis_title="Time (s)",
            yaxis_title="Voltage (V)",
            legend=dict(orientation="h", y=1.02, yanchor="bottom"),
        )

        # 'directory' writes plotly.min.js next to the html (offline-friendly).
        fig.write_html(self._html_path, include_plotlyjs="directory", full_html=True)
        self.view.load(QUrl.fromLocalFile(self._html_path))

    # ------------------------------------------------------------------
    # Fitting (reuses fitters.GenericFit)
    # ------------------------------------------------------------------

    def on_fit(self):
        ch = self.cb_fit_ch.currentIndex() + 1
        if ch not in self.traces:
            self.lbl_fit.setText("No data on CH%d to fit." % ch)
            return
        t, y = self.traces[ch]
        model_name = self.cb_fit_model.currentText()
        fitter = FIT_MODELS[model_name]()
        fitter.set_data(np.asarray(y), np.asarray(t))

        # Optional manual guess: only used if every field is filled.
        guess = self._read_guess()
        if guess is not None:
            fitter.set_guess(np.array(guess))

        try:
            fitter.dofit()
        except Exception as exc:
            self.lbl_fit.setText("Fit failed: %s" % exc)
            return

        fx, fy = fitter.get_fitcurve_smooth(300)
        self.fit_overlay = (np.asarray(fx), np.asarray(fy),
                            "%s fit (CH%d)" % (model_name, ch))
        lines = ["%s = %.4g" % (p, v) for p, v in zip(fitter.params, fitter.fp)]
        self.lbl_fit.setText("\n".join(lines))
        self.update_plot()

    def _read_guess(self):
        vals = []
        for edit in self.param_edits.values():
            text = edit.text().strip()
            if text == "":
                return None  # any blank -> fall back to auto-guess
            try:
                vals.append(float(text))
            except ValueError:
                return None
        return vals if vals else None

    def on_clear_fit(self):
        self.fit_overlay = None
        self.lbl_fit.setText("No fit yet.")
        self.update_plot()

    # ------------------------------------------------------------------
    # Save / close
    # ------------------------------------------------------------------

    def on_save(self):
        ch = self.cb_fit_ch.currentIndex() + 1
        if ch not in self.traces:
            self.status.showMessage("No data on CH%d to save." % ch)
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save trace", "ch%d_trace.csv" % ch, "CSV (*.csv)"
        )
        if not path:
            return
        t, y = self.traces[ch]
        np.savetxt(
            path, np.column_stack([np.asarray(t), np.asarray(y)]),
            delimiter=",", header="time_s,voltage_v", comments="",
        )
        self.status.showMessage("Saved %s" % path)

    def closeEvent(self, event):
        self._stop_worker()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    try:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt6"))
    except Exception:
        app.setStyle("Fusion")  # minimal fallback
    win = ScopePanel()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
