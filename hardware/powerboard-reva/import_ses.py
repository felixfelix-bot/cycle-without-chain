#!/usr/bin/python3
"""Import a Specctra SES into a board and dump its tracks as JSON.

Runs in its OWN PROCESS because ImportSpecctraSES corrupts swig state for the
whole interpreter: after the call, every BOARD reference in that process becomes
a raw SwigPyObject with no methods -- including boards loaded fresh afterwards.
So the import must not happen in the same process that still needs to use a board.

Usage: import_ses.py <board.kicad_pcb> <session.ses>

Import and save only -- no track reading. The read is read_tracks.py's job, in a
separate process. The import itself succeeds and SaveBoard writes the tracks
correctly; only enumerating them afterwards in the same interpreter fails.
"""
import json
import sys

import pcbnew


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: import_ses.py <board> <ses>")
        return 2
    board_path, ses_path = sys.argv[1:3]
    board = pcbnew.LoadBoard(board_path)
    pcbnew.ImportSpecctraSES(board, ses_path)
    pcbnew.SaveBoard(board_path, board)
    # Deliberately does NOT read the tracks back. See the module docstring: the
    # read fails in this process, so read_tracks.py does it separately.
    print("imported %s" % ses_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
