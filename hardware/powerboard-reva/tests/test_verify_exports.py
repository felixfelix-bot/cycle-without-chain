"""Negative controls exercise the CLI with and without optimization, in scratch."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class ExportVerifierTests(unittest.TestCase):
    def run_case(self, mutate=None, valid=False):
        for optimized in (False, True):
            with self.subTest(optimized=optimized), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'board'
                shutil.copytree(SOURCE, root, ignore=shutil.ignore_patterns('__pycache__'))
                if mutate:
                    mutate(root)
                before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
                command = [sys.executable] + (['-O'] if optimized else [])
                # Optional subprocess coverage, including optimized execution.
                if os.environ.get('VERIFIER_COVERAGE'):
                    command += ['-m', 'coverage', 'run', '--parallel-mode', '--include=*/verify_exports.py']
                result = subprocess.run(command + [str(root / 'verify_exports.py')], capture_output=True, text=True)
                if valid:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('PARTIAL_NOT_SAFE_TO_ENERGIZE', result.stdout)
                    summary = json.loads(result.stdout)
                    for key, count in {'components': 397, 'nets': 226,
                                       'verified_pin_assignments': 1171, 'explicit_nc_endpoints': 51, 'mosfets': 29,
                                       'drivers': 4, 'erc_errors': 0, 'erc_warnings': 0,
                                       'pwr_flags': 10, 'svg_pages': 32}.items():
                        self.assertEqual(summary[key], count)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                after = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
                self.assertEqual(before, after, 'validation must not write artifacts')

    def test_valid_is_read_only(self):
        self.run_case(valid=True)

    def test_missing_empty_malformed_inputs(self):
        for filename in ('exports/powerboard-reva.net', 'exports/erc.rpt', 'pin-net-map.csv', 'review-bom.csv', 'mcu-core.kicad_sch'):
            for mode in ('missing', 'empty', 'malformed'):
                with self.subTest(filename=filename, mode=mode):
                    def mutate(root):
                        p = root / filename
                        if mode == 'missing':
                            p.unlink()
                        else:
                            p.write_text('' if mode == 'empty' else 'not a valid artifact (')
                    self.run_case(mutate)

    def test_structural_controls(self):
        def extra_net(root):
            p = root / 'exports/powerboard-reva.net'
            p.write_text(p.read_text().replace('(nets', '(nets (net (code "999") (name "EXTRA"))', 1))
        def duplicate_manifest(root):
            p = root / 'pin-net-map.csv'
            lines = p.read_text().splitlines()
            lines[2] = lines[1]
            p.write_text('\n'.join(lines) + '\n')
        def missing_endpoint(root):
            p = root / 'exports/powerboard-reva.net'
            import re
            text, count = re.subn(r'\(node \(ref "J4"\) \(pin "1"\)[^\n]*', '', p.read_text(), count=1)
            self.assertEqual(count, 1)
            p.write_text(text)
        for mutate in (extra_net, duplicate_manifest, missing_endpoint):
            with self.subTest(mutation=mutate.__name__):
                self.run_case(mutate)

    def test_explicit_nc_corruptions(self):
        import re
        def mutate_net(root, mode):
            p = root / 'exports/powerboard-reva.net'
            text = p.read_text()
            pattern = r'\(node \(ref "U17"\) \(pin "38"\)[^\n]*'
            match = re.search(pattern, text)
            self.assertIsNotNone(match)
            original = match.group()
            replacements = {
                'missing': '',
                'changed': original.replace('(pin "38")', '(pin "101")'),
                'not_nc': original.replace('+no_connect', ''),
                'not_singleton': original + '\n' + original.replace('(pin "38")', '(pin "101")'),
            }
            p.write_text(text.replace(original, replacements[mode], 1))
        for mode in ('missing', 'changed', 'not_nc', 'not_singleton'):
            with self.subTest(mode=mode):
                self.run_case(lambda root: mutate_net(root, mode))
        def missing_marker(root):
            p = root / 'mcu-core.kicad_sch'
            text, count = re.subn(r'\(no_connect \(at [^)]*\) \(uuid [^)]*\)\)', '', p.read_text(), count=1)
            self.assertEqual(count, 1)
            p.write_text(text)
        self.run_case(missing_marker)

    def test_issue_body_under_clean_totals_is_rejected(self):
        """The dangerous case: totals read clean but a finding is present.

        The verifier must not rely on the totals line alone. This injects a
        complete, well-formed power_pin_not_driven block while leaving the
        summary at 0/0, and the verifier must still fail.
        """
        def mutate(root):
            p = root / 'exports/erc.rpt'
            text = p.read_text()
            marker = '** ERC messages: 0  Errors 0  Warnings 0'
            self.assertIn(marker, text)
            block = ('[power_pin_not_driven]: Input Power pin not driven by any '
                     'Output Power pins\n    ; error\n'
                     '    @(50.80 mm, 76.20 mm): Symbol U1 Pin 3 [VM, Power input, Line]\n')
            p.write_text(text.replace(marker, block + marker, 1))
        self.run_case(mutate)

    def test_missing_pwr_flag_is_rejected(self):
        """A vanished PWR_FLAG must fail, or the undriven errors return silently."""
        def mutate(root):
            # Remove ONE COMPLETE flag reference everywhere it appears, rather
            # than rewriting a single occurrence: each flag appears several times
            # (symbol uuid, instance reference, property), so a one-occurrence
            # edit leaves the reference count unchanged and the mutant passes.
            targets = set()
            for sch in root.glob('*.kicad_sch'):
                targets.update(re.findall(r'#FLG\d{3}', sch.read_text()))
            self.assertTrue(targets, 'no #FLG reference to remove')
            victim = sorted(targets)[0]
            removed = 0
            for sch in root.glob('*.kicad_sch'):
                text = sch.read_text()
                if victim in text:
                    sch.write_text(text.replace(victim, '#FLGX'))
                    removed += 1
            self.assertGreater(removed, 0, 'victim %s not found to remove' % victim)
        self.run_case(mutate)

    def test_corruptions(self):
        cases = [
            ('exports/powerboard-reva.net', 'GEN_INHA', 'BROKEN_GEN_INHA'),
            ('exports/powerboard-reva.net', '(pin "32")', '(pin "999")'),
            ('exports/powerboard-reva.net', 'DRV8353SRTAT', 'WRONG_PART'),
            ('exports/powerboard-reva.net', '(ref "U1")', '(ref "U999")'),
            ('exports/powerboard-reva.net', '(node (ref "J4") (pin "1")', '(node (ref "J4") (pin "1")) (node (ref "J4") (pin "1")'),
            # ERC is now clean (0 errors / 0 warnings), so the corruption cases
            # cannot mutate issue text that no longer exists. They instead inject
            # each class of change the verifier must reject:
            #   - a non-zero total
            #   - a warning alongside a zero error count
            #   - a well-formed issue body under a clean total (the dangerous one:
            #     totals look fine but a finding is present)
            ('exports/erc.rpt', '** ERC messages: 0  Errors 0  Warnings 0',
             '** ERC messages: 1  Errors 1  Warnings 0'),
            ('exports/erc.rpt', '** ERC messages: 0  Errors 0  Warnings 0',
             '** ERC messages: 1  Errors 0  Warnings 1'),
            ('exports/powerboard-reva.net', 'DC_LINK', 'BROKEN_DC_LINK'),
            ('pin-net-map.csv', 'GEN_INHA', 'BROKEN_GEN_INHA'),
            ('review-bom.csv', 'DRV8353SRTAT', 'WRONG_PART'),
        ]
        for filename, old, new in cases:
            with self.subTest(filename=filename, old=old):
                def mutate(root):
                    p = root / filename
                    text = p.read_text()
                    self.assertIn(old, text)
                    p.write_text(text.replace(old, new, 1))
                self.run_case(mutate)


if __name__ == '__main__':
    unittest.main()
