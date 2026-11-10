"""Build the gate's expected map from the committed ``pin-net-map.csv``.

The parity gate takes a JSON expected map. The board directory already carries
one authoritative connectivity table — ``pin-net-map.csv``, the same file
``verify_exports.py`` grades the S-expression export against — so deriving the
JSON from it removes a second, hand-maintained copy that could drift.

Refusing to guess is the point: a CSV with a duplicate ``(ref, pin)`` or an
empty ``net`` is a ``ValueError``, which the caller surfaces as ``NOT RUN``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REQUIRED_COLUMNS = ("ref", "pin", "net")


class PinMapError(ValueError):
    """The CSV is not usable as an expected map."""


def from_pin_net_map(csv_path, out_path):
    """Write an expected map to ``out_path`` and return its Path."""
    csv_path = Path(csv_path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, strict=True)
        if reader.fieldnames is None:
            raise PinMapError("%s: no header row" % csv_path.name)
        missing = [name for name in REQUIRED_COLUMNS if name not in reader.fieldnames]
        if missing:
            raise PinMapError("%s: missing column(s) %s" % (csv_path.name, ", ".join(missing)))
        nets = {}
        seen = {}
        for lineno, row in enumerate(reader, start=2):
            ref, pin, net = (row.get("ref") or "").strip(), (row.get("pin") or "").strip(), \
                            (row.get("net") or "").strip()
            if not ref or not pin or not net:
                raise PinMapError("%s line %d: empty ref/pin/net" % (csv_path.name, lineno))
            key = (ref, pin)
            if key in seen:
                raise PinMapError(
                    "%s line %d: duplicate endpoint %s.%s (first on line %d)"
                    % (csv_path.name, lineno, ref, pin, seen[key]))
            seen[key] = lineno
            nets.setdefault(net, []).append([ref, pin])

    if not nets:
        raise PinMapError("%s: no endpoints" % csv_path.name)

    payload = {"nets": {name: sorted(rows) for name, rows in sorted(nets.items())}}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n")
    return out_path
