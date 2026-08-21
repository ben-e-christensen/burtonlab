"""Per-pulse peak-to-peak charge from Keithley 6514 time,charge CSVs.

The charge toggles between a low plateau and a high plateau each cycle, with
slow drift on top. This measures each cycle LOCALLY -- low-plateau extreme to
the peak of the high plateau right after -- so drift cancels. Each config maps
to its -1/-2 replicate files; their per-file means are averaged together into
one reported value.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

HERE = Path(__file__).parent
C = HERE / 'kiethley'          # <-- point this at the folder holding the charge CSVs

# ============ CONFIG ============
PREFACTOR = 1e12             # C -> pC

# group -> { config_name: [replicate file stems] }
# entries with two stems are averaged together; single-stem entries are the
# ones that broke the -1/-2 convention -- adjust the lists if a pairing is wrong.
GROUPS = {
    'tube': {
        'al-tube-ball-top':      ['al-tube-ball-top-1',      'al-tube-ball-top-2'],
        'al-tube-ball-midpoint': ['al-tube-ball-midpoint-1', 'al-tube-ball-midpoint-2'],
        'al-tube-wire':          ['al-tube-wire-1',          'al-tube-wire-2'],
    },
    'cup': {
        'cup-ball':                    ['cup-ball-1', 'cup-ball-2'],
        'cup-wire-five-eighths':       ['cup-wire-five-eighths-1', 'cup-wire-five-eighths-2'],
        'cup-wire-inch-and-a-quarter': ['cup-wire-inch-and-a-quarter-1', 'cup-wire-inch-and-a-quarter-2'],
    },
    'ring': {
        'ring-black-ball':              ['ring-black-ball-1', 'ring-black-ball-2'],
        'ring-black-wire-1':             ['ring-black-wire-1'],
        'ring-black-wire-2':             ['ring-black-wire-2'],
        'ring-black-wire-3':             ['ring-black-wire-3'],
        'ring-black-wire-4':             ['ring-black-wire-4'],
        'ring-black-wire-1-ball-bottom': ['ring-black-wire-1-ball-bottom'],
        'ring-black-wire-2-ball-bottom': ['ring-black-wire-2-ball-bottom'],
        'ring-black-wire-3-ball-bottom': ['ring-black-wire-3-ball-bottom'],
        'ring-blue-ball':                ['ring-blue-ball-1', 'ring-blue-ball-2'],
        'ring-blue-wire':                ['ring-blue-wire-1', 'ring-blue-wire-2'],
        'ring-blue-wire-1-ball-bottom':  ['ring-blue-wire-1-ball-bottom'],
        'ring-blue-wire-2-ball-bottom':  ['ring-blue-wire-2-ball-bottom'],
    },
}

RESULTS_CSV = HERE / 'charge_ptp_results.csv'   # None to skip
RESULTS_PNG = HERE / 'charge_ptp_plot.png'      # None to skip
# ================================


def load_charge(path):
    df = pd.read_csv(path, names=['t', 'q'], header=0)
    return df.q.to_numpy()


def pulse_steps(q, thresh=None):
    """Per-cycle pk-to-pk: for each low plateau, (peak of following high) - (low min)."""
    if thresh is None:
        thresh = (np.percentile(q, 75) + np.percentile(q, 25)) / 2
    low = q < thresh
    steps, n, idx = [], len(q), 0
    while idx < n:
        if low[idx]:
            j = idx
            while j < n and low[j]:
                j += 1
            low_min = q[idx:j].min()
            k = j
            while k < n and not low[k]:
                k += 1
            if k > j:
                steps.append(q[j:k].max() - low_min)
            idx = k
        else:
            idx += 1
    return np.array(steps)


def file_stats(stem):
    """Return (mean pk-to-pk [pC], n_pulses) for one file, or None if missing."""
    path = C / f'{stem}.csv'
    if not path.exists():
        return None
    s = pulse_steps(load_charge(path)) * PREFACTOR
    if len(s) == 0:
        return None
    return s.mean(), len(s)


print('per-pulse peak-to-peak charge [pC], averaged across replicate files')
print('=' * 74)

rows = []
for group, configs in GROUPS.items():
    print(f'\n[{group}]')
    for config, stems in configs.items():
        results = []
        for stem in stems:
            r = file_stats(stem)
            if r is None:
                print(f'    {stem:<34}  (missing/no pulses, skipped)')
            else:
                mean_pc, n = r
                print(f'    {stem:<34} {mean_pc:7.2f} pC  (n={n})')
                results.append(mean_pc)

        if not results:
            print(f'  {config:<34}  -- no data --')
            continue

        avg = np.mean(results)
        spread = np.std(results) if len(results) > 1 else float('nan')
        tag = f'{avg:7.2f} pC' + (f'  (+/- {spread:.2f} across {len(results)} files)'
                                   if len(results) > 1 else '  (single file)')
        print(f'  {config:<34} {tag}')
        rows.append({'group': group, 'config': config, 'avg_ptp_pC': avg,
                     'spread_pC': spread, 'n_files': len(results)})

table = pd.DataFrame(rows)
if len(table) == 0:
    print('\nNo files found — check the C path.')
    raise SystemExit

if RESULTS_CSV:
    table.to_csv(RESULTS_CSV, index=False)
    print(f'\nSaved table -> {RESULTS_CSV}')

# --- bar chart, colored by group ---
colors = {'tube': 'C0', 'cup': 'C2', 'ring': 'C1'}
fig, ax = plt.subplots(figsize=(12, 5.5))
yerr = table.spread_pC.fillna(0)
ax.bar(range(len(table)), table.avg_ptp_pC, yerr=yerr, capsize=3,
       color=[colors[g] for g in table.group])
ax.set_xticks(range(len(table)))
ax.set_xticklabels(table.config, rotation=45, ha='right', fontsize=7)
ax.set_ylabel('avg per-pulse pk-to-pk charge [pC]')
ax.set_title('Charge pk-to-pk per config (averaged over replicate files)')
handles = [plt.Rectangle((0, 0), 1, 1, color=colors[g]) for g in colors]
ax.legend(handles, colors.keys())
plt.tight_layout()

if RESULTS_PNG:
    fig.savefig(RESULTS_PNG, dpi=200)
    print(f'Saved plot  -> {RESULTS_PNG}')

plt.show()