#!/usr/bin/env python3
"""Render the blended-efficiency figure for docs/parallel-hybrid.md.

Shows that parallel-hybrid efficiency is not a single number: it depends on the
split between rider power and motor power. Two panels -- efficiency vs. assist
level, and energy cost per km -- because the second is what the rider feels.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

GREEN = "#1f8a4c"
ORANGE = "#c2410c"
GREY = "#333333"
LIGHT = "#9ca3af"
BLUE = "#1d4ed8"
RED = "#b91c1c"

ETA_CHAIN = 0.961
ETA_BATTERY_PATH = 0.80      # motor * controller
ETA_SERIES = 0.613

RIDER_W = 150.0              # steady rider input, W at the pedals
WHEEL_W = 400.0              # total power at the road, W (moderate assist)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.5, 6.6), dpi=100)
fig.patch.set_facecolor("white")

# ------------------------------------------------------------------ panel 1
# share = fraction of WHEEL power that comes from the motor
share = np.linspace(0, 1, 400)

# Parallel: rider contributes (1-share)*wheel through chain; motor contributes
# share*wheel through battery path. Effective efficiency = wheel / total input.
# Inputs: rider mechanical (counted at the pedals) + battery electrical.
rider_needed = (1 - share) * WHEEL_W / ETA_CHAIN
battery_needed = share * WHEEL_W / ETA_BATTERY_PATH
parallel_eta = WHEEL_W / (rider_needed + battery_needed)

ax1.plot(share * 100, parallel_eta * 100, lw=3.4, color=BLUE,
         label="Parallel hybrid (blended)")
ax1.axhline(ETA_SERIES * 100, color=RED, lw=2.6, ls="--",
            label=f"Series rider-only example ({ETA_SERIES*100:.1f}%)")
ax1.axhline(ETA_CHAIN * 100, color=GREEN, lw=2.2, ls=":", alpha=0.85,
            label=f"Chain only ({ETA_CHAIN*100:.1f}%)")

# annotate the 50/50 point
half = np.interp(50, share * 100, parallel_eta * 100)
ax1.plot(50, half, "o", ms=11, color=BLUE, mec="white", mew=2.2, zorder=6)
ax1.annotate(f"50/50 split\n{half:.0f}%", xy=(50, half),
             xytext=(50, half - 22), ha="center", va="top",
             fontsize=12.5, fontweight="bold", color=BLUE,
             arrowprops=dict(arrowstyle="->", color=BLUE, lw=2))

ax1.set_xlabel("share of wheel power supplied by the motor (%)", fontsize=12)
ax1.set_ylabel("efficiency, pedals + battery to road (%)", fontsize=12)
ax1.set_title("Parallel efficiency depends on how hard you pedal",
              fontsize=14, fontweight="bold", loc="left", pad=12)
ax1.set_xlim(0, 100)
ax1.set_ylim(55, 100)
ax1.grid(alpha=0.25, lw=0.8)
ax1.set_axisbelow(True)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)
ax1.legend(fontsize=10.5, loc="lower left", framealpha=0.95)

ax1.text(97, 58.5,
         "left end = you do all the work\nright end = motor does all the work",
         fontsize=10, color=GREY, ha="right", va="bottom", style="italic")

# ------------------------------------------------------------------ panel 2
# Energy per km at 20 km/h for a 100 kg vehicle, three drive types, showing
# what the rider actually pays in battery Wh/km at each assist level.
speed_kmh = 20.0
# road load at 20 km/h: rolling + aero, tuned to ~15 Wh/km class
m = 100.0
crr = 0.008
CdA = 0.55
rho = 1.2
v = speed_kmh / 3.6
p_roll = crr * m * 9.81 * v
p_aero = 0.5 * rho * CdA * v ** 3
p_road = p_roll + p_aero

shares = np.array([0.0, 0.25, 0.50, 0.75, 1.0])

# battery Wh/km: motor supplies share of road power, through the battery path
batt_wh_km = shares * p_road / ETA_BATTERY_PATH / speed_kmh
# rider Wh/km equivalent: rider supplies the rest through the chain
rider_wh_km = (1 - shares) * p_road / ETA_CHAIN / speed_kmh

# series hybrid: ALL road power passes the serial path
series_wh_km = p_road / ETA_SERIES / speed_kmh

x = np.arange(len(shares))
w = 0.38
b1 = ax2.bar(x - w / 2, rider_wh_km, w, color=GREEN, label="your legs (Wh/km)")
b2 = ax2.bar(x + w / 2, batt_wh_km, w, color=ORANGE, label="battery (Wh/km)")
ax2.axhline(series_wh_km, color=RED, lw=2.6, ls="--",
            label=f"series rider-only ({series_wh_km:.1f} Wh/km)")

ax2.set_xticks(x)
ax2.set_xticklabels([f"{int(s*100)}%" for s in shares], fontsize=11)
ax2.set_xlabel("share of wheel power from the motor", fontsize=12)
ax2.set_ylabel("steady-state energy per km at 20 km/h (Wh)", fontsize=12)
ax2.set_title("Where the energy goes, and what the series path would cost",
              fontsize=14, fontweight="bold", loc="left", pad=12)
ax2.grid(axis="y", alpha=0.25, lw=0.8)
ax2.set_axisbelow(True)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)
ax2.legend(fontsize=10.5, loc="upper right", framealpha=0.95)

for rect, val in zip(b2, batt_wh_km):
    if val > 0.4:
        ax2.text(rect.get_x() + rect.get_width() / 2, val + 0.35,
                 f"{val:.1f}", ha="center", va="bottom", fontsize=9.5,
                 color=ORANGE, fontweight="bold")

ax2.set_ylim(0, max(series_wh_km, rider_wh_km.max() + batt_wh_km.max()) * 1.25)

fig.text(0.5, 0.008,
         "Steady state, flat, no wind, no stops -- so absolute Wh are low. What matters is the ratio:\n"
         "parallel keeps the chain for rider watts; the series reference assumes ALL input is pedal power.",
         fontsize=10.5, color=GREY, ha="center", va="bottom", style="italic",
         linespacing=1.5)

fig.tight_layout(rect=(0, 0.12, 1, 1))

from pathlib import Path
out = Path(__file__).with_name("parallel-hybrid-blend.png")
fig.savefig(out, dpi=100, facecolor="white", bbox_inches="tight", pad_inches=0.22)
print("wrote", out)
print(f"road load at 20 km/h: {p_road:.0f} W -> series total {series_wh_km:.1f} Wh/km")
for s, b in zip(shares, batt_wh_km):
    print(f"  motor share {s*100:3.0f}%: battery {b:4.1f} Wh/km, rider {p_road*(1-s)/ETA_CHAIN/speed_kmh:4.1f} Wh/km")
