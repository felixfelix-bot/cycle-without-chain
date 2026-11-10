"""Shared plumbing for the fail-closed gates.

Everything here is deliberately boring and explicit:

* a *check* is a named boolean with a detail string; a gate passes only when
  every check it recorded is true and it recorded at least one;
* the JSON verdict goes to stdout and nothing else does, so a caller can
  ``json.loads(stdout)`` without stripping log noise;
* human-readable reasons go to stderr;
* exit 0 is PASS, exit 1 is FAIL (the artifact was graded and failed), exit 2
  is NOT RUN (the gate could not even grade anything).

No ``assert`` is used anywhere in this package: the suite is run under
``python3 -O`` as well, where assertions vanish.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
import uuid
from pathlib import Path

PASS = 0
FAIL = 1
NOT_RUN = 2

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_NOT_RUN = "NOT RUN"


class UsageError(Exception):
    """Bad invocation: wrong argument count, unknown option, bad value."""


class StrictParser(argparse.ArgumentParser):
    """An ArgumentParser that raises instead of calling sys.exit.

    The default behaviour prints a usage line and exits 2, which would lose
    the JSON verdict, so every error path is turned into ``UsageError``.
    ``allow_abbrev=False`` stops ``--net`` from silently meaning ``--netlist``.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)
        kwargs.setdefault("add_help", True)
        super().__init__(*args, **kwargs)

    def error(self, message):  # noqa: D401 - argparse hook
        raise UsageError(message)

    def exit(self, status=0, message=None):  # pragma: no cover - help path only
        if status:
            raise UsageError(message or "argument parsing failed")
        raise SystemExit(0)


class Checks:
    """Ordered collection of named pass/fail checks."""

    def __init__(self):
        self._items = []

    def add(self, name, ok, detail=""):
        self._items.append({"name": name, "ok": bool(ok), "detail": str(detail)})
        return bool(ok)

    def require(self, name, ok, detail=""):
        return self.add(name, ok, detail)

    def as_list(self):
        return list(self._items)

    def failed(self):
        return [item["name"] for item in self._items if not item["ok"]]

    def all_ok(self):
        return bool(self._items) and all(item["ok"] for item in self._items)


def sha256_file(path, chunk=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def is_readable_file(path):
    path = Path(path)
    if not path.exists():
        return False, "missing input: %s" % path
    if not path.is_file():
        return False, "not a regular file: %s" % path
    if not os.access(str(path), os.R_OK):
        return False, "unreadable input (permission denied): %s" % path
    try:
        with open(path, "rb") as handle:
            handle.read(1)
    except OSError as exc:
        return False, "unreadable input (%s): %s" % (exc.strerror or exc, path)
    return True, ""


def emit(payload, human_lines=()):
    """Print the single JSON verdict on stdout, human detail on stderr."""
    for line in human_lines:
        print(line, file=sys.stderr)
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stdout.flush()


def new_run_dir(root):
    """Create a fresh, collision-proof directory for one gate run.

    ``exist_ok=False`` means a re-run can never inherit an earlier run's
    report: the new directory either does not exist yet or the call fails.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(8):
        stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        run_id = "%s-%d-%s" % (stamp, os.getpid(), uuid.uuid4().hex[:10])
        candidate = root / run_id
        try:
            candidate.mkdir(parents=False, exist_ok=False)
        except FileExistsError:  # pragma: no cover - astronomically unlikely
            continue
        return candidate
    raise RuntimeError("could not allocate a unique run directory under %s" % root)


def not_run(gate, reason, exit_code=NOT_RUN, extra=None):
    payload = {
        "gate": gate,
        "verdict": VERDICT_NOT_RUN,
        "exit_code": exit_code,
        "checks": [],
        "reason": str(reason),
    }
    if extra:
        payload.update(extra)
    emit(payload, ["%s: NOT RUN: %s" % (gate, reason)])
    return exit_code


def finish(gate, checks, evidence=None, findings=None, human_lines=(), extras=None):
    verdict = VERDICT_PASS if checks.all_ok() else VERDICT_FAIL
    exit_code = PASS if verdict == VERDICT_PASS else FAIL
    payload = {
        "gate": gate,
        "verdict": verdict,
        "exit_code": exit_code,
        "checks": checks.as_list(),
        "evidence": evidence or {},
    }
    if findings is not None:
        payload["findings"] = findings
    if extras:
        payload.update(extras)
    reason_lines = list(human_lines)
    if verdict == VERDICT_FAIL:
        reason_lines.insert(0, "%s: FAIL (%s)" % (gate, ", ".join(checks.failed())))
    else:
        reason_lines.insert(0, "%s: PASS" % gate)
    emit(payload, reason_lines)
    return exit_code


def guard(gate, body, argv=None):
    """Run ``body(argv)`` translating usage errors into NOT RUN.

    Any unexpected exception is a NOT RUN with the traceback on stderr: a
    checker that crashes must never look like a checker that approved.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        return body(argv)
    except UsageError as exc:
        return not_run(gate, "usage: %s" % exc)
    except SystemExit as exc:  # --help
        return int(exc.code or 0)
    except Exception:  # noqa: BLE001 - deliberately broad, fail closed
        traceback.print_exc()
        return not_run(gate, "unhandled exception while grading (see stderr)")


def require_inputs(gate, **paths):
    for label, value in paths.items():
        if value is None:
            raise UsageError("missing required argument for %s" % label)
        ok, why = is_readable_file(value)
        if not ok:
            raise UsageError(why)
