"""
Plot scope monitor CSV (v6 format) — mean and std dev per channel.
Usage: python plot_scope_v6.py scope_data/20260906_XXXXXX_run.csv
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt

csv_path = sys.argv[1] if len(sys.argv) > 1 else "scope_data/latest.csv"

df = pd.read_csv(csv_path)
t = df["time_s"]

channels = {
    1: {"mean": "ch1_top_mean", "std": "ch1_top_std",
        "label": "CH1 – Top Ring", "color": "#e6b800"},
    2: {"mean": "ch2_mid_mean", "std": "ch2_mid_std",
        "label": "CH2 – Middle Ring", "color": "#00bfff"},
    3: {"mean": "ch3_bot_mean", "std": "ch3_bot_std",
        "label": "CH3 – Bottom Ring", "color": "#ff4d4d"},
}

fig, (ax_mean, ax_std) = plt.subplots(2, 1, figsize=(12, 8),
                                       facecolor="#1e1e1e", sharex=True)

for ax in (ax_mean, ax_std):
    ax.set_facecolor("#1e1e1e")
    ax.tick_params(colors="white", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#444")
    ax.grid(True, alpha=0.25, color="#555")

# Mean plot
for ch, cfg in channels.items():
    vals = pd.to_numeric(df[cfg["mean"]], errors="coerce")
    ax_mean.plot(t, vals, color=cfg["color"], linewidth=0.8, label=cfg["label"])

ax_mean.set_ylabel("Mean Voltage (V)", color="white", fontsize=10)
ax_mean.set_title(f"Mean per Capture — {csv_path}", color="white", fontsize=10)
ax_mean.legend(loc="upper right", facecolor="#2a2a2a", edgecolor="#444", labelcolor="white")
ax_mean.axhline(0, color="white", linewidth=0.3, alpha=0.5)

# Std dev plot
for ch, cfg in channels.items():
    vals = pd.to_numeric(df[cfg["std"]], errors="coerce")
    ax_std.plot(t, vals, color=cfg["color"], linewidth=0.8, label=cfg["label"])

ax_std.set_ylabel("Std Dev (V)", color="white", fontsize=10)
ax_std.set_xlabel("Time (s)", color="white", fontsize=10)
ax_std.set_title("Std Dev per Capture", color="white", fontsize=10)
ax_std.legend(loc="upper right", facecolor="#2a2a2a", edgecolor="#444", labelcolor="white")

fig.tight_layout()
out = csv_path.rsplit(".", 1)[0] + ".png"
fig.savefig(out, dpi=150, facecolor="#1e1e1e")
print(f"Saved → {out}")
plt.show()