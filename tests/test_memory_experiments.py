"""Phase 3 contracts and independent checksums; no timing-based cache assertions."""
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import unittest
CLI = sys.argv.pop()
MASK = (1 << 64) - 1
EVENTS = {'l1d_read_accesses', 'l1d_read_misses', 'll_read_accesses', 'll_read_misses', 'dtlb_read_accesses', 'dtlb_read_misses'}

class MemoryTests(unittest.TestCase):
    def command(self, *args):
        data = json.loads(subprocess.check_output([CLI, *args]))
        self.assertEqual(data['schema'], 'archgraph-memory-experiments')
        self.assertEqual(data['schema_version'], 1)
        self.assertTrue(data['verified'])
        self.assertIn('build_type', data['metadata'])
        return data

    def timing(self, record, runs=2):
        self.assertEqual(len(record['runs']), runs)
        self.assertEqual(record['median_wall_ns'], statistics.median(r['wall_ns'] for r in record['runs']))
        for run in record['runs']:
            self.assertGreaterEqual(run['wall_ns'], 0)
            self.assertEqual(set(run['counters']), EVENTS)
            for counter in run['counters'].values():
                if counter['status'] not in ('available', 'multiplexed'):
                    self.assertIsNone(counter['value'])
            for metric, access, miss in [('l1d_read_miss_ratio','l1d_read_accesses','l1d_read_misses'),
                                       ('ll_read_miss_ratio','ll_read_accesses','ll_read_misses'),
                                       ('dtlb_read_miss_ratio','dtlb_read_accesses','dtlb_read_misses')]:
                a, m = run['counters'][access]['value'], run['counters'][miss]['value']
                if a is None or m is None or a == 0:
                    self.assertIsNone(run['derived'][metric])
                else:
                    self.assertAlmostEqual(run['derived'][metric], m/a)

    def test_memory_and_graphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = Path(tmp)/'g.txt'
            graph.write_text('5 5\n0 0 0\n0 1 0\n1 2 4294967295\n2 2 4\n3 4 2\n')
            data = self.command('memory', '--input', str(graph))
            for layout in data['layouts'].values():
                self.assertEqual(layout['logical_payload_bytes'], 40)
                self.assertIsNone(layout['allocator_overhead_bytes'])
                self.assertIsNone(layout['physical_memory_bytes'])
                self.assertEqual(layout['container_overhead_estimate_bytes'],layout['container_object_bytes']+layout['used_metadata_bytes'])
                self.assertEqual(layout['accounted_total_bytes'], layout['capacity_storage_bytes'] + layout['container_object_bytes'])
            self.assertIn('rss_bytes',data['process_memory'])
            comparison = self.command('compare-layouts','--input',str(graph),'--source','0','--runs','2')
            self.assertTrue(comparison['outputs_identical'])
            self.assertEqual(data['input_identity'],comparison['input_identity'])
            self.timing(comparison['csr_dijkstra']); self.timing(comparison['adjacency_dijkstra'])
            self.assertEqual(comparison['csr_dijkstra']['runs'][0]['checksum'], comparison['adjacency_dijkstra']['runs'][0]['checksum'])
            checksums = []
            for pattern in ('csr','adjacency'):
                d = self.command('locality','--pattern',pattern,'--input',str(graph),'--passes','3','--runs','2')
                self.assertEqual(d['edge_visits'],15)
                self.timing(d['timing'])
                checksums.append(d['expected_checksum'])
            self.assertEqual(checksums[0],checksums[1])
            graph.write_text('0 0\n')
            self.assertEqual(self.command('memory','--input',str(graph))['edges'],0)
            self.assertEqual(self.command('locality','--pattern','adjacency','--input',str(graph),'--runs','2')['expected_checksum'],0)
            graph.write_text('2 2\n0 1 1\n0 1 2\n')
            result = subprocess.run([CLI,'memory','--input',str(graph)],capture_output=True)
            self.assertEqual(result.returncode,2); self.assertIn(b'duplicate',result.stderr)

    def test_spatial_and_reproducibility(self):
        seed, elements, accesses = 17, 128, 256
        expected = (sum(((i*0x9e3779b97f4a7c15)&MASK)^seed for i in range(elements))*2)&MASK
        for pattern in ('sequential','strided','random'):
            args = ['locality','--pattern',pattern,'--size','1024','--accesses',str(accesses),'--seed',str(seed),'--runs','2']
            if pattern == 'strided': args += ['--stride','16']
            first = self.command(*args)['experiment']; second = self.command(*args)['experiment']
            self.assertEqual(first['sequence_fingerprint_u64'],second['sequence_fingerprint_u64'])
            self.assertEqual(first['expected_checksum'],expected)
            self.assertEqual(first['data_reads'],accesses)
            self.assertEqual(first['index_reads'],accesses)
            self.assertEqual(first['distinct_data_elements'],elements)
            self.timing(first['timing'])
            self.assertTrue(all(r['checksum'] == expected for r in first['timing']['runs']))
        # Independent SplitMix64/Fisher-Yates implementation verifies the random order fingerprint.
        state, order = seed,list(range(elements))
        def next_value():
            nonlocal state
            state = (state+0x9e3779b97f4a7c15)&MASK
            z = state
            z = ((z^(z>>30))*0xbf58476d1ce4e5b9)&MASK
            z = ((z^(z>>27))*0x94d049bb133111eb)&MASK
            return z^(z>>31)
        for n in range(elements,1,-1):
            threshold = ((1<<64)-n)%n
            r = next_value()
            while r < threshold: r = next_value()
            j = r%n
            order[n-1],order[j] = order[j],order[n-1]
        fingerprint = 14695981039346656037
        for value in order:
            for byte in value.to_bytes(8,'little'): fingerprint = ((fingerprint^byte)*1099511628211)&MASK
        self.assertEqual(first['sequence_fingerprint_u64'],fingerprint)
        profiled = self.command('locality','--pattern','random','--size','1024','--hardware-counters','--runs','2')
        self.timing(profiled['experiment']['timing'])

    def test_temporal(self):
        for working in (1024,8192):
            d = self.command('locality','--pattern','temporal','--size','8192','--working-set',str(working),'--accesses','4096','--runs','2')['experiment']
            self.assertEqual(d['allocated_data_bytes'],8192)
            self.assertEqual(d['active_data_bytes'],working)
            self.assertEqual(d['sequence_payload_bytes'],working//2)
            self.assertEqual(d['data_reads'],4096)
            self.timing(d['timing'])

    def test_cache_metadata_and_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = str(Path(tmp)/'missing')
            d = self.command('cache-study','--cache-root',absent,'--max-size','4096','--runs','2')
            self.assertEqual(d['cache_info']['status'],'unavailable')
            self.assertEqual(d['plan_mode'],'fallback_configurable_not_cache_capacities')
            d = self.command('cache-study','--cache-root',absent,'--sizes','1024,4096','--runs','2')
            self.assertEqual(d['plan_mode'],'explicit')
            self.assertEqual([e['allocated_data_bytes'] for e in d['experiments']],[1024,4096])
            self.assertEqual([e['data_reads'] for e in d['experiments']],[512,512])
            for e in d['experiments']: self.timing(e['timing'])
            root = Path(tmp)/'cache'; index = root/'index0'; index.mkdir(parents=True)
            for name,value in {'level':'1','type':'Data','size':'1024','coherency_line_size':'64','shared_cpu_list':'0-1'}.items():
                (index/name).write_text(value+'\n')
            d = self.command('cache-study','--cache-root',str(root),'--max-size','4096','--runs','2')
            self.assertEqual(d['plan_mode'],'discovered')
            self.assertEqual([e['allocated_data_bytes'] for e in d['experiments']],[512,1024,2048])
            self.assertEqual(d['cache_info']['entries'][0]['shared_cpu_list'],'0-1')

    def test_help_and_rejections(self):
        for command in ('memory','locality','cache-study','compare-layouts'):
            result = subprocess.run([CLI,command,'--help'],capture_output=True)
            self.assertEqual(result.returncode,0); self.assertIn(b'Usage:',result.stdout)
        invalid = [ ['memory'], ['memory','--input','nonexistent'], ['memory','--hardware-counters'],
            ['locality','--pattern','bad'], ['locality','--size','0'], ['locality','--size','9'],
            ['locality','--size','268435464'], ['locality','--size','-1'], ['locality','--size','+8'],
            ['locality','--runs','0'], ['locality','--repetitions','10001'], ['locality','--warmups','10001'],
            ['locality','--seed','18446744073709551616'], ['locality','--accesses','0'],
            ['locality','--pattern','strided','--stride','0'], ['locality','--pattern','csr'],
            ['locality','--pattern','csr','--size','1024'], ['locality','--pattern','temporal','--size','1024','--working-set','2048'],
            ['cache-study','--sizes','8,8'], ['cache-study','--sizes','8,'], ['cache-study','--sizes',''],
            ['cache-study','--sizes','1024','--accesses','1'], ['cache-study','--max-size','4'],
            ['locality','--runs','1','--repetitions','1'], ['locality','--hardware-counters','--hardware-counters'],
            ['locality','--unknown','1'], ['locality','--size'] ]
        for args in invalid:
            with self.subTest(args=args):
                result = subprocess.run([CLI,*args],capture_output=True)
                self.assertEqual(result.returncode,2); self.assertFalse(result.stdout); self.assertTrue(result.stderr)

if __name__ == '__main__': unittest.main()
