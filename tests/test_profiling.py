"""Schema, provenance and fallback contracts; no mock measurements are hardware claims."""
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import unittest
CLI = sys.argv.pop()
EVENTS = ('cpu_cycles', 'instructions', 'cache_references', 'cache_misses',
          'branch_instructions', 'branch_misses')

class ProfilingTests(unittest.TestCase):
    def command(self, *args):
        return json.loads(subprocess.check_output([CLI, *args]))

    def test_diagnostic(self):
        data = self.command('--counter-diagnostics')
        for key in ('os', 'architecture', 'kernel', 'perf_event_paranoid', 'affinity_logical_processors'):
            self.assertIn(key, data)
        self.assertEqual(set(data['availability']), set(EVENTS))
        self.assertEqual(set(data['probe_counters']), set(EVENTS))
        self.assertIn('time_enabled_ns', data['probe_counters']['cpu_cycles'])
        for value in data['availability'].values():
            self.assertIn(value['status'], ('ready', 'permission_denied', 'unsupported', 'system_error'))
            self.assertIsNone(value['value'])

    def test_benchmarks(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = Path(tmp) / 'graph.txt'
            graph.write_text('3 2\n0 1 4\n1 2 5\n')
            base = ['bench', '--input', str(graph), '--source', '0', '--repetitions', '4', '--warmups', '0']
            plain = self.command(*base, '--algorithm', 'dijkstra')
            seq = self.command(*base, '--algorithm', 'dijkstra', '--hardware-counters')
            parallel = self.command(*base, '--hardware-counters', '--algorithm', 'delta-stepping', '--delta', '4', '--threads', '2')
            self.assertEqual(plain['counter_status'], 'not_requested')
            self.assertEqual(parallel['counter_status'], 'unsupported_scope')
            self.assertEqual(plain['input_identity'], seq['input_identity'])
            self.assertEqual(seq['input_identity'], parallel['input_identity'])
            # Independent fingerprint of the documented loaded-CSR encoding.
            digest = 14695981039346656037
            for value in [3,2, 0,1,2,2, 1,2, 4,5]:
                for byte in value.to_bytes(8, 'little'):
                    digest = ((digest ^ byte) * 1099511628211) & ((1 << 64) - 1)
            self.assertEqual(seq['input_identity']['value'], f'{digest:016x}')
            for data in (plain, seq, parallel):
                self.assertEqual(data['status'], 'completed')
                self.assertTrue(data['verified'])
                self.assertEqual(data['median_wall_ns'], statistics.median(data['samples']))
                self.assertEqual(len(data['runs']), 4)
                self.assertFalse(data['measurement_scope']['thread_aggregation'])
                for key in ('compiler', 'build_type', 'compiler_flags', 'build_revision', 'build_dirty'):
                    self.assertIn(key, data['metadata'])
                for run, sample in zip(data['runs'], data['samples']):
                    self.assertEqual(run['wall_ns'], sample)
                    self.assertEqual(set(run['counters']), set(EVENTS))
                    for counter in run['counters'].values():
                        if counter['status'] in ('available', 'multiplexed'):
                            self.assertGreater(counter['time_running_ns'], 0)
                            self.assertIsNotNone(counter['value'])
                        else:
                            self.assertIsNone(counter['value'])
                    for metric, numerator, denominator in [('ipc', 'instructions', 'cpu_cycles'),
                            ('cpi', 'cpu_cycles', 'instructions'), ('cache_miss_ratio','cache_misses','cache_references'),
                            ('branch_miss_ratio','branch_misses','branch_instructions')]:
                        n, d = (run['counters'][k]['value'] for k in (numerator, denominator))
                        if n is None or d is None or d == 0:
                            self.assertIsNone(run['derived'][metric])
                        else:
                            self.assertAlmostEqual(run['derived'][metric], n/d)
            graph.write_text('3 2\n0 1 4\n1 2 6\n')
            changed = self.command(*base, '--algorithm', 'dijkstra')
            self.assertNotEqual(changed['input_identity'], plain['input_identity'])
            # Flag may appear anywhere, but duplicates and use outside bench fail.
            for args in [base + ['--algorithm','dijkstra','--hardware-counters','--hardware-counters'],
                         ['sssp','--hardware-counters'], ['--hardware-counters']]:
                result = subprocess.run([CLI, *args], capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(result.stdout)

if __name__ == '__main__':
    unittest.main()
