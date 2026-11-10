"""Circuit contract independent of generator: verify exported endpoint assignments."""
import csv
from pathlib import Path
import unittest
import verify_exports

class RearmConnectivity(unittest.TestCase):
    def test_actual_export_matches_edge_memory_topology(self):
        root = Path(__file__).resolve().parents[1]
        verify_exports.verify(root)  # independently compares all exported endpoints
        with (root / 'pin-net-map.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        nets = {(r['ref'], r['pin']): r['net'] for r in rows}
        required = {
            'U7': ['RESET_INV','SAFETY3V3','RELEASE_N','PGND','RELEASE_SEEN','HEALTHY','SAFETY3V3','SAFETY3V3'],
            'U8': ['RESET_CLEAN','RELEASE_SEEN','FAULT_LATCH','PGND','PERMIT','HEALTHY','SAFETY3V3','SAFETY3V3'],
            'U11': ['ANALOG_OK','WD_OK','GEN_nFAULT','PGND','GEN_OK','WD_RESET_N','ANALOG_CLEAN','SAFETY3V3'],
            'U12': ['HUB_nFAULT','ARM_CLEAN','RESET_RC','PGND','RESET_CLEAN','MCU_ARM','HUB_OK','SAFETY3V3'],
            'U13': ['ANALOG_CLEAN','PGND','GEN_OK','FAULTS_OK','SAFETY3V3','HUB_OK'],
            'U14': ['FAULTS_OK','PGND','WD_OK','HEALTHY','SAFETY3V3','SAFETY3V3'],
            'U15': ['PGND','RESET_CLEAN','PGND','RESET_INV','SAFETY3V3'],
            'U16': ['HEALTHY','PGND','PERMIT','TIMER_BREAK_OK','SAFETY3V3','ARM_CLEAN'],
        }
        for ref, expected in required.items():
            for i, net in enumerate(expected, 1):
                self.assertEqual(nets[ref, str(i)], net, (ref, i))
        self.assertFalse(any(ref in {'D1','D2','D3'} for ref, pin in nets))
        for pin in ['1','13','14']:
            self.assertEqual(nets['U6',pin], 'ANALOG_OK')
