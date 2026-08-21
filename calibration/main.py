# -*- coding: utf-8 -*-
"""
gds1054b_grab.py

Pulls a waveform off a GW Instek GDS-1054B over USB and plots/saves it.

The scope's rear USB port enumerates as a USB CDC virtual COM port (NOT
USBTMC), so this just talks plain ASCII SCPI-style commands over a normal
serial connection -- no PyVISA needed, just pyserial.

Prerequisite on the scope: Utility -> I/O -> USB Device Port -> "Computer"
(not the default printer/PictBridge mode), then connect the USB cable to
the rear DEVICE port (Type B).

Install once: pip install pyserial numpy matplotlib

Written to run either as a plain script, or cell-by-cell in Spyder
(the "# %%" markers below are Spyder/IPython cell delimiters -- put the
cursor in a cell and hit Ctrl+Enter to run just that block).
"""

# %% Imports
import re
import time
import datetime
import serial
import serial.tools.list_ports
import numpy as np
import matplotlib.pyplot as plt

# %% Step 1: find the right port
# Run this cell, plug/unplug the scope's USB cable, and see which entry
# appears/disappears -- that's your port. On Windows it'll look like
# "COM5"; on Linux, usually "/dev/ttyACM0"; on macOS, "/dev/tty.usbmodemXXXX".
for p in serial.tools.list_ports.comports():
    print(f"{p.device:15s} {p.description}")

# %% Step 2: connect
SCOPE_PORT = "COM6"     # <-- change this to whatever showed up above
BAUD_RATE = 115200      # CDC virtual port largely ignores this, but pyserial needs a value

if "ser" in globals() and ser.is_open:
    print(f"Reusing existing open connection on {ser.port}")
else:
    ser = serial.Serial(SCOPE_PORT, BAUD_RATE, timeout=2)
    time.sleep(0.5)  # let the port settle


def scpi_write(cmd: str):
    """Send a command/query, no response read."""
    ser.write((cmd.strip() + "\n").encode("ascii"))


def scpi_read_line(timeout=2.0) -> str:
    """Read a single short ASCII response line (for simple queries)."""
    ser.timeout = timeout
    line = ser.readline().decode("ascii", errors="ignore").strip()
    return line


def scpi_query(cmd: str, timeout=2.0) -> str:
    ser.reset_input_buffer()   # drop any stale/unread response so answers can't desync
    scpi_write(cmd)
    return scpi_read_line(timeout=timeout)


# Sanity check -- should print something like "GW,GDS-1054B,PXXXXXXX,V1.XX"
print(scpi_query("*IDN?"))

# %% Step 3: continuous-poll helper (no triggering -- just watches the channel)
def _read_exact(n_bytes: int, idle_timeout=10.0) -> bytes:
    """
    Block until exactly n_bytes have been read from the serial port.

    The timeout is an IDLE timeout, not a total one: it resets every time
    bytes arrive, so a slow multi-MB transfer (e.g. 1M points = 2MB, which
    takes well over a minute over CDC serial) won't be killed partway just
    for being large. It only gives up if the scope actually goes silent.
    """
    buf = bytearray()
    last_progress = time.time()
    while len(buf) < n_bytes:
        chunk = ser.read(n_bytes - len(buf))
        if chunk:
            buf.extend(chunk)
            last_progress = time.time()          # made progress -- reset the clock
        elif time.time() - last_progress > idle_timeout:
            raise TimeoutError(
                f"Scope went silent after {len(buf)}/{n_bytes} bytes "
                f"({100*len(buf)/n_bytes:.1f}%)"
            )
    return bytes(buf)


def poll_voltage(channel: int = 1, duration_s: float = 8.0, record_length: int = 10_000):
    """
    Watches ONE channel in free-running (Auto trigger) real-time mode for
    duration_s seconds, then freezes and reads back the capture.

    Returns (t, v, meta): t starts at 0 (seconds since the poll began),
    v is volts, meta is the scope's reported acquisition settings.
    """
    scpi_write(":HEADer ON")
    time.sleep(0.1)
    scpi_write(":TRIGger:MODe AUTO")                 # free-runs regardless of any trigger condition
    time.sleep(0.1)
    scpi_write(":ACQuire:MODe SAMPle")                # plain real-time sampling, not averaging/peak-detect
    time.sleep(0.1)
    scpi_write(f":ACQuire:RECOrdlength {record_length}")
    time.sleep(0.1)
    scpi_write(f":CHANnel{channel}:DISPlay ON")
    time.sleep(0.1)

    # Scope timebases only exist in 1-2-5 steps (0.5, 1, 2, 5 s/div, ...).
    # An off-step value like 0.8 gets silently REJECTED (not rounded), which
    # is why the 8s request was leaving the scope stuck at its old setting.
    # Snap UP to the nearest valid step so the window is at least duration_s.
    needed = duration_s / 10
    exponent = np.floor(np.log10(needed))
    for mant in (1, 2, 5, 10):
        tb_scale = mant * 10.0 ** exponent
        if tb_scale >= needed * 0.999:
            break
    scpi_write(f":TIMebase:SCALe {tb_scale:.1e}")
    time.sleep(0.1)

    # Read back what the scope actually confirms -- don't just trust the
    # value we asked for.
    try:
        actual_scale = float(scpi_query(":TIMebase:SCALe?"))
    except ValueError:
        actual_scale = tb_scale
    actual_window = actual_scale * 10
    print(f"Timebase confirmed: {actual_scale:.4g} s/div -> ~{actual_window:.4g} s window "
          f"(requested {duration_s:.4g} s)")

    scpi_write(":RUN")
    time.sleep(actual_window + 1.0)   # wait for the CONFIRMED window, not just the requested one
    scpi_write(":STOP")            # freeze so the read-back is a clean, static snapshot
    time.sleep(0.3)                # let the scope actually finish settling before we query it

    v, meta = _read_channel_memory(channel, record_length)
    sample_period = _sample_period_from_meta(meta, actual_window, record_length)
    t = np.arange(len(v)) * sample_period   # t=0 at the start of the poll
    print(f"CH{channel}: {len(v)} points read")

    return t, v, meta


def _sample_period_from_meta(meta, window_s, record_length):
    """Pull a finite sampling period out of a channel's meta, with fallback."""
    try:
        sp = float(meta.get("Sampling Period", "nan"))
    except ValueError:
        sp = float("nan")
    if not np.isfinite(sp):
        # defensive fallback: compute from the confirmed window instead of
        # trusting a possibly-invalid reported value (ET-mode reports 'inf')
        sp = window_s / record_length
    return sp


def _read_channel_memory(channel: int, record_length: int):
    """Reads one channel's stored waveform from the (already stopped) scope."""
    scpi_write(f":ACQuire{channel}:MEMory?")

    # --- read until we find the '#' that starts the binary block ---
    buf = bytearray()
    last_progress = time.time()
    while b"#" not in buf:
        chunk = ser.read(4096)
        if chunk:
            buf.extend(chunk)
            last_progress = time.time()
        elif time.time() - last_progress > 10.0:
            raise TimeoutError("No '#' block header seen -- check the scope is in Computer USB mode")

    hash_idx = buf.index(b"#")
    while len(buf) < hash_idx + 2:
        buf.extend(_read_exact(1))
    n_len_digits = int(buf[hash_idx + 1: hash_idx + 2])

    header_end = hash_idx + 2 + n_len_digits
    while len(buf) < header_end:
        buf.extend(_read_exact(header_end - len(buf)))
    n_data_bytes = int(buf[hash_idx + 2: header_end])

    total_needed = header_end + n_data_bytes
    if len(buf) < total_needed:
        remaining = total_needed - len(buf)
        if n_data_bytes > 200_000:   # big transfer -- say something so it doesn't look hung
            print(f"  reading {n_data_bytes/1e6:.2f} MB from CH{channel} "
                  f"(this takes a while at high record lengths)...")
        buf.extend(_read_exact(remaining))

    preamble = buf[:hash_idx].decode("ascii", errors="ignore")
    raw_bytes = bytes(buf[header_end:total_needed])
    ser.reset_input_buffer()   # discard the trailing terminator after the block,
                               # so it can't desync the next query one-behind

    def field(name, cast=float, default=None):
        m = re.search(name + r",([^;]+);", preamble)
        return cast(m.group(1)) if m else default

    vscale = field("Vertical Scale", float, 1.0)

    raw = np.frombuffer(raw_bytes, dtype=">i2").astype(np.float64)
    v = (raw / 25.0) * vscale

    meta = dict(re.findall(r"([^,;]+),([^;]+);", preamble))
    return v, meta


# %% Step 4: name this run, then poll a single channel and plot it
# Describe what you're actually measuring -- spaces and dashes are fine,
# they get cleaned up for the filename but kept intact for the plot title.
LABEL = "al tube - sig"     # e.g. "ring - noise", "cup - drop", "tube - baseline"
CHANNEL = 1

t, v, meta = poll_voltage(channel=CHANNEL, duration_s=2.0, record_length=1_000_000)

plt.figure(figsize=(9, 4))
plt.plot(t, v, linewidth=1)
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.title(f"{LABEL}  (CH{CHANNEL})")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

print(f"{len(v)} points, vscale = {meta.get('Vertical Scale')} V/div")

# %% Step 5: save to CSV, named with the label + timestamp
def slugify(text: str) -> str:
    """'ring - noise' -> 'ring-noise'  (safe for filenames, still readable)"""
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", s)


out_path = (f"gds1054b_{slugify(LABEL)}_ch{CHANNEL}"
            f"_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv")
np.savetxt(out_path, np.column_stack([t, v]), delimiter=",",
           header="time_s,voltage_v", comments="")
print(f"Saved {out_path}")

# %% Step 6: resume live acquisition on the scope, and release the port
scpi_write(":RUN")
ser.close()   # MUST stay uncommented -- Windows holds COM6 exclusively, so
              # leaving it open makes the next run fail with PermissionError(13)