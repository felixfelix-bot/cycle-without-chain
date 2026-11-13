"""Tests for the pin-name audit (PCB-02).

The value of a pin audit is entirely in whether it can fail. A check that prints
"61/61 match" and would also print that for a swapped VSSA/VDDA is worse than no
check, because it manufactures confidence. Every test below is therefore a
negative control: it mutates the datasheet table in a way a real defect would,
and asserts the audit notices.

The positive case is one test. The rest exist to prove the positive case means
something.
"""

import unittest

import audit_pin_names as a


def table():
    return a.load_table(a.DATA / "stm32g474ve-lqfp100-pins.json")


def rows():
    import csv
    return [r for r in csv.DictReader(a.PIN_MAP.open(newline="", encoding="utf-8"))
            if r["ref"] == "U17"]


class TestPositiveCase(unittest.TestCase):
    def test_every_populated_pin_matches(self):
        ok, bad = a.audit(table(), rows())
        self.assertEqual(bad, [])
        self.assertEqual(len(ok), 61)


class TestNegativeControls(unittest.TestCase):
    """Each of these is a defect that would reach fabrication undetected."""

    def test_swapped_power_pins_are_caught(self):
        t = table()
        t[35], t[37] = t[37], t[35]     # VSSA <-> VDDA
        ok, bad = a.audit(t, rows())
        pins = {b[0] for b in bad}
        self.assertEqual(pins, {35, 37})

    def test_wrong_gpio_name_is_caught(self):
        t = table()
        t[21] = "PA2"                    # schematic says PA1
        ok, bad = a.audit(t, rows())
        self.assertTrue(any(b[0] == 21 for b in bad))

    def test_missing_pin_in_table_is_caught(self):
        t = table()
        del t[99]                        # VSS
        ok, bad = a.audit(t, rows())
        self.assertTrue(any(b[0] == 99 for b in bad))

    def test_prefix_collision_is_not_accepted(self):
        """PA1 must not match PA10.

        A naive prefix comparison would let PA1 and PA10 pass as equal, which is
        exactly how an off-by-one pin assignment survives review.
        """
        self.assertFalse(a.name_matches("PA1", "PA10"))
        self.assertFalse(a.name_matches("PB1", "PB10"))
        self.assertTrue(a.name_matches("PA10", "PA10"))

    def test_function_suffix_is_accepted(self):
        self.assertTrue(a.name_matches("PF0", "PF0-OSC_IN"))
        self.assertTrue(a.name_matches("PB8", "PB8-BOOT0"))
        self.assertTrue(a.name_matches("PG10", "PG10-NRST"))

    def test_suffix_does_not_mask_a_different_pin(self):
        self.assertFalse(a.name_matches("PF1", "PF0-OSC_IN"))


class TestUnnamedPinsAreNotAPass(unittest.TestCase):
    """A symbol with '~' pin names must be reported, never counted as matching.

    U24/U25/U510 use the stock 74xGxx symbol whose pins are unnamed. Their nets
    are correct, but the pin names cannot be compared to a datasheet. Counting
    them as a pass would be the exact false-green this repo keeps finding.
    """

    def test_unnamed_pin_is_not_matched(self):
        part = [{"ref": "U99", "pin": "1", "pin_name": "~", "net": "X"},
                {"ref": "U99", "pin": "2", "pin_name": "Y", "net": "Z"}]
        table = {1: "A", 2: "Y"}
        # emulate the main-loop rule: any '~' makes the part unauditable
        self.assertTrue(any((r["pin_name"] or "").strip() == "~" for r in part))
        ok, bad = a.audit(table, part)
        # and confirm audit() alone would have produced a bogus mismatch
        self.assertTrue(any(b[1] == "~" for b in bad))

    def test_the_three_stock_symbol_parts_are_reported(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, "audit_pin_names.py"],
                           capture_output=True, text=True,
                           cwd=a.PIN_MAP.parent)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("UNNAMED PINS", r.stdout)
        for ref in ("U24", "U25", "U510"):
            self.assertIn(ref, r.stdout)


class TestTableIntegrity(unittest.TestCase):
    def test_table_covers_all_100_pins(self):
        t = table()
        self.assertEqual(len(t), 100)
        self.assertEqual(sorted(t), list(range(1, 101)))

    def test_no_pin_name_is_empty(self):
        for pin, name in table().items():
            self.assertTrue(name.strip(), "pin %s has an empty name" % pin)

    def test_key_power_pins_have_expected_names(self):
        t = table()
        self.assertEqual(t[100], "VDD")
        self.assertEqual(t[99], "VSS")
        self.assertEqual(t[35], "VSSA")
        self.assertEqual(t[37], "VDDA")
        self.assertEqual(t[36], "VREF+")
        self.assertEqual(t[6], "VBAT")


if __name__ == "__main__":
    unittest.main()
