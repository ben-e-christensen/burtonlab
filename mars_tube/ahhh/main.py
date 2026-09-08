"""
GDS-1054B Oscilloscope Monitor  v8
Polls CH1 (Top Ring), CH2 (Middle Ring), CH3 (Bottom Ring)

Grabs full waveform buffer each cycle. Plots latest waveform.
Saves raw data as .npz files. No stats computed at runtime.

Output structure:
  scope_data/
    20260908_HHMMSS_label/
      waveforms/
        capture_000000.npz
        ...
      frames/
        frame_000000.png
        ...
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
OUTPUT_DIR = "scope_data"
PNG_FPS = 5
WAVEFORM_RECORD_LEN = 1000

CHANNEL_CFG = {
    1: {"label": "CH1 – Top Ring",    "color": "#e6b800"},
    2: {"label": "CH2 – Middle Ring", "color": "#00bfff"},
    3: {"label": "CH3 – Bottom Ring", "color": "#ff4d4d"},
}


class ScopeMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("GDS-1054B  ·  3-Channel Monitor")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.running = False
        self.recording = False
        self.scope = None
        self.cap = None
        self.t0 = None

        self.wf_t = {1: None, 2: None, 3: None}
        self.wf_v = {1: None, 2: None, 3: None}

        self.frames_dir = None
        self.waveforms_dir = None
        self.capture_num = 0
        self.poll_count = 0
        self._last_frame = None
        self._frame_lock = threading.Lock()

        self.run_label = tk.StringVar(value="run")
        self.status_var = tk.StringVar(value="Idle")

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

        self.btn_start = ttk.Button(ctrl, text="Start", command=self._start)
        self.btn_start.pack(side=tk.LEFT, padx=2)
        self.btn_stop = ttk.Button(ctrl, text="Stop", command=self._stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=2)
        self.btn_record = ttk.Button(ctrl, text="● Record", command=self._toggle_record, state=tk.DISABLED)
        self.btn_record.pack(side=tk.LEFT, padx=2)

        # single waveform plot
        self.fig = Figure(figsize=(9, 4.5), dpi=100, facecolor="#1e1e1e")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1e1e1e")
        self.ax.set_xlabel("Time (s)", color="white", fontsize=9)
        self.ax.set_ylabel("Voltage (V)", color="white", fontsize=9)
        self.ax.set_title("Latest Waveform", color="white", fontsize=10)
        self.ax.tick_params(colors="white", labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color("#444")
        self.ax.grid(True, alpha=0.25, color="#555")

        self.wf_lines = {}
        for ch in (1, 2, 3):
            cfg = CHANNEL_CFG[ch]
            line, = self.ax.plot([], [], color=cfg["color"], linewidth=0.8, label=cfg["label"])
            self.wf_lines[ch] = line
        self.ax.legend(loc="upper right", fontsize=8, facecolor="#2a2a2a",
                       edgecolor="#444", labelcolor="white")
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        ttk.Label(self.root, textvariable=self.status_var,
                  relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    # ═══════════════════════════════════════════════════════════════════
    #  Webcam
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
        interval = 1.0 / PNG_FPS
        frame_num = 0
        while self.recording:
            t0 = time.time()
            with self._frame_lock:
                frame = self._last_frame
            if frame is not None and self.frames_dir:
                fname = os.path.join(self.frames_dir, f"frame_{frame_num:06d}.png")
                cv2.imwrite(fname, frame)
                frame_num += 1
            elapsed = time.time() - t0
            time.sleep(max(0, interval - elapsed))
        print(f"[PNG] Saved {frame_num} frames")

    # ═══════════════════════════════════════════════════════════════════
    #  Scope
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

    def _read_channel_memory(self, channel, record_length):
        self._scpi_write(f":ACQuire{channel}:MEMory?")

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

        m = re.search(r"Vertical Scale,([^;]+);", preamble)
        vscale = float(m.group(1)) if m else 1.0

        raw = np.frombuffer(raw_bytes, dtype=">i2").astype(np.float64)
        v = (raw / 25.0) * vscale

        meta = dict(re.findall(r"([^,;]+),([^;]+);", preamble))
        return v, meta

    def _grab_waveforms(self):
        record_len = WAVEFORM_RECORD_LEN

        self._scpi_write(":HEADer ON")
        time.sleep(CMD_DELAY)
        self._scpi_write(f":ACQuire:RECOrdlength {record_len}")
        time.sleep(CMD_DELAY)
        self._scpi_write(":TRIGger:MODe AUTO")
        time.sleep(CMD_DELAY)
        self._scpi_write(":RUN")

        resp = self._query(":TIMebase:SCALe?")
        try:
            tb_scale = float(resp)
        except ValueError:
            tb_scale = 0.001
        window_s = tb_scale * 10.0

        time.sleep(max(window_s + 0.1, 0.2))
        self._scpi_write(":STOP")
        time.sleep(0.15)

        waveforms = {}
        for ch in (1, 2, 3):
            if not self.running:
                break
            try:
                v, meta = self._read_channel_memory(ch, record_len)
                try:
                    sp = float(meta.get("Sampling Period", "nan"))
                except ValueError:
                    sp = float("nan")
                if not np.isfinite(sp):
                    sp = window_s / record_len
                t = np.arange(len(v)) * sp
                waveforms[ch] = (t, v)
            except Exception as e:
                print(f"[WF] CH{ch} grab failed: {e}")
                waveforms[ch] = None

        # restart scope
        if self.scope and self.scope.is_open:
            self._scpi_write(":RUN")

        return waveforms

    # ═══════════════════════════════════════════════════════════════════
    #  Polling thread
    # ═══════════════════════════════════════════════════════════════════
    def _poll_loop(self):
        while self.running:
            t_now = time.time() - self.t0
            waveforms = self._grab_waveforms()

            if not self.running:
                break

            # stash for plot
            for ch in (1, 2, 3):
                if waveforms.get(ch) is not None:
                    self.wf_t[ch], self.wf_v[ch] = waveforms[ch]

            self.poll_count += 1

            # save raw waveform
            if self.recording and self.waveforms_dir:
                save_dict = {"elapsed_s": np.array(t_now)}
                for ch in (1, 2, 3):
                    if waveforms.get(ch) is not None:
                        t_arr, v_arr = waveforms[ch]
                        save_dict[f"t{ch}"] = t_arr
                        save_dict[f"v{ch}"] = v_arr
                npz_path = os.path.join(self.waveforms_dir,
                                        f"capture_{self.capture_num:06d}.npz")
                np.savez_compressed(npz_path, **save_dict)
                self.capture_num += 1

            self.root.after(0, self._update_plot)

    def _update_plot(self):
        for ch in (1, 2, 3):
            t, v = self.wf_t[ch], self.wf_v[ch]
            if t is not None and v is not None:
                self.wf_lines[ch].set_data(t, v)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

        elapsed = time.time() - self.t0 if self.t0 else 0
        rate = self.poll_count / max(elapsed, 0.01)
        rec_tag = f"  ● REC ({self.capture_num} captures)" if self.recording else ""
        self._set_status(f"Captures: {self.poll_count}   Rate: {rate:.2f}/s   Elapsed: {elapsed:.0f}s{rec_tag}")

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
        time.sleep(0.5)   # let poll loop exit cleanly before touching serial
        if self.recording:
            self._toggle_record()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_record.config(state=tk.DISABLED)
        self._set_status("Stopped")

    def _toggle_record(self):
        if not self.recording:
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", self.run_label.get().strip()) or "run"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            run_dir = os.path.join(OUTPUT_DIR, f"{ts}_{slug}")
            self.frames_dir = os.path.join(run_dir, "frames")
            self.waveforms_dir = os.path.join(run_dir, "waveforms")
            os.makedirs(self.frames_dir, exist_ok=True)
            os.makedirs(self.waveforms_dir, exist_ok=True)

            self.capture_num = 0
            self.recording = True
            self.btn_record.config(text="■ Stop Rec")
            self._set_status(f"Recording → {run_dir}/")
            print(f"[REC] → {run_dir}/")

            threading.Thread(target=self._png_save_loop, daemon=True).start()
        else:
            self.recording = False
            self.frames_dir = None
            self.waveforms_dir = None
            self.btn_record.config(text="● Record")
            print(f"[REC] Stopped — {self.capture_num} captures saved")

    def _set_status(self, msg):
        self.status_var.set(msg)

    def _on_close(self):
        self.running = False
        self.recording = False
        time.sleep(0.5)   # let threads exit
        if self.scope and self.scope.is_open:
            try:
                self.scope.write(b":RUN\n")
            except Exception:
                pass
            self.scope.close()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.cam_win.destroy()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("950x520")
    app = ScopeMonitor(root)
    root.mainloop()