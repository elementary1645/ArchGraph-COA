"""Integration checks for static measurement boundaries and JSON contracts."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = sys.argv.pop()

class BenchmarkTests(unittest.TestCase):
    def test_metadata(self):
        data = json.loads(subprocess.check_output([CLI, '--cpu']))
        self.assertEqual(data['clock'], 'std::chrono::steady_clock')
        self.assertGreater(data['openmp_spec'], 0)
        self.assertIsNone(data['hardware_counters_available'])

    def test_verified_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = Path(tmp) / 'graph.txt'
            graph.write_text('5 4\n0 1 0\n1 2 4294967295\n0 3 2\n3 2 1\n')
            for algorithm in ['dijkstra', 'delta-stepping']:
                args = [CLI, 'bench', '--input', str(graph), '--source', '0', '--algorithm', algorithm]
                if algorithm == 'delta-stepping':
                    args += ['--delta', '16', '--threads', '2']
                data = json.loads(subprocess.check_output(args + ['--repetitions', '3', '--warmups', '1']))
                self.assertTrue(data['verified'])
                self.assertEqual(data['unit'], 'wall_ns')
                self.assertEqual(len(data['samples']), 3)
                self.assertTrue(all(type(t) is int and t >= 0 for t in data['samples']))
                self.assertIsNone(data['actual_threads'])
                for option, value in [('--repetitions', '0'), ('--repetitions', '10001'),
                                      ('--warmups', '-1'), ('--warmups', '10001')]:
                    result = subprocess.run(args + [option, value], capture_output=True)
                    self.assertEqual(result.returncode, 2)
                    self.assertFalse(result.stdout)
                    self.assertTrue(result.stderr)

if __name__ == '__main__':
    unittest.main()
