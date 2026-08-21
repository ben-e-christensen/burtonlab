"""Peak-to-peak comparison: drive Vpp vs each sensor capture's Vpp.

Handles GDS-1054B multi-channel exports, where each channel is written as a
separate side-by-side block with its OWN time column (CH1: cols 0-1,
CH2: cols 2-3, ...). One result row per channel. Saves CSV + PNG.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

HERE = Path(__file__).parent
G = HERE / 'gw'

# ============ CONFIG ============
DRIVE_VPP = 20.0        # measured drive peak-to-peak [V]

GROUPS = {
    'tube': [
        G / 'al tube - midway.CSV',
        G / 'al tube just ball.CSV',
        G / 'al tube just wire.CSV',
    ],
    'rings': [
        G / 'pmma tube ball in front of black sensor.CSV',
        G / 'pmma tube ball in front of blue sensor.CSV',
        G / 'pmma tube just wire (blue top) (2) (better).CSV',
        G / 'pmma tube just wire blue bottom.CSV',
    ],
    'cup': [
        G / 'cup ball just pass lip.CSV',
        G / 'cup ball midpoint.CSV',
        G / 'cup ball nearly touching bottom.CSV',
    ],
}

ROBUST_VPP  = True                       # percentile Vpp (rejects spikes) vs raw max-min
RESULTS_CSV = HERE / 'vpp_results.csv'   # None to skip
RESULTS_PNG = HERE / 'vpp_plot.png'      # None to skip
# ================================


def load_gds1054b(path):
    """Parse a GDS-1054B export. Returns {channel_name: (time, voltage)}.

    Multi-channel files store channels as side-by-side 2-column blocks, each
    with its own time column. Channel k -> data columns [2k, 2k+1].
    """
    channels = []
    with open(path) as f:
        for i, line in enumerate(f):
            parts = [p.strip() for p in line.rstrip('\r\n').split(',')]
            if parts and parts[0] == 'Source':
                channels = [parts[j + 1] for j, p in enumerate(parts) if p == 'Source']
            if parts and parts[0] == 'Waveform Data':
                skip = i + 1
                break

    df = pd.read_csv(path, skiprows=skip, header=None)
    df = df.dropna(axis=1, how='all')                 # drop trailing-comma column
    n = len(channels) if channels else df.shape[1] // 2
    if not channels:
        channels = [f'CH{k+1}' for k in range(n)]

    return {ch: (df.iloc[:, 2*k].to_numpy(), df.iloc[:, 2*k+1].to_numpy())
            for k, ch in enumerate(channels)}


def vpp(v):
    if ROBUST_VPP:
        return np.percentile(v, 99.9) - np.percentile(v, 0.1)
    return v.max() - v.min()


print(f'Drive: {DRIVE_VPP:.4g} Vpp  ({"robust" if ROBUST_VPP else "raw"} Vpp on sensors)')
print('=' * 72)

rows = []
for group, files in GROUPS.items():
    print(f'\n[{group}]')
    for path in files:
        chans = load_gds1054b(path)
        for ch, (t, v) in chans.items():
            val = vpp(v)
            tag = Path(path).name + (f' [{ch}]' if len(chans) > 1 else '')
            print(f'  {tag:<58} {val*1e3:8.2f} mVpp   ({val/DRIVE_VPP:.4g} V/V)')
            rows.append({'group': group, 'file': Path(path).name, 'channel': ch,
                         'drive_Vpp': DRIVE_VPP, 'sensor_Vpp': val,
                         'ratio': val / DRIVE_VPP})

table = pd.DataFrame(rows)
if RESULTS_CSV:
    table.to_csv(RESULTS_CSV, index=False)
    print(f'\nSaved table -> {RESULTS_CSV}')

# --- bar chart, colored by group ---
colors = {'tube': 'C0', 'rings': 'C1', 'cup': 'C2'}
labels = [f + (f'\n[{c}]' if (table.file == f).sum() > 1 else '')
          for f, c in zip(table.file, table.channel)]

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.bar(range(len(table)), table.sensor_Vpp * 1e3,
       color=[colors[g] for g in table.group])
ax.set_xticks(range(len(table)))
ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
ax.set_ylabel('sensor Vpp [mV]')
ax.set_title(f'Sensor Vpp  (drive = {DRIVE_VPP:.0f} Vpp)')
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
ax.legend(handles, colors.keys())
plt.tight_layout()

if RESULTS_PNG:
    fig.savefig(RESULTS_PNG, dpi=200)
    print(f'Saved plot  -> {RESULTS_PNG}')

plt.show()