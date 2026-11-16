# CPU profiling guide

Phase 2 adds optional Linux hardware counters to the existing verified benchmark.
Imported Dijkstra and delta-stepping implementations are unchanged.

## Build and demonstrate

```sh
cmake -S . -B build/phase2-release -DCMAKE_BUILD_TYPE=Release \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase2-release --parallel 2
ctest --test-dir build/phase2-release --output-on-failure
build/phase2-release/archgraph --counter-diagnostics
python3 -B benchmarks/python/generate.py generate --spec benchmarks/configs/chain-v1.json --output data/phase2-chain
python3 -B benchmarks/python/generate.py verify --manifest data/phase2-chain/manifest.json
build/phase2-release/archgraph bench --input data/phase2-chain/graph.txt \
  --source 0 --algorithm dijkstra --repetitions 10 --hardware-counters
build/phase2-release/archgraph bench --input data/phase2-chain/graph.txt \
  --source 0 --algorithm delta-stepping --delta 16 --threads 2 \
  --repetitions 10 --hardware-counters
```

The generation directory must be new. The flag may occur anywhere among benchmark
options; it takes no value and duplicates are rejected. Existing SSSP commands and
benchmarks without counters still work. Software-only tests do not need hardware
access. The optional hardware CTest returns skip code 77 when the cycle/instruction
pair is inaccessible or not reliably scheduled, and fails on unexpected syscall
errors. Skips must be reported separately from passed tests.

## Execution boundaries and overhead

File loading, fingerprinting, reference Dijkstra, warmups, sample storage allocation,
verification, scaling and serialization are outside the measured region. Each
repetition creates a fresh counter session outside wall timing; this avoids
cumulative enabled/running times that a reset alone would not clear. Each result's
complete distance vector is verified after both clocks/counters stop. A correctness
failure prevents completed result JSON from being emitted.

Counters enable before the wall-clock start and disable after its stop. Thus
hardware regions include the clock calls and a small amount of user-space
control/boundary code. Three groups have slightly different boundaries. Wall time
brackets the original uninstrumented algorithm invocation, including its allocations
and, for delta-stepping, OpenMP runtime work. No overhead subtraction or claim of
perfectly identical timing/counter intervals is made. Short chain inputs are useful
for a demo of behavior, not stable performance inference. Run repeated experiments
on suitable larger deterministic inputs and retain manifests and conditions before
drawing any architectural conclusions.

## JSON contract (additive schema version 1)

Existing `algorithm`, `source`, `vertices`, `edges`, `delta`, `requested_threads`,
`actual_threads`, `warmups`, `repetitions`, `verified`, `unit`, `samples` and
`metadata` fields remain. Additional fields are:

- `status`: `completed` means graph processing and verification succeeded; consult
  counter status independently.
- `median_wall_ns`: arithmetic midpoint of the central sorted samples for an even
  count; the central sample for an odd count. `samples` remains individual wall ns.
- `input_identity`: `fnv1a64-csr-le-u64-v1` fingerprint of the loaded graph. Serialize
  vertex count, edge count, then all CSR offsets, destinations and weights as
  unsigned 64-bit little-endian integers; hash bytes with standard FNV-1a 64.
  This is a deterministic, noncryptographic graph identity, not a file SHA-256.
  Retain the generator manifest for SHA-256, seeds, recipe and file provenance.
- `hardware_counters_requested`, `counter_status`, `measurement_scope`, `warnings`:
  explicit intent, overall availability and interpretation. Overall `partial`
  means some events are valid; `mixed` means repetition statuses differ. All
  unrequested events are `not_requested`; OpenMP events are `unsupported_scope`.
- `runs`: one entry per repetition, with index, wall ns, counter status, six counter
  records and derived IPC/CPI/cache/branch ratios.
- Each counter record contains `status`, `errno`, `diagnostic`, `raw`,
  `time_enabled_ns`, `time_running_ns` and `value`. Numeric fields are null when
  unavailable; real measured zero counts remain zero. `value` is a double (possibly
  scaled), while raw counts/times are uint64 JSON integers; consumers must avoid
  rounding raw integers through a narrow JSON number representation.
- `metadata` adds configure-time Git revision/dirty state and compiler flags to CPU,
  compiler and build-type information. Reconfigure after source changes; these
  fields describe configure time and do not hash the executable. `--cpu` retains
  `hardware_counters_available: null`; use the explicit diagnostic/profiling fields
  for real availability rather than treating platform metadata as a PMU probe.

Overall and per-event statuses are documented in [PERFORMANCE_COUNTERS.md](PERFORMANCE_COUNTERS.md).
Derived ratios use only valid same-group operands; missing operands and zero
denominators are null. Hardware values are never inferred from software timing.

In a denied environment a completed run can correctly have
`counter_status: "permission_denied"`, every `value: null` and every derived
metric null, while retaining valid wall samples and successful verification.
Hardware readings must not be compared to unsupported OpenMP counters as if both
were complete. Live demonstrations can show diagnostics, permission fallback,
correctness agreement and wall timing even when PMU access is unavailable.
