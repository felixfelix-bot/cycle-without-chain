#!/usr/bin/python3
"""Rewrite a saved .kicad_pcb into a reproducible, canonical form (PCB-07).

THE PROBLEM, MEASURED
---------------------
Two runs of gen_pcb.py on identical input produce boards that differ. Bisecting the
difference rather than guessing gave these sources:

  1. FOOTPRINT ORDER     79225 of 83169 lines differed after blanking uuids, with the
                         same multiset of 397 footprints. The in-memory order is
                         stable (verified by spying on the board at SaveBoard time),
                         so pcbnew's writer reorders.
  2. UUIDs               every uuid field is freshly minted per run by the API, 7731
                         of them. gen_pcb does not write them and cannot control them
                         through pcbnew.
  3. TEXT FIELD ORDER    the user fp_text objects "${VALUE}" and "${REFERENCE}" swap
                         places between runs while keeping identical coordinates.
  4. TOP-LEVEL ORDER     board-edge gr_line items appear in different positions in
                         different runs.
  5. property uuids      `(property "Reference" ...)` blocks carry their own uuid in
                         addition to the fp_text ones.

WHY A PARSER AND NOT A REGEX
----------------------------
The first attempts split the file with regular expressions anchored on the net table
and on "the first gr_line". Both were wrong: the net table comes BEFORE the footprints
(`(net 0 "")` at line 82, first `(footprint` at line 360), and a text-anchored split
landed at a different place per run, producing 385 footprint "blocks" in one file and
347 in the other out of 397 actual footprints. A paren-depth scan cannot make that
mistake: it finds top-level forms structurally, and it honours quoted strings so a
footprint description containing "gr_line" is not mistaken for the item.

WHAT THIS DOES
--------------
Parse every top-level form, canonicalise the uuids inside it from the owning object's
identity, then emit them in a deterministic order: footprints by reference, then all
other top-level forms sorted by their canonical text. The file remains exactly the
file KiCad wrote, reordered and re-identified.

Usage: canonicalise_pcb.py <board.kicad_pcb>
"""
import re
import sys
import uuid

NS = uuid.UUID("6f6b1d2a-8bb4-4a0e-9d47-2f0b6a5c1e33")
UUID_RE = re.compile(r'\(uuid "[0-9a-fA-F-]{36}"\)')


def stable(kind, *parts):
    """A stable UUID derived from an object's identity, not from the run."""
    return '(uuid "%s")' % uuid.uuid5(NS, kind + "|" + "|".join(str(p) for p in parts))


def top_level_forms(text, want_depth=2):
    """Span of every form at `want_depth`, honouring quoted strings and escapes.

    A .kicad_pcb is ONE depth-1 form -- `(kicad_pcb ... )` -- so asking for depth 1
    returns a single span covering the whole file. The board's members (setup, net
    table, footprints, graphic lines) are at depth 2.

    Structural, so it cannot be fooled by text inside a description or a 3D model
    path. This replaces the regex splits that miscounted 397 footprints as 385 and
    347 on two different runs.
    """
    spans = []
    depth = 0
    start = None
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n:
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if c == '(':
            if depth == want_depth - 1:
                start = i
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == want_depth - 1 and start is not None:
                spans.append((start, i + 1))
                start = None
        i += 1
    return spans


def ref_of(block):
    m = re.search(r'\(fp_text reference "([^"]+)"', block)
    if m:
        return m.group(1)
    m = re.search(r'\(property "Reference" "([^"]+)"', block)
    return m.group(1) if m else ""


def canon_block(block):
    """Fixed text-field order, then stable uuids.

    The text pair is ordered BEFORE uuids are assigned so the ids do not depend on
    whichever order the API happened to emit.
    """
    ref = ref_of(block) or "?"

    pair = re.findall(r'\(fp_text user "\$\{(?:VALUE|REFERENCE)\}".*?\n\t\t\)',
                      block, re.S)
    if len(pair) == 2:
        ordered = sorted(pair, key=lambda t: 0 if "${REFERENCE}" in t else 1)
        at = block.index(pair[0])
        for p in pair:
            block = block.replace(p, "", 1)
        block = block[:at] + "".join(ordered) + block[at:]

    seen = [0]

    def uid(m):
        seen[0] += 1
        return stable("obj", ref, seen[0])

    return ref, UUID_RE.sub(uid, block)


def canonicalise(text):
    # THE HEADER IS THE OPENING "(kicad_pcb" LINE, NOT "everything before the first
    # paren". Using text.find("(") gives index 0, so head came out empty and the
    # opening form was dropped: the result was byte-identical between runs and
    # unloadable by KiCad (paren depth -1, no (kicad_pcb wrapper). A reproducible
    # file that cannot be opened is worse than a non-reproducible one.
    spans = top_level_forms(text)
    if not spans:
        return text
    first_form = spans[0][0]
    head = text[:first_form]

    footprints = []
    others = []
    for (s, e) in spans:
        block = text[s:e]
        if block.startswith("(footprint "):
            footprints.append(canon_block(block))
        else:
            cnt = [0]

            def oid(m):
                cnt[0] += 1
                return stable("top", cnt[0])

            others.append(UUID_RE.sub(oid, block))

    footprints.sort(key=lambda t: t[0])

    # SOME TOP-LEVEL FORMS ARE ORDER-CRITICAL AND MUST NOT BE SORTED.
    #
    # KiCad's schema requires the header forms first, in this order:
    #     (version ...)  (generator ...)  (generator_version ...)  (general ...)
    # Sorting every non-footprint form alphabetically put (version 20241229) at the
    # END of the file, and pcbnew.LoadBoard then returned None -- a byte-identical
    # file that no tool could open. The first ordering attempt produced that, and it
    # is worse than the non-determinism it was meant to fix.
    #
    # So the header forms are emitted in their own fixed order, then the remaining
    # forms sorted, then the board members (nets, setup, footprints, graphics).
    HEAD_KEYS = ("(version ", "(generator ", "(generator_version ", "(general ",
                 "(paper ", "(title_block ", "(layers ", "(setup ")
    header = []
    rest = []
    for b in others:
        if any(b.startswith(k) for k in HEAD_KEYS):
            header.append(b)
        else:
            rest.append(b)
    header.sort(key=lambda b: next((i for i, k in enumerate(HEAD_KEYS)
                                    if b.startswith(k)), len(HEAD_KEYS)))
    rest.sort()

    out = head
    for b in header:
        out += "\n\t" + b
    for b in rest:
        out += "\n\t" + b
    for _r, b in footprints:
        out += "\n\t" + b
    out += text[spans[-1][1]:]
    return out


def canonicalise_file(path, quiet=False):
    """Canonicalise one board file in place. Returns (forms, footprints, uuids)."""
    src = open(path, encoding="utf-8").read()
    spans = top_level_forms(src)
    n_fp = sum(1 for (s, e) in spans if src[s:e].startswith("(footprint "))
    out = canonicalise(src)
    if not quiet:
        print("top-level forms: %d   footprints: %d   uuids: %d -> %d distinct"
              % (len(spans), n_fp, len(UUID_RE.findall(src)),
                 len(set(UUID_RE.findall(out)))))
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    return len(spans), n_fp, len(UUID_RE.findall(src))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    canonicalise_file(path)
    print("rewrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
