"""Consistency check for ``docs/design/open-gates-register.md``.

WHAT THIS IS
------------
A linter for the open-gates register. It answers exactly one question: *is the
register complete enough to be read and counted?* A row must have a bucket in
{A, B, C, D}, a citation naming both a document and a section of it, a unique
ID, and the right number of columns; the bucket-summary table must agree with
the rows.

WHAT THIS IS NOT
----------------
This is **not** proof that the engineering is right, and it is not a release
gate. It cannot tell whether a gate has been classified into the correct
bucket, whether the cited section really raises that gate, whether a "RESOLVED"
row was honestly closed, or whether a consequence is the real one. Those are
review judgements on the document, made by a human or a reviewer reading it.
Passing this check means the register is *internally well-formed*, nothing
more. Do not cite a green run as evidence that the design is safe, legal or
manufacturable.

Contract
--------
Exit 0 PASS, exit 1 FAIL (row-level fault or count mismatch), exit 2 NOT RUN
(no register, no gate table, no summary table). No ``assert`` is used anywhere,
so normal and ``python3 -O`` execution behave identically.

Usage::

    python3 analysis/gates/register_check.py docs/design/open-gates-register.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PASS, FAIL, NOT_RUN = 0, 1, 2

BUCKETS = ("A", "B", "C", "D")

# A gate row is a pipe table row whose first cell looks like a gate ID.
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d{2}$")

# A citation must name a document *and* a section of it. Both are required: a
# filename alone cannot be checked against the source, and a section alone
# cannot be located.
DOC_RE = re.compile(r"[\w][\w./-]*\.(?:md|csv|py|json|txt)")
SECTION_RE = re.compile(r"§")

REQUIRED_COLUMNS = 8


class NotRun(Exception):
    """The document cannot be graded at all."""


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def find_tables(lines: list[str]) -> tuple[int, int]:
    """Return (gate header index, summary header index) or raise NotRun."""
    gate_header = None
    summary_header = None
    in_summary = False
    for index, line in enumerate(lines):
        lowered = line.lower()
        if lowered.startswith("## "):
            in_summary = "bucket summary" in lowered
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.lower() for cell in split_row(line)]
        if gate_header is None and cells[:2] == ["id", "subsystem"]:
            gate_header = index
        elif in_summary and summary_header is None and cells[:2] == ["bucket", "meaning"]:
            summary_header = index
    if gate_header is None:
        raise NotRun("no gate table found (no header row starting '| ID | Subsystem |')")
    if summary_header is None:
        raise NotRun("no bucket summary table found (no '| Bucket | Meaning |' header)")
    return gate_header, summary_header


def collect_rows(lines: list[str], start: int) -> list[tuple[int, list[str]]]:
    """Rows after ``start`` until the table ends."""
    rows = []
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.lstrip().startswith("|"):
            break
        cells = split_row(line)
        if set("".join(cells)) <= set("-: "):
            continue  # separator row
        if cells and cells[0].lower() == "id":
            continue
        rows.append((index + 1, cells))
    return rows


def collect_summary(lines: list[str], start: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.lstrip().startswith("|"):
            break
        cells = split_row(line)
        if len(cells) < 3 or set("".join(cells)) <= set("-: "):
            continue
        bucket = cells[0]
        if bucket not in BUCKETS:
            continue
        try:
            counts[bucket] = int(cells[2])
        except ValueError:
            raise NotRun(
                f"summary line {index + 1}: count {cells[2]!r} is not an integer"
            ) from None
    for bucket in BUCKETS:
        counts.setdefault(bucket, None)  # type: ignore[arg-type]
    return counts


def check(path: Path) -> tuple[list[str], dict[str, int]]:
    if not path.is_file():
        raise NotRun(f"register not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    gate_header, summary_header = find_tables(lines)
    rows = collect_rows(lines, gate_header)
    if not rows:
        raise NotRun("gate table has no data rows")

    problems: list[str] = []
    seen: dict[str, int] = {}
    actual = {bucket: 0 for bucket in BUCKETS}

    for lineno, cells in rows:
        label = cells[0] if cells else f"<line {lineno}>"
        if len(cells) != REQUIRED_COLUMNS:
            problems.append(
                f"line {lineno} ({label}): row has {len(cells)} columns, "
                f"expected {REQUIRED_COLUMNS}"
            )
            continue
        if not ID_RE.match(cells[0]):
            problems.append(f"line {lineno}: ID {cells[0]!r} is not of the form PREFIX-NN")
            continue
        gate_id = cells[0]
        if gate_id in seen:
            problems.append(
                f"line {lineno} ({gate_id}): duplicate ID, first seen on line "
                f"{seen[gate_id]}"
            )
        else:
            seen[gate_id] = lineno

        bucket = cells[4]
        if bucket == "":
            problems.append(f"line {lineno} ({gate_id}): empty bucket")
        elif bucket not in BUCKETS:
            problems.append(
                f"line {lineno} ({gate_id}): bucket {bucket!r} is not one of A/B/C/D"
            )
        else:
            actual[bucket] += 1

        source = cells[7]
        if not DOC_RE.search(source) or not SECTION_RE.search(source):
            problems.append(
                f"line {lineno} ({gate_id}): no citation — needs a document "
                f"(e.g. '*.md') plus a section marker '§'; got {source!r}"
            )

        # The bucket is this document's own claim about what work remains. A row
        # whose status already says closed/resolved must not keep counting as
        # open, or the remaining-work number is inflated and the reader is told
        # two different things in one line. Applies both ways: bucket D is
        # defined as resolved, so an open row there is equally wrong.
        status = cells[6].strip().upper()
        closed_status = status.startswith("CLOSED") or status.startswith("RESOLVED")
        if closed_status and bucket in ("A", "B", "C"):
            problems.append(
                f"line {lineno} ({gate_id}): status says closed/resolved but bucket is "
                f"{bucket}; move it to D or drop the claim"
            )
        elif bucket == "D" and not closed_status:
            problems.append(
                f"line {lineno} ({gate_id}): bucket D is 'resolved' but status "
                f"{cells[6].strip()[:40]!r} does not say closed/resolved"
            )

    stated = collect_summary(lines, summary_header)
    for bucket in BUCKETS:
        if stated.get(bucket) is None:
            problems.append(f"summary table has no row for bucket {bucket}")
        elif stated[bucket] != actual[bucket]:
            problems.append(
                f"summary count for bucket {bucket} is {stated[bucket]} but the "
                f"table has {actual[bucket]} rows"
            )

    return problems, actual


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: register_check.py <register.md>", file=sys.stderr)
        return NOT_RUN
    path = Path(argv[1])
    try:
        problems, actual = check(path)
    except NotRun as exc:
        print(f"NOT RUN: {exc}", file=sys.stderr)
        return NOT_RUN

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        print(f"FAIL: {len(problems)} problem(s) in {path}", file=sys.stderr)
        return FAIL

    counts = " ".join(f"{bucket}={actual[bucket]}" for bucket in BUCKETS)
    print(
        f"PASS: {path} — well-formed, cited, counts agree ({counts})",
        file=sys.stderr,
    )
    return PASS


if __name__ == "__main__":
    sys.exit(main(sys.argv))
