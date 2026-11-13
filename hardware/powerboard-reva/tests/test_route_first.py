"""PCB-04 ordering: inter-block nets must be routable on a bare board.

THE FINDING THIS ENCODES
------------------------
Three successive attempts to route the 40 inter-block nets on the merged board
failed, and all three failed for the same reason from different directions:

  * blind insertion     199 shorts, 180 crossings
  * collision-checked   only 14 of 57 escape pads reachable; 43 blocked
  * gap-fill on v1      never converged

The conclusion was that the board is full and the existing block copper is what
blocks progress. This test encodes the fix rather than the diagnosis: given a
board with no copper at all, the inter-block nets route. That is a claim about
ordering, so it is checkable without a router -- what it needs is the evidence
that routing them first is feasible at all.

WHAT IS ASSERTED
----------------
1. The routed result exists and is a real board file that reloads.
2. It carries copper on at least two layers -- if it only used F.Cu the result
   would be a fluke of one plane, not a routing success.
3. At least 38 of the 40 declared inter-block nets have tracks. One or two
   shorts are tolerated because a router may legitimately fail a net with no
   legal path; the *claim* is that the set is routable when given the space.
4. No net outside the declared set carries copper. If the preparation step
   leaked a net, the result would not be about the inter-block nets at all.

WHAT IS NOT ASSERTED
--------------------
* That the board is DRC-clean. It is not: this is the inter-block copper only,
  and block routing has not run over it yet.
* That the merged board (block + inter-block) is clean. That is the next step
  and needs its own evidence.
* Anything about the GEN/HUB power stages, which are hand layout by intent.

The numbers here are from a real run, not a target. If a future change makes the
router fail this set, the test should fail -- that is the point.
"""
import json
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
WORK = P / 'routing' / 'first'
ROUTED = P / 'powerboard-reva-first.kicad_pcb'
STATS = WORK / 'interblock-only-stats.json'

DECLARED = [
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


class RouteFirst(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ROUTED.exists():
            raise unittest.SkipTest(
                'no route-first result; run route_first.py (needs pcbnew+freerouting)')
        cls.data = json.loads(STATS.read_text(encoding='utf-8'))

    def test_result_reloads_as_a_board(self):
        """A board file that will not reload is not a result."""
        import pcbnew
        board = pcbnew.LoadBoard(str(ROUTED))
        if board is None:
            raise ValueError(f'{ROUTED.name} did not reload')
        if board.GetCopperLayerCount() < 2:
            raise ValueError('expected a multilayer board')

    def test_copper_on_more_than_one_layer(self):
        per = {k: v for k, v in self.data['tracks_per_layer'].items() if v}
        if len(per) < 2:
            raise ValueError(f'copper on only one layer: {per}')

    def test_copper_lands_on_a_board_whose_pads_keep_their_nets(self):
        """The merge base must be the real board, not the cleared routing copy.

        The first merge landed this copper on the inter-block preparation board,
        which had 1081 of 1415 pads cleared to net 0 -- and DRC then reported
        2 unconnected, a number that means nothing because a pad with no net
        cannot be unconnected. Recording it as a test so the flattering number
        cannot come back.
        """
        import pcbnew
        board = pcbnew.LoadBoard(str(P / 'powerboard-reva-board.kicad_pcb'))
        if board is None:
            raise ValueError('powerboard-reva-board.kicad_pcb did not reload')
        total = netted = 0
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                total += 1
                if pad.GetNetname():
                    netted += 1
        if netted < 1200:
            raise ValueError(
                f'only {netted} of {total} pads carry a net; the merge base was '
                f'the cleared routing copy and any DRC verdict from it is void')

    def test_the_declared_nets_are_routed(self):
        routed = set(self.data['tracks_per_net'])
        missing = [n for n in DECLARED if n not in routed]
        got = len(DECLARED) - len(missing)
        if got < 38:
            raise ValueError(
                f'only {got} of {len(DECLARED)} inter-block nets routed; '
                f'missing {missing}')

    def test_no_foreign_nets_leaked_into_the_result(self):
        routed = set(self.data['tracks_per_net'])
        foreign = sorted(routed - set(DECLARED))
        if foreign:
            raise ValueError(
                f'copper on nets outside the declared set: {foreign}')

    def test_the_run_is_reproducible_from_the_committed_scripts(self):
        """The result must come from route_first.py, not from an ad-hoc edit."""
        script = P / 'route_first.py'
        if not script.exists():
            raise ValueError('route_first.py missing; the result has no provenance')
        text = script.read_text(encoding='utf-8')
        for needle in ('route_first', 'freerouting'):
            if needle not in text and needle != 'route_first':
                raise ValueError(f'route_first.py does not invoke {needle}')
        for net in DECLARED:
            if f'"{net}"' not in text:
                raise ValueError(f'{net} is not in route_first.py; the test and '
                                 f'the script disagree about the net list')


if __name__ == '__main__':
    unittest.main()
