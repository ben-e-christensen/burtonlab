# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 13:50:41 2026

@author: burtonlabuser
"""

# -*- coding: utf-8 -*-
"""
plot_scope_csv.py

Plots a CSV that the GDS-1054B wrote directly to a USB stick (DS0001.CSV
and friends) -- no scope connection needed.

These files are NOT plain two-column CSVs. They have a ~24-line metadata
header (Memory Length, Sampling Period, Vertical Scale, etc.), then a
"Waveform Data," marker line, then time,voltage rows. Every row also ends
in a trailing comma, which naive parsers read as a third empty column.
This script handles all of that.

The time column is already in seconds and already referenced to the
trigger (negative = pre-trigger), so no conversion is needed.

Run cell-by-cell in Spyder (Ctrl+Enter), or as a plain script.
"""

# %% Imports
import os
import glob
import numpy as np
import matplotlib.pyplot as plt

# %% Step 1: point at the file
# Either name a file directly, or leave FILE = "" to grab the first
# DS*.CSV found in FOLDER.
FOLDER = os.getcwd()
FILE = r"C:\Users\burtonlabuser\Desktop\ben\al_tube_on.CSV"          # e.g. r"C:\Users\burtonlabuser\Desktop\ben\DS0001.CSV"

LABEL = ""         

if FILE:
    path = FILE
else:
    hits = sorted(glob.glob(os.path.join(FOLDER, "DS*.CSV")))
    if not hits:
        raise FileNotFoundError(
            f"No DS*.CSV found in {FOLDER}. Set FILE to the full path, "
            "or set FOLDER to where you copied the files off the USB stick."
        )
    path = hits[0]
    if len(hits) > 1:
        print(f"Found {len(hits)} files; using {os.path.basename(path)}. "
              "Set FILE to pick a different one.")

print(f"Reading {path}")


# %% Step 2: parse header + data
def read_scope_csv(path):
    """
    Returns (t, v, meta):
      t    -- time in seconds, 0 = trigger point
      v    -- volts
      meta -- dict of the header fields the scope wrote
    """
    meta = {}
    n_header = 0
    with open(path, "r") as f:
        for i, line in enumerate(f):
            parts = [p.strip() for p in line.rstrip("\r\n").split(",")]
            if parts and parts[0] == "Waveform Data":
                n_header = i + 1        # data starts on the next line
                break
            if len(parts) >= 2:
                meta[parts[0]] = parts[1]
        else:
            raise ValueError("No 'Waveform Data' marker found -- is this a scope CSV?")

    # usecols=(0,1) drops the phantom third column made by the trailing comma
    data = np.loadtxt(path, delimiter=",", skiprows=n_header, usecols=(0, 1))
    return data[:, 0], data[:, 1], meta


def pick_time_unit(t):
    """Choose s / ms / us / ns so the axis reads nicely at any timebase."""
    span = float(np.max(np.abs(t))) if len(t) else 0.0
    for scale, name in ((1.0, "s"), (1e3, "ms"), (1e6, "\u00b5s"), (1e9, "ns")):
        if span * scale >= 1.0:
            return scale, name
    return 1e9, "ns"


t, v, meta = read_scope_csv(path)

print(f"  {len(v)} points spanning {t[0]:.3e} to {t[-1]:.3e} s")
print(f"  {meta.get('Horizontal Scale')} s/div, sampling period "
      f"{meta.get('Sampling Period')} s, mode = {meta.get('SincET Mode')}")
print(f"  source = {meta.get('Source')}, {meta.get('Vertical Scale')} V/div")
print(f"  V range: {v.min():.4f} to {v.max():.4f} V")

# %% Step 3: plot
scale, unit = pick_time_unit(t)
title = LABEL or os.path.basename(path)

plt.figure(figsize=(10, 4))
plt.plot(t * scale, v, linewidth=0.6)
plt.axvline(0, color="r", linestyle="--", linewidth=0.8, label="trigger")
plt.xlabel(f"Time ({unit}, 0 = trigger)")
plt.ylabel("Voltage (V)")
plt.title(title)
plt.grid(True, alpha=0.3)
plt.legend(fontsize=8)
plt.tight_layout()

out_png = os.path.splitext(path)[0] + "_plot.png"
plt.savefig(out_png, dpi=150)   # save BEFORE show()
print(f"Saved {out_png}")

plt.show()

# %% Step 4 (optional): zoom in around the trigger
# The record can be far longer than what was on screen -- at 1M points the
# stored data covers much more time than the display window. Narrow the
# view to see the event itself.
ZOOM_S = 5e-6      # half-width around t=0, in seconds. Adjust to taste.

m = np.abs(t) <= ZOOM_S
if m.sum() > 1:
    tz, vz = t[m], v[m]
    zscale, zunit = pick_time_unit(tz)

    plt.figure(figsize=(10, 4))
    plt.plot(tz * zscale, vz, linewidth=0.8)
    plt.axvline(0, color="r", linestyle="--", linewidth=0.8, label="trigger")
    plt.xlabel(f"Time ({zunit}, 0 = trigger)")
    plt.ylabel("Voltage (V)")
    plt.title(f"{title} -- zoomed \u00b1{ZOOM_S*zscale:.3g} {zunit}")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()

    zoom_png = os.path.splitext(path)[0] + "_zoom.png"
    plt.savefig(zoom_png, dpi=150)
    print(f"Saved {zoom_png}  ({m.sum()} points)")
    plt.show()
else:
    print(f"Zoom window \u00b1{ZOOM_S} s contains too few points; widen ZOOM_S.")