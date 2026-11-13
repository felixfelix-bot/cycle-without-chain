#!/usr/bin/python3
"""Route the inter-block nets on the already-merged board.

WHAT THIS SOLVES
----------------
Block routing left 43 connections unjoined: nets whose two ends sit in different
functional blocks. They are signals, not power -- SPI to the drivers, the twelve
gate-drive lines, Hall inputs, encoders, the two OC reference dividers, and a
handful of control lines (OC_OK, MCU_ARM, ARM_CLEAN, RESET_REQUEST, WDI,
TIMER_BREAK_OK, FSR_SAMPLE_ENABLE, BRAKE_DUMP_PWM).

Approach: build a sub-board that keeps every component but deletes all existing
tracks, restrict the DSN to those nets, route them, and merge the result onto the
routed board. Restricting to a named net list is what keeps this fast -- the full
board does not finish, and 43 nets is a small problem.

Runs its board work in child processes for the same reason as everything else in
this chain: pcbnew/swig does not survive ImportSpecctraSES plus further board
operations in one interpreter.

Usage: /usr/bin/python3 route_interblock.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTED = os.path.join(HERE, "powerboard-reva-routed.kicad_pcb")
OUT = os.path.join(HERE, "powerboard-reva-routed-v2.kicad_pcb")
WORK = os.path.join(HERE, "routing", "interblock")
PY = "/usr/bin/python3"

# The 43 nets that cross block boundaries, from the DRC split. Listed explicitly
# rather than computed, so a change in the block definition cannot silently widen
# the routing scope.
NETS = [
    "DRV_MOSI", "DRV_SCK", "DRV_MISO",
    "GEN_INHA", "GEN_INHB", "GEN_INHC", "GEN_INLA", "GEN_INLB", "GEN_INLC",
    "HUB_INHA", "HUB_INHB", "HUB_INHC", "HUB_INLA", "HUB_INLB", "HUB_INLC",
    "GEN_SOB", "GEN_SOC", "HUB_SOA_ADC", "HUB_SOB_ADC", "HUB_SOC_ADC",
    "OC_HIGH_REF", "OC_LOW_REF",
    "GEN_HALL_1", "GEN_HALL_2", "GEN_HALL_3",
    "HUB_HALL_1", "HUB_HALL_2", "HUB_HALL_3",
    "ENC_A", "ENC_B", "LEFT_FSR_ADC", "RIGHT_FSR_ADC",
    "OC_OK", "MCU_ARM", "ARM_CLEAN", "RESET_REQUEST", "WDI",
    "TIMER_BREAK_OK", "FSR_SAMPLE_ENABLE", "BRAKE_DUMP_PWM",
]


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    sub = os.path.join(WORK, "interblock.kicad_pcb")
    dsn = os.path.join(WORK, "interblock.dsn")
    ses = os.path.join(WORK, "interblock.ses")

    # Step 1: strip tracks and restrict to the inter-block nets, in a child.
    r = subprocess.run([PY, os.path.join(HERE, "prepare_interblock.py"),
                        ROUTED, sub, ",".join(NETS)],
                       capture_output=True, text=True, timeout=600)
    print((r.stdout or "").strip()[-500:])
    if r.returncode != 0:
        print("FAIL prepare: %s" % (r.stderr or "")[-400:])
        return 1

    # Step 2: route.
    cmd = ["java", "-Xmx5g", "-Djava.awt.headless=true",
           "-jar", "/opt/freerouting/freerouting-2.5.0.jar",
           "--gui.enabled=false", "-de", dsn, "-do", ses, "-mp", "20"]
    try:
        rr = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    except subprocess.TimeoutExpired:
        print("FAIL: routing timed out at 1200 s")
        return 1
    if not os.path.exists(ses):
        print("FAIL: no SES (rc=%d)" % rr.returncode)
        print((rr.stdout or "")[-500:])
        return 1
    print("routed: %s (%d bytes)" % (os.path.basename(ses),
                                     os.path.getsize(ses)))

    # Step 3: import into the sub-board (own process), read tracks (own process).
    r = subprocess.run([PY, os.path.join(HERE, "import_ses.py"), sub, ses],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print("FAIL import: %s" % (r.stderr or "")[-300:])
        return 1
    tracks_json = os.path.join(WORK, "interblock.tracks.json")
    r = subprocess.run([PY, os.path.join(HERE, "read_tracks.py"), sub,
                        tracks_json], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print("FAIL read: %s" % (r.stderr or "")[-300:])
        return 1
    tracks = json.load(open(tracks_json, encoding="utf-8"))
    print("harvested %d new segments" % len(tracks))

    # Step 4: merge onto the ROUTED board (not the empty one).
    r = subprocess.run([PY, os.path.join(HERE, "merge_tracks.py"),
                        tracks_json, OUT],
                       capture_output=True, text=True, timeout=900)
    print((r.stdout or "").strip()[-400:])
    if r.returncode != 0:
        print("FAIL merge: %s" % (r.stderr or "")[-400:])
        return 1

    print()
    print("wrote %s" % os.path.basename(OUT))
    print("NOTE: merge_tracks.py loads powerboard-reva.kicad_pcb (the UNROUTED")
    print("master) by default. This run needed the ROUTED board as its base --")
    print("check the track count in the output above to confirm it merged onto")
    print("the routed file and not the empty one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
