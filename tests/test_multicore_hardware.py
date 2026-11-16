import json
import subprocess
import sys
cli = sys.argv[1]
cpu = json.loads(subprocess.check_output([cli, '--cpu'], text=True))
if cpu['topology']['safe_thread_limit'] < 2:
    print('SKIP: fewer than two CPUs available under affinity/quota/runtime limits')
    sys.exit(77)
p = subprocess.run([cli, 'parallel-kernels', '--threads', '1,2', '--size', '1024', '--chunks', '16', '--repetitions', '2', '--affinity', 'compact'], capture_output=True, text=True)
assert p.returncode == 0, p.stderr
d = json.loads(p.stdout)
if any(t['observed_threads'] != t['requested_threads'] or not t['affinity_applied'] for t in d['trials']):
    print('SKIP: runtime team or worker affinity unavailable')
    sys.exit(77)
assert d['verified'] and all(t['affinity_restored'] for t in d['trials'])
print('Hardware multicore/affinity correctness passed; timing is not a scaling claim')
