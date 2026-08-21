# -*- coding: utf-8 -*-
"""
plot_captures.py
 
Loads every gds1054b_capture_*.csv file sitting in the same folder and
plots them all together. No scope connection needed -- this just reads
whatever gds1054b_grab.py already saved to disk.
 
Run cell-by-cell in Spyder (Ctrl+Enter), or as a plain script.
"""
 
# %% Imports
import glob
import os
import numpy as np
import matplotlib.pyplot as plt
 
# %% Step 1: find every capture file
# Looks in the current working directory -- if Spyder's console cwd isn't
# where the CSVs landed, set FOLDER to the right path explicitly, e.g.
# FOLDER = r"C:\Users\burtonlabuser\Desktop\captures"
FOLDER = os.getcwd()
 
paths = sorted(glob.glob(os.path.join(FOLDER, "gds1054b_capture_*.csv")))
print(f"Found {len(paths)} capture(s) in {FOLDER}:")
for p in paths:
    print(" ", os.path.basename(p))
 
if not paths:
    raise FileNotFoundError(
        "No gds1054b_capture_*.csv files found -- check FOLDER above, "
        "or run gds1054b_grab.py first to actually capture some data."
    )
 
# %% Step 2: load and plot them all together
plt.figure(figsize=(9, 5))
 
for p in paths:
    data = np.genfromtxt(p, delimiter=",", skip_header=1)
    with open(p) as f:
        cols = f.readline().strip().split(",")   # e.g. time_s,ch1_v,ch2_v,ch3_v
    t = data[:, 0]
    base = os.path.basename(p).replace("gds1054b_capture_", "").replace(".csv", "")
    for i, colname in enumerate(cols[1:], start=1):
        chan_label = colname.replace("_v", "").upper() if colname != "voltage_v" else "CH1"
        label = f"{base} {chan_label}" if len(cols) > 2 or len(paths) > 1 else chan_label
        v = data[:, i]
        plt.plot(t, v, label=label, linewidth=1)
        print(f"{label}: {len(v)} points, {t[-1]:.2f}s span, "
              f"{v.min():.4f}V to {v.max():.4f}V")
 
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.title(f"GDS-1054B captures ({len(paths)} run{'s' if len(paths) != 1 else ''})")
plt.grid(True, alpha=0.3)
plt.legend(fontsize=8)
plt.tight_layout()
 
# %% Step 3: save the combined figure as an image (before showing it --
# show() can clear/hand off the figure on some backends, leaving a blank
# save if savefig() runs after it)
out_png = os.path.join(FOLDER, "gds1054b_captures_combined.png")
plt.savefig(out_png, dpi=150)
print(f"Saved {out_png}")
 
plt.show()
 
