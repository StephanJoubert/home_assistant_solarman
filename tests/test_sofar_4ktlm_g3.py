"""Decode representative G3 blocks with the integration's actual parser.

These are synthetic samples; no device serials or household telemetry are used.
Run with: python -m unittest discover -s tests -v (requires PyYAML).
"""
import importlib.util
from pathlib import Path
import unittest

import yaml


COMPONENT = Path(__file__).resolve().parents[1] / 'custom_components' / 'solarman'
PROFILE = 'sofar_4ktlm-g3.yaml'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ParameterParser = load_module('solarman_profile_parser', COMPONENT / 'parser.py').ParameterParser


class Sofar4KTLMG3Test(unittest.TestCase):
    def setUp(self):
        with (COMPONENT / 'inverter_definitions' / PROFILE).open(encoding='utf-8') as source:
            self.profile = yaml.safe_load(source)

    def decode(self, registers):
        parser = ParameterParser(self.profile)
        for request in self.profile['requests']:
            start, end = request['start'], request['end']
            block = [registers.get(address, 0) for address in range(start, end + 1)]
            parser.parse(block, start, len(block))
        return parser.get_result()

    def test_complete_aligned_requests_and_register_coverage(self):
        requests = self.profile['requests']
        self.assertEqual(
            [(r['start'], r['end'], r['mb_functioncode']) for r in requests],
            [(0x0400, 0x042E, 3), (0x0480, 0x04AF, 3), (0x0580, 0x0589, 3), (0x0680, 0x069B, 3)],
        )
        sensors = ParameterParser(self.profile).get_sensors()
        names = [sensor['name'] for sensor in sensors]
        self.assertEqual(len(names), len(set(names)))
        for sensor in sensors:
            with self.subTest(sensor=sensor['name']):
                self.assertTrue(any(all(r['start'] <= address <= r['end'] for address in sensor['registers']) for r in requests))
        self.assertNotIn('L2 Voltage', names)
        self.assertNotIn('L3 Voltage', names)
        self.assertNotIn('Inverter module temperature', names)

    def test_two_mppt_single_phase_generation_and_energy_word_order(self):
        decoded = self.decode({
            0x0404: 2, 0x0418: 42, 0x041A: 33,
            0x0484: 6000, 0x0485: 97, 0x0486: 0, 0x048D: 2200, 0x048E: 441,
            0x0584: 2600, 0x0585: 200, 0x0586: 52,
            0x0587: 2590, 0x0588: 198, 0x0589: 51,
            0x0684: 0, 0x0685: 321, 0x0686: 1, 0x0687: 0x2345,
        })
        self.assertEqual(decoded['Inverter status'], 'Normal')
        self.assertEqual(decoded['PV1 Power'], 520)
        self.assertEqual(decoded['PV2 Power'], 510)
        self.assertEqual(decoded['PV1 Voltage'], 260)
        self.assertAlmostEqual(decoded['PV2 Current'], 1.98)
        self.assertEqual(decoded['Output active power'], 970)
        self.assertEqual(decoded['Grid frequency'], 60)
        self.assertEqual(decoded['L1 Voltage'], 220)
        self.assertAlmostEqual(decoded['L1 Current'], 4.41)
        self.assertEqual(decoded['Inverter inner temperature'], 42)
        self.assertEqual(decoded['Inverter radiator temperature'], 33)
        self.assertAlmostEqual(decoded['Daily Production'], 3.21)
        self.assertAlmostEqual(decoded['Total Production'], 0x12345 * 0.1)

    def test_g3_fault_status_is_not_the_legacy_status_mapping(self):
        self.assertEqual(self.decode({0x0404: 4})['Inverter status'], 'Recoverable Fault')
        self.assertEqual(self.decode({0x0404: 5})['Inverter status'], 'Permanent Fault')

    def test_fault_bitfields_are_not_mislabelled_as_legacy_faults(self):
        decoded = self.decode({0x0404: 2, 0x0405: 3, 0x0410: 0x8000})
        self.assertEqual(decoded['Fault 1'], 3)
        self.assertEqual(decoded['Fault 2'], 'No error')
        self.assertEqual(decoded['Fault 12'], 0x8000)

    def test_profile_is_available_in_config_flow_lookup_list(self):
        const = load_module('solarman_profile_const', COMPONENT / 'const.py')
        self.assertIn(PROFILE, const.LOOKUP_FILES)


if __name__ == '__main__':
    unittest.main()
