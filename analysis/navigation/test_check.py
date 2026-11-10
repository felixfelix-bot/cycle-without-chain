"""Design arithmetic / pin reservation tests; not firmware or electrical proof."""
import unittest
from pathlib import Path
import importlib.util

class DesignTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('check.py')
        self.assertTrue(path.exists(), 'navigation checker not implemented')
        spec = importlib.util.spec_from_file_location('check', path)
        assert spec is not None and spec.loader is not None
        self.c = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.c)

    def test_free_pins_against_export(self):
        self.assertEqual(self.c.conflicts(self.c.netlist_pins(), self.c.RESERVED), [])

    def test_collision_and_pending_fsr_detected(self):
        self.assertEqual(self.c.conflicts({'52': 'OTHER'}, {'52': 'SPI2_SCK'}), ['52'])
        self.assertEqual(self.c.conflicts({}, {'4': 'NAV'}), ['4'])

    def test_netlist_parser_finds_motor_and_swd(self):
        pins = self.c.netlist_pins()
        self.assertIn('27', pins)
        self.assertIn('76', pins)
        self.assertNotIn('52', pins)

    def test_power_and_duration_units(self):
        self.assertAlmostEqual(self.c.energy_wh(3.3, 12.3532, 1), .04076556)
        self.assertAlmostEqual(self.c.energy_wh(3.3, 12.3532, 2), .08153112)
        self.assertAlmostEqual(self.c.energy_wh(3.3, 0, 1), 0)
        with self.assertRaises(ValueError): self.c.energy_wh(3.3, -1, 1)

    def test_bus_and_log_units(self):
        self.assertAlmostEqual(self.c.spi_us(16, 4_000_000), 32)
        self.assertEqual(self.c.log_bytes_per_second(), 15112)
        capacity = self.c.uart_8n1_capacity(115200)
        self.assertEqual(capacity, 11520)
        self.assertLess(1000, capacity)  # GNSS only fits.
        self.assertGreater(self.c.log_bytes_per_second(), capacity)
        self.assertAlmostEqual(1000 / capacity * 100, 8.6805555556)
        self.assertAlmostEqual(65536 / 15112, 4.336685, places=5)
        self.assertEqual(15112 * 3600, 54403200)
        with self.assertRaises(ValueError): self.c.uart_8n1_capacity(0)
        with self.assertRaises(ValueError): self.c.spi_us(16, 0)

if __name__ == '__main__': unittest.main()
