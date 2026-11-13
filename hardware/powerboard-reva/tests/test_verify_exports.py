"""Negative controls exercise the CLI with and without optimization, in scratch."""
import json
import os
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
                    for key, count in {'components': 387, 'nets': 220,
                                       'verified_pin_assignments': 1142, 'explicit_nc_endpoints': 51, 'mosfets': 29,
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

    def test_corruptions(self):
        cases = [
            ('exports/powerboard-reva.net', 'GEN_INHA', 'BROKEN_GEN_INHA'),
            ('exports/powerboard-reva.net', '(pin "32")', '(pin "999")'),
            ('exports/powerboard-reva.net', 'DRV8353SRTAT', 'WRONG_PART'),
            ('exports/powerboard-reva.net', '(ref "U1")', '(ref "U999")'),
            ('exports/powerboard-reva.net', '(node (ref "J4") (pin "1")', '(node (ref "J4") (pin "1")) (node (ref "J4") (pin "1")'),
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

    def test_erc_faults_are_caught(self):
        """Negative controls for the empty-ERC rule.

        ERC is required to be EMPTY, so there is no pre-existing error text to
        mutate: the old controls rewrote 'Errors 10' and 'Pin 24 [VREF', which
        stopped existing the moment the ten undriven-supply errors were really
        fixed. Rather than delete those controls, plant a fault into the clean
        report. This is a stronger check than the one it replaces -- it proves
        the verifier rejects a *new* issue of any kind, not just that it noticed
        a specific known string changing.
        """
        # (description, mutation applied to a copy of the clean erc.rpt)
        def add_issue(text):
            return text.replace(
                ' ** ERC messages: 0  Errors 0  Warnings 0',
                ' ** ERC messages: 1  Errors 1  Warnings 0\n'
                '[power_pin_not_driven]: Input Power pin not driven by any Output Power pins\n'
                '    Symbol U3 Pin 1 [IN]\n'
                ' ** ERC messages: 1  Errors 1  Warnings 0',
            )

        def bump_totals(text):
            return text.replace('** ERC messages: 0  Errors 0  Warnings 0',
                                '** ERC messages: 1  Errors 1  Warnings 0')

        def rename_issue(text):
            return add_issue(text).replace('Symbol U3 Pin 1', 'Symbol U1 Pin 24')

        def header_swap(text):
            return text.replace('Report includes: Errors, Warnings', 'Report includes: Warnings')

        for name, fn in (('new_issue', add_issue), ('totals_only', bump_totals),
                         ('wrong_identity', rename_issue), ('bad_header', header_swap)):
            with self.subTest(case=name):
                def mutate(root, fn=fn):
                    p = root / 'exports/erc.rpt'
                    text = p.read_text()
                    new = fn(text)
                    self.assertNotEqual(new, text, f'{name} mutation did not change the report')
                    p.write_text(new)
                self.run_case(mutate)

    def test_erc_clean_control_passes(self):
        """The positive control: the unmodified report must be accepted.

        Without this, a verifier that rejected every ERC report would pass all
        four negative controls in test_erc_faults_are_caught and look thorough
        while being useless.
        """
        self.run_case(valid=True)



if __name__ == '__main__':
    unittest.main()
