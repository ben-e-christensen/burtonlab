"""
GDS-1054B Oscilloscope Monitor  v5
Polls CH1 (Top Ring), CH2 (Middle Ring), CH3 (Bottom Ring)

Two modes selectable in the GUI:
  - Scalar: fast measurement queries (:MEASure:PK2Pk?, etc.)
  - Waveform: mini waveform grab (1000 pts), compute stats in numpy

Separate windows for plot and webcam.
CSV logging of stats. Webcam PNGs at 5 FPS.
"""

import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import serial
import time
import threading
import csv
import os
from datetime import datetime
import cv2
from PIL import Image, ImageTk
import numpy as np
import re

# ── Defaults ──────────────────────────────────────────────────────────
COM_PORT = "COM6"
BAUD = 115200
TIMEOUT = 2
WEBCAM_INDEX = 0
CMD_DELAY = 0.05
MAX_POINTS = 600
OUTPUT_DIR = "scope_data"
PNG_FPS = 5
WAVEFORM_RECORD_LEN = 1000   # small for speed

CHANNEL_CFG = {
    1: {"label": "CH1 – Top Ring",    "color": "#e6b800"},
    2: {"label": "CH2 – Middle Ring", "color": "#00bfff"},
    3: {"label": "CH3 – Bottom Ring", "color": "#ff4d4d"},
}

MEAS_COMMANDS = {
    "Pk-Pk":     ":MEASure:PK2Pk?",
    "MAX":       ":MEASure:MAX?",
    "MIN":       ":MEASure:MIN?",
    "RMS":       ":MEASure:RMS?",
    "Mean":      ":MEASure:MEAN?",
    "Frequency": ":MEASure:FREQuency?",
    "Amplitude": ":MEASure:AMPlitude?",
}


class ScopeMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("GDS-1054B  ·  3-Channel Monitor")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── state ─────────────────────────────────────────────────────
        self.running = False
        self.recording = False
        self.scope = None
        self.cap = None
        self.t0 = None

        # scrolling stats history
        self.times = []
        self.ch_data = {1: [], 2: [], 3: []}

        # latest waveform traces (for waveform subplot)
        self.wf_t = {1: None, 2: None, 3: None}
        self.wf_v = {1: None, 2: None, 3: None}

        self.csv_file = None
        self.csv_writer = None
        self.png_dir = None
        self._last_frame = None
        self._frame_lock = threading.Lock()

        self.mode_var = tk.StringVar(value="Waveform")
        self.meas_type = tk.StringVar(value="Pk-Pk")
        self.run_label = tk.StringVar(value="run")
        self.status_var = tk.StringVar(value="Idle")
        self.reading_vars = {ch: tk.StringVar(value="---") for ch in (1, 2, 3)}
        self.poll_count = 0

        self._build_main_window()
        self._build_webcam_window()

    # ═══════════════════════════════════════════════════════════════════
    #  GUI
    # ═══════════════════════════════════════════════════════════════════
    def _build_main_window(self):
        ctrl = ttk.Frame(self.root, padding=6)
        ctrl.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(ctrl, text="Run label:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(ctrl, textvariable=self.run_label, width=14).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(ctrl, text="Mode:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Combobox(ctrl, textvariable=self.mode_var,
                      values=["Scalar", "Waveform"], state="readonly",
                      width=9).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(ctrl, text="Stat:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Combobox(ctrl, textvariable=self.meas_type,
                      values=list(MEAS_COMMANDS.keys()),
                      state="readonly", width=9).pack(side=tk.LEFT, padx=(0, 8))

        self.btn_start = ttk.Button(ctrl, text="Start", command=self._start)
        self.btn_start.pack(side=tk.LEFT, padx=2)
        self.btn_stop = ttk.Button(ctrl, text="Stop", command=self._stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=2)
        self.btn_record = ttk.Button(ctrl, text="● Record", command=self._toggle_record, state=tk.DISABLED)
        self.btn_record.pack(side=tk.LEFT, padx=2)
        self.btn_clear = ttk.Button(ctrl, text="Clear", command=self._clear)
        self.btn_clear.pack(side=tk.LEFT, padx=2)

        # live readings
        readings = tk.Frame(self.root, bg="#1e1e1e", padx=6, pady=4)
        readings.pack(side=tk.TOP, fill=tk.X)
        for ch in (1, 2, 3):
            cfg = CHANNEL_CFG[ch]
            tk.Label(readings, text=cfg["label"] + ": ", font=("Consolas", 11, "bold"),
                     fg=cfg["color"], bg="#1e1e1e").pack(side=tk.LEFT)
            tk.Label(readings, textvariable=self.reading_vars[ch],
                     font=("Consolas", 13), fg=cfg["color"], bg="#1e1e1e",
                     width=14).pack(side=tk.LEFT, padx=(0, 16))

        # matplotlib: 2 subplots (waveform trace + scrolling stats)
        self.fig = Figure(figsize=(9, 5.5), dpi=100, facecolor="#1e1e1e")
        self.ax_wf = self.fig.add_subplot(211)     # latest waveform
        self.ax_ts = self.fig.add_subplot(212)     # time-series stats
        self._style_ax(self.ax_wf, ylabel="Voltage (V)", xlabel="Sample Time (s)")
        self._style_ax(self.ax_ts, ylabel="Stat Value", xlabel="Elapsed (s)")

        self.wf_lines = {}
        self.ts_lines = {}
        for ch in (1, 2, 3):
            cfg = CHANNEL_CFG[ch]
            wl, = self.ax_wf.plot([], [], color=cfg["color"], linewidth=0.8,
                                   label=cfg["label"])
            tl, = self.ax_ts.plot([], [], color=cfg["color"], linewidth=1.2,
                                   label=cfg["label"], marker=".", markersize=3)
            self.wf_lines[ch] = wl
            self.ts_lines[ch] = tl

        self.ax_wf.legend(loc="upper right", fontsize=7, facecolor="#2a2a2a",
                          edgecolor="#444", labelcolor="white")
        self.ax_ts.legend(loc="upper left", fontsize=7, facecolor="#2a2a2a",
                          edgecolor="#444", labelcolor="white")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        ttk.Label(self.root, textvariable=self.status_var,
                  relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def _style_ax(self, ax, ylabel="", xlabel=""):
        ax.set_facecolor("#1e1e1e")
        ax.set_xlabel(xlabel, color="white", fontsize=8)
        ax.set_ylabel(ylabel, color="white", fontsize=8)
        ax.tick_params(colors="white", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#444")
        ax.grid(True, alpha=0.25, color="#555")
        self.fig.tight_layout()

    # ═══════════════════════════════════════════════════════════════════
    #  Webcam window
    # ═══════════════════════════════════════════════════════════════════
    def _build_webcam_window(self):
        self.cam_win = tk.Toplevel(self.root)
        self.cam_win.title("Webcam")
        self.cam_win.protocol("WM_DELETE_WINDOW", lambda: None)
        self.cam_win.geometry("640x480")
        self.cam_label = tk.Label(self.cam_win, bg="black")
        self.cam_label.pack(fill=tk.BOTH, expand=True)

        try:
            self.cap = cv2.VideoCapture(WEBCAM_INDEX, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(WEBCAM_INDEX)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self._cam_tick()
                print("[CAM] Webcam opened OK")
            else:
                self.cam_label.config(text="No webcam found", fg="gray", font=("Consolas", 14))
        except Exception as e:
            self.cam_label.config(text=f"Cam error: {e}", fg="red")

    def _cam_tick(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                with self._frame_lock:
                    self._last_frame = frame.copy()
                display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                win_w = self.cam_label.winfo_width()
                win_h = self.cam_label.winfo_height()
                if win_w > 10 and win_h > 10:
                    display = cv2.resize(display, (win_w, win_h))
                img = Image.fromarray(display)
                imgtk = ImageTk.PhotoImage(image=img)
                self.cam_label.configure(image=imgtk)
                self.cam_label._imgtk = imgtk
        self.root.after(33, self._cam_tick)

    def _png_save_loop(self):
        """Save webcam PNGs at PNG_FPS while recording."""
        interval = 1.0 / PNG_FPS
        frame_num = 0
        while self.recording:
            t0 = time.time()
            with self._frame_lock:
                frame = self._last_frame
            if frame is not None and self.png_dir:
                fname = os.path.join(self.png_dir, f"frame_{frame_num:06d}.png")
                cv2.imwrite(fname, frame)
                frame_num += 1
            elapsed = time.time() - t0
            time.sleep(max(0, interval - elapsed))
        print(f"[PNG] Saved {frame_num} frames")

    # ═══════════════════════════════════════════════════════════════════
    #  Scope serial helpers
    # ═══════════════════════════════════════════════════════════════════
    def _connect_scope(self):
        try:
            self.scope = serial.Serial(COM_PORT, BAUD, timeout=TIMEOUT)
            time.sleep(0.3)
            self.scope.reset_input_buffer()
            self.scope.reset_output_buffer()
            idn = self._query("*IDN?")
            print(f"[SCOPE] Connected: {idn}")
            self._set_status(f"Connected: {idn.strip()}")
            return True
        except Exception as e:
            print(f"[SCOPE] Connection failed: {e}")
            self._set_status(f"Scope connect FAILED: {e}")
            return False

    def _scpi_write(self, cmd):
        if self.scope and self.scope.is_open:
            self.scope.write((cmd.strip() + "\n").encode("ascii"))

    def _query(self, cmd):
        if not (self.scope and self.scope.is_open):
            return ""
        self.scope.reset_input_buffer()
        self.scope.write((cmd.strip() + "\n").encode("ascii"))
        time.sleep(CMD_DELAY)
        raw = self.scope.readline()
        if self.scope.in_waiting:
            self.scope.read(self.scope.in_waiting)
        decoded = raw.decode(errors="replace").strip()
        print(f"[SCPI] {cmd:35s} → '{decoded[:60]}'")
        return decoded

    def _read_exact(self, n_bytes, idle_timeout=10.0):
        buf = bytearray()
        last_progress = time.time()
        while len(buf) < n_bytes:
            chunk = self.scope.read(n_bytes - len(buf))
            if chunk:
                buf.extend(chunk)
                last_progress = time.time()
            elif time.time() - last_progress > idle_timeout:
                raise TimeoutError(f"Scope silent after {len(buf)}/{n_bytes} bytes")
        return bytes(buf)

    # ── Scalar measurement ────────────────────────────────────────────
    def _read_scalar(self, ch):
        meas_cmd = MEAS_COMMANDS.get(self.meas_type.get(), ":MEASure:PK2Pk?")
        self._scpi_write(f":MEASure:SOURce1 CH{ch}")
        time.sleep(CMD_DELAY)
        resp = self._query(meas_cmd)
        return self._parse_float(resp)

    # ── Waveform grab ─────────────────────────────────────────────────
    def _grab_waveforms(self):
        """
        Stop scope, grab short waveforms from all 3 channels,
        restart scope. Returns dict {ch: (t_array, v_array)} and
        a dict of computed stats {ch: float}.
        """
        record_len = WAVEFORM_RECORD_LEN

        # configure and run
        self._scpi_write(":HEADer ON")
        time.sleep(CMD_DELAY)
        self._scpi_write(f":ACQuire:RECOrdlength {record_len}")
        time.sleep(CMD_DELAY)
        self._scpi_write(":TRIGger:MODe AUTO")
        time.sleep(CMD_DELAY)
        self._scpi_write(":RUN")

        # read back the confirmed timebase scale for timing
        resp = self._query(":TIMebase:SCALe?")
        try:
            tb_scale = float(resp)
        except ValueError:
            tb_scale = 0.001  # fallback 1ms/div
        window_s = tb_scale * 10.0

        # let the scope fill one window
        time.sleep(max(window_s + 0.1, 0.2))
        self._scpi_write(":STOP")
        time.sleep(0.15)

        waveforms = {}
        stats = {}
        stat_type = self.meas_type.get()

        for ch in (1, 2, 3):
            try:
                v, meta = self._read_channel_memory(ch, record_len)
                # compute time axis
                try:
                    sp = float(meta.get("Sampling Period", "nan"))
                except ValueError:
                    sp = float("nan")
                if not np.isfinite(sp):
                    sp = window_s / record_len
                t = np.arange(len(v)) * sp

                waveforms[ch] = (t, v)

                # compute the selected stat from the raw data
                if stat_type == "Pk-Pk":
                    stats[ch] = float(np.ptp(v))
                elif stat_type == "MAX":
                    stats[ch] = float(np.max(v))
                elif stat_type == "MIN":
                    stats[ch] = float(np.min(v))
                elif stat_type == "RMS":
                    stats[ch] = float(np.sqrt(np.mean(v**2)))
                elif stat_type == "Mean":
                    stats[ch] = float(np.mean(v))
                elif stat_type == "Amplitude":
                    stats[ch] = float(np.max(v) - np.min(v))
                else:
                    stats[ch] = float(np.ptp(v))

            except Exception as e:
                print(f"[WF] CH{ch} grab failed: {e}")
                waveforms[ch] = (np.array([0]), np.array([0]))
                stats[ch] = None

        # restart live acquisition
        self._scpi_write(":RUN")
        return waveforms, stats

    def _read_channel_memory(self, channel, record_length):
        """Read one channel's stored waveform (scope must be stopped)."""
        self._scpi_write(f":ACQuire{channel}:MEMory?")

        # read until '#' block header
        buf = bytearray()
        last_progress = time.time()
        while b"#" not in buf:
            chunk = self.scope.read(4096)
            if chunk:
                buf.extend(chunk)
                last_progress = time.time()
            elif time.time() - last_progress > 10.0:
                raise TimeoutError("No '#' block header")

        hash_idx = buf.index(b"#")
        while len(buf) < hash_idx + 2:
            buf.extend(self._read_exact(1))
        n_len_digits = int(buf[hash_idx + 1:hash_idx + 2])

        header_end = hash_idx + 2 + n_len_digits
        while len(buf) < header_end:
            buf.extend(self._read_exact(header_end - len(buf)))
        n_data_bytes = int(buf[hash_idx + 2:header_end])

        total_needed = header_end + n_data_bytes
        if len(buf) < total_needed:
            buf.extend(self._read_exact(total_needed - len(buf)))

        preamble = buf[:hash_idx].decode("ascii", errors="ignore")
        raw_bytes = bytes(buf[header_end:total_needed])
        self.scope.reset_input_buffer()

        # parse vertical scale from preamble
        m = re.search(r"Vertical Scale,([^;]+);", preamble)
        vscale = float(m.group(1)) if m else 1.0

        raw = np.frombuffer(raw_bytes, dtype=">i2").astype(np.float64)
        v = (raw / 25.0) * vscale

        meta = dict(re.findall(r"([^,;]+),([^;]+);", preamble))
        return v, meta

    @staticmethod
    def _parse_float(s):
        if not s:
            return None
        if "off" in s.lower():
            return None
        for token in reversed(s.split()):
            try:
                return float(token)
            except ValueError:
                continue
        return None

    # ═══════════════════════════════════════════════════════════════════
    #  Polling thread
    # ═══════════════════════════════════════════════════════════════════
    def _poll_loop(self):
        while self.running:
            t_now = time.time() - self.t0
            mode = self.mode_var.get()

            if mode == "Waveform":
                waveforms, vals = self._grab_waveforms()
                # stash waveform data for plot update
                for ch in (1, 2, 3):
                    self.wf_t[ch], self.wf_v[ch] = waveforms[ch]
            else:
                vals = {}
                for ch in (1, 2, 3):
                    vals[ch] = self._read_scalar(ch)

            # update readings and history
            for ch in (1, 2, 3):
                v = vals.get(ch)
                if v is not None:
                    self.ch_data[ch].append(v)
                    if abs(v) < 0.01:
                        self.reading_vars[ch].set(f"{v*1e3:+.3f} mV")
                    else:
                        self.reading_vars[ch].set(f"{v:+.4f} V")
                else:
                    self.ch_data[ch].append(float("nan"))
                    self.reading_vars[ch].set("ERR")

            self.times.append(t_now)
            self.poll_count += 1

            # CSV
            if self.recording and self.csv_writer:
                self.csv_writer.writerow([
                    f"{t_now:.4f}",
                    vals.get(1, ""),
                    vals.get(2, ""),
                    vals.get(3, ""),
                    datetime.now().isoformat(timespec="milliseconds"),
                ])
                self.csv_file.flush()

            self.root.after(0, self._update_plot)

    def _update_plot(self):
        if not self.times:
            return

        mode = self.mode_var.get()

        # ── top subplot: waveform trace ───────────────────────────────
        if mode == "Waveform":
            for ch in (1, 2, 3):
                t, v = self.wf_t[ch], self.wf_v[ch]
                if t is not None and v is not None:
                    self.wf_lines[ch].set_data(t, v)
            self.ax_wf.relim()
            self.ax_wf.autoscale_view()
            self.ax_wf.set_title("Latest Waveform Capture", color="white", fontsize=9)
        else:
            # in scalar mode, clear the waveform plot
            for ch in (1, 2, 3):
                self.wf_lines[ch].set_data([], [])
            self.ax_wf.set_title("(Scalar mode – no waveform)", color="gray", fontsize=9)

        # ── bottom subplot: scrolling stats ───────────────────────────
        n = MAX_POINTS
        t_slice = self.times[-n:]
        for ch in (1, 2, 3):
            d_slice = self.ch_data[ch][-n:]
            self.ts_lines[ch].set_data(t_slice, d_slice)

        self.ax_ts.set_xlim(t_slice[0], t_slice[-1] if len(t_slice) > 1 else t_slice[0] + 1)
        self.ax_ts.relim()
        self.ax_ts.autoscale_view(scalex=False, scaley=True)
        stat_label = self.meas_type.get()
        self.ax_ts.set_title(f"{stat_label} over time", color="white", fontsize=9)

        self.canvas.draw_idle()

        elapsed = self.times[-1] if self.times[-1] > 0 else 0.01
        rate = self.poll_count / elapsed
        rec_tag = "  ● REC" if self.recording else ""
        self._set_status(f"Samples: {len(self.times)}   Rate: {rate:.2f} samp/s   Mode: {self.mode_var.get()}{rec_tag}")

    # ═══════════════════════════════════════════════════════════════════
    #  Controls
    # ═══════════════════════════════════════════════════════════════════
    def _start(self):
        if self.running:
            return
        if self.scope is None:
            if not self._connect_scope():
                return
        self.running = True
        self.t0 = time.time()
        self.poll_count = 0
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_record.config(state=tk.NORMAL)
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _stop(self):
        self.running = False
        if self.recording:
            self._toggle_record()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_record.config(state=tk.DISABLED)
        self._set_status("Stopped")

    def _toggle_record(self):
        if not self.recording:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", self.run_label.get().strip()) or "run"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # CSV
            csv_fname = os.path.join(OUTPUT_DIR, f"{ts}_{slug}.csv")
            self.csv_file = open(csv_fname, "w", newline="")
            self.csv_writer = csv.writer(self.csv_file)
            stat = self.meas_type.get()
            mode = self.mode_var.get()
            self.csv_writer.writerow([
                "time_s",
                f"ch1_top_{stat}",
                f"ch2_mid_{stat}",
                f"ch3_bot_{stat}",
                "timestamp",
            ])

            # PNG folder
            self.png_dir = os.path.join(OUTPUT_DIR, f"{ts}_{slug}_frames")
            os.makedirs(self.png_dir, exist_ok=True)

            self.recording = True
            self.btn_record.config(text="■ Stop Rec")
            self._set_status(f"Recording → {csv_fname}")
            print(f"[REC] CSV → {csv_fname}")
            print(f"[REC] PNG → {self.png_dir}/")

            threading.Thread(target=self._png_save_loop, daemon=True).start()
        else:
            self.recording = False
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            self.png_dir = None
            self.btn_record.config(text="● Record")
            print("[REC] Stopped")

    def _clear(self):
        self.times.clear()
        for ch in (1, 2, 3):
            self.ch_data[ch].clear()
            self.wf_t[ch] = None
            self.wf_v[ch] = None
        self.poll_count = 0
        self.t0 = time.time() if self.running else None
        for ch in (1, 2, 3):
            self.reading_vars[ch].set("---")
            self.wf_lines[ch].set_data([], [])
            self.ts_lines[ch].set_data([], [])
        self.canvas.draw_idle()
        self._set_status("Cleared")

    def _set_status(self, msg):
        self.status_var.set(msg)

    def _on_close(self):
        self.running = False
        self.recording = False
        time.sleep(0.3)
        if self.csv_file:
            self.csv_file.close()
        if self.scope and self.scope.is_open:
            try:
                self.scope.write(b":RUN\n")   # leave scope running
            except Exception:
                pass
            self.scope.close()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.cam_win.destroy()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x650")
    app = ScopeMonitor(root)
    root.mainloop()