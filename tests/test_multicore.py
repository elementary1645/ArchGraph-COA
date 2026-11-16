import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

schema = json.loads((Path(__file__).resolve().parents[1] / 'docs/multicore-v1.schema.json').read_text())
def validate(value, rule):
    if 'const' in rule:
        assert value == rule['const']
    if 'enum' in rule:
        assert value in rule['enum']
    if 'type' in rule:
        kinds = rule['type'] if isinstance(rule['type'], list) else [rule['type']]
        checks = {'object': isinstance(value, dict), 'array': isinstance(value, list), 'string': isinstance(value, str), 'integer': type(value) is int, 'number': type(value) in (int, float), 'boolean': type(value) is bool, 'null': value is None}
        assert any(checks[k] for k in kinds), (value, kinds)
    if isinstance(value, dict):
        assert all(k in value for k in rule.get('required', []))
        for k, v in value.items():
            if k in rule.get('properties', {}):
                validate(v, rule['properties'][k])
    if isinstance(value, list):
        assert len(value) >= rule.get('minItems', 0)
        for v in value:
            validate(v, rule.get('items', {}))
    if type(value) in (int, float):
        if 'minimum' in rule:
            assert value >= rule['minimum']
        if 'exclusiveMinimum' in rule:
            assert value > rule['exclusiveMinimum']

cli = sys.argv[1]
def run(args, ok=True):
    p = subprocess.run([cli] + args, text=True, capture_output=True)
    assert (p.returncode == 0) == ok, (args, p.stdout, p.stderr)
    return json.loads(p.stdout) if ok else p

with tempfile.TemporaryDirectory() as tmp:
    graph = Path(tmp) / 'graph.txt'
    graph.write_text('4 4\n0 1 2\n1 2 3\n0 2 9\n2 3 1\n')
    csvpath = Path(tmp) / 'trials.csv'
    args = ['scaling', '--input', str(graph), '--source', '0', '--threads', '1,2', '--allow-oversubscription', '--repetitions', '3', '--warmups', '2', '--hardware-counters', '--csv', str(csvpath)]
    d = run(args)
    validate(d, schema)
    assert d['schema'] == 'archgraph-multicore-experiments' and d['schema_version'] == 1
    assert d['verified'] and d['counter_status'] == 'unsupported_scope'
    assert len(d['trials']) == 10 and sum(t['warmup'] for t in d['trials']) == 4
    assert len({t['checksum'] for t in d['trials']}) == 1
    assert all(t['observed_threads'] in (1, 2) and t['wall_ns'] > 0 for t in d['trials'])
    assert all(s['minimum_wall_ns'] <= s['median_wall_ns'] <= s['maximum_wall_ns'] for s in d['summaries'])
    baseline = next(s['median_wall_ns'] for s in d['summaries'] if s['requested_threads'] == 1)
    for s in d['summaries']:
        assert abs(s['speedup'] - baseline/s['median_wall_ns']) < 1e-12
        assert abs(s['efficiency'] - s['speedup']/s['requested_threads']) < 1e-12
    with csvpath.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(d['trials'])
    for row, trial in zip(rows, d['trials']):
        assert float(row['wall_ns']) == trial['wall_ns'] and int(row['checksum']) == trial['checksum']
    again = run(args)
    assert [(t['block'], t['warmup'], t['requested_threads']) for t in d['trials']] == [(t['block'], t['warmup'], t['requested_threads']) for t in again['trials']]
    for bad in ['0', '1,1', '1,', '4097', '-2']:
        run(['scaling', '--input', str(graph), '--source', '0', '--threads', bad], False)
    safe = run(['--cpu'])['topology']['safe_thread_limit']
    run(['scaling', '--input', str(graph), '--source', '0', '--threads', str(safe+1)], False)
    for options in [['--repetitions', '0'], ['--delta', '0'], ['--parallel-fraction', 'nan'], ['--source', '4294967296'], ['--algorithm', 'dijkstra'], ['--affinity', 'bad']]:
        run(['scaling', '--input', str(graph), '--source', '0'] + options, False)
    for workload in ['uniform', 'irregular']:
        k = run(['parallel-kernels', '--threads', '1,2', '--allow-oversubscription', '--size', '513', '--chunks', '1,7', '--workload', workload, '--repetitions', '2', '--warmups', '1', '--affinity', 'compact'])
        validate(k, schema)
        assert len(k['trials']) == 48 and len(k['summaries']) == 16
        assert len({t['checksum'] for t in k['trials']}) == 1
        assert all(t['affinity_restored'] and t['wall_ns'] > 0 for t in k['trials'])
    run(['parallel-kernels', '--chunks', '0'], False)
    limited_env = dict(os.environ, OMP_THREAD_LIMIT='1')
    p = subprocess.run([cli] + args, text=True, capture_output=True, env=limited_env)
    assert p.returncode == 0, p.stderr
    limited = json.loads(p.stdout)
    assert all(t['observed_threads'] == 1 for t in limited['trials'])
    assert next(s for s in limited['summaries'] if s['requested_threads'] == 2)['speedup'] is None
    assert next(s for s in limited['summaries'] if s['requested_threads'] == 2)['efficiency'] is None
print('Phase 4 JSON, CSV, correctness, scheduling, synchronization and CLI contracts passed')
