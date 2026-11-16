# Phase 3 validation

Executed locally on 2026-11-16. The feature branch starts from latest fetched main
`c14b369130cabb4acbfffa9a4df1e85373cc98c3` (Phase 2 merge). The imported CSR,
Dijkstra, delta-stepping, all previous test sources and import provenance remain
unchanged. DynaGraph-HPC was not modified. The only change to the original static
benchmark exposes its existing fingerprint helper for reuse, without changing its
byte encoding, output schema or algorithm boundaries.

## Implementation files

Created `include/archgraph/{cache,experiments,identity,layout}.hpp`,
`src/analysis/cache.cpp`, and `src/experiments/{cli.cpp,commands.cpp,layout.cpp,
locality.cpp,runner.hpp}`. New tests are `test_layout.cpp`, `test_locality.cpp`,
`test_cache.cpp`, `test_memory_perf.cpp`, `test_memory_hardware.cpp` and
`test_memory_experiments.py`. Created CACHE_HIERARCHY.md, MEMORY_ORGANIZATION.md,
LOCALITY_EXPERIMENTS.md, this validation report and ten small build/test receipts.

Updated CMakeLists.txt, tests/CMakeLists.txt, apps/archgraph.cpp,
include/archgraph/perf.hpp, src/profiling/perf.cpp, src/benchmark/static.cpp,
README.md, ARCHITECTURE.md, COA_CONCEPT_MAPPING.md and ROADMAP.md. Existing CI
needs no workflow change because it builds/runs the CMake-registered tests.

## Builds and exact outcomes

GCC 13.3.0, CMake 3.28.3, Python 3.14.2, OpenMP 4.5, Linux x86_64. CPU metadata
reported AMD EPYC 9V74 80-Core Processor; affinity exposed two logical processors.
This is a shared/virtualized environment, not exclusive physical-core allocation.

| Final configuration | Registered | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Clean Debug, strict warnings | 23 | 21 | 0 | 2 hardware |
| Clean Release, strict warnings | 23 | 21 | 0 | 2 hardware |
| ASan + UBSan + leak detection | 23 | 21 | 0 | 2 hardware |

Final suites total **63 passed, 0 failed, 6 hardware skips**. Hardware skips are not
counted as passes. All 17 earlier registered tests are retained; Phase 3 adds four
native tests (`layout`, `locality`, `cache`, `memory_perf`), Python `memory_experiments`
and optional `memory_hardware`. With hardware tests disabled, 21 tests register.
Five Python suites contain 32 unittest methods per configuration (22 artifact,
1 loader, 2 original benchmark, 2 Phase 2 profiling, 5 Phase 3 experiment methods),
nested within the CTest counts. Native assertions/cases are not separate CTests.
A final verbose Debug rerun of Python and hardware tests passed five and skipped
two, with zero failures; this is additional execution, not additional coverage.

Debug and Release were built in new build directories and also rebuilt with
`--clean-first` after the last implementation changes. All final builds were clean
under `-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror`. Initial compile-time
type mismatches were corrected before final verification. No previous test was
weakened. [Build and test receipts](validation/phase3/) retain the final outcomes.
Sanitizers ran outside the sandbox with leak detection enabled because Phase 2
already established that sandbox thread-inspection restrictions prevent LSan.
No suppression or security setting was changed. Hosted CI was not executed here;
existing CMake/CI registration automatically includes the new tests.

```sh
cmake -S . -B build/phase3-debug -DCMAKE_BUILD_TYPE=Debug \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase3-debug --clean-first --parallel 2
ctest --test-dir build/phase3-debug --output-on-failure
cmake -S . -B build/phase3-release -DCMAKE_BUILD_TYPE=Release \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase3-release --clean-first --parallel 2
ctest --test-dir build/phase3-release --output-on-failure
cmake -S . -B build/phase3-sanitize -DCMAKE_BUILD_TYPE=Debug \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined -no-pie'
cmake --build build/phase3-sanitize --parallel 2
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 \
  ctest --test-dir build/phase3-sanitize --output-on-failure
```

## Correctness and reproducibility evidence

- Exact CSR/adjacency/CSR round trips compare offsets, destinations and weights.
  All-source shortest paths match both baseline Dijkstra and independent
  Bellman–Ford on 30 seeded graphs plus empty, disconnected, zero-weight,
  self-loop and maximum-weight cases. Duplicate edges remain rejected with either
  equal or differing weights. Empty graphs support memory/traversal; invalid SSSP
  sources still fail.
- Memory tests verify actual capacities, control storage, payload and allocation
  counts, and explicit null allocator/physical attribution. RSS is process-wide.
- Sequence tests verify permutations even for noncoprime and oversized strides,
  deterministic seeds, complete/partial cycles, wrapped checksums and invalid input.
  Python independently computes the SplitMix64/Fisher–Yates fingerprint and expected
  array checksum. Repeated command runs match parameters, fingerprints and checksums;
  no test requires identical timing.
- Metadata fixtures cover complete, partial, malformed and missing cache information,
  explicit/fallback planning, half/near/double capacity targets and reported omissions.
- Memory PMU tests check Linux encodings, shared group/scaling/cleanup paths,
  permission fallback, invalid reads and null ratios through an injected backend.
  All Phase 2 tests remain unchanged, retaining their broader syscall-error coverage.
- JSON tests validate schema, counts, medians, consumed results, per-event nulls,
  derived-ratio gating, graph identities and previous CLI behavior. All new commands
  have help checks and malformed, duplicate, unknown and inapplicable option checks.
- Original sequential/parallel correctness, CLI boundary tests, deterministic
  generator goldens and graph-loader tests all passed unchanged.

## Actual environment and benchmark observations

All commands in MEMORY_ORGANIZATION.md, CACHE_HIERARCHY.md and
LOCALITY_EXPERIMENTS.md were executed successfully and produced parseable JSON.
Generation/manifest verification, both layout comparisons, all five spatial graph/
array patterns, both temporal working sets, metadata-derived and explicit-size cache
studies, help/version/CPU and earlier commands were exercised directly or by retained
tests. Full outputs and generated inputs remain locally under ignored `results/phase3-demo`
and `data/phase3-*`; they are not required by tests and are not committed as portable
or authoritative performance results. The small tables below are retained solely as
honest smoke-test observations, not benchmark conclusions.

The cache snapshot for logical CPU 0 reported:

| Type | Level | Capacity | Line bytes | Reported sharing |
| --- | ---: | ---: | ---: | --- |
| Data | 1 | 32 KiB | 64 | 0-1 |
| Instruction | 1 | 32 KiB | 64 | 0-1 |
| Unified | 2 | 1 MiB | 64 | 0-1 |
| Unified | 3 | 32 MiB | 64 | 0-1 |

These are OS metadata, not verified physical-cache capacities available exclusively
to the process. The automatic plan selected nine data sizes from 16 KiB through
64 MiB, with zero omitted targets. Each size used 8,388,608 data reads and the same
number of index reads per trial, three repetitions, one warmup and seed 1. Index
storage adds 50% of active data bytes. Medians were nonmonotonic, ranging from
15,994,016 ns to 172,772,785 ns. This does not demonstrate a cache-level transition.

All six requested L1D/LL/DTLB event opens were `permission_denied` (EACCES/13 in
sandboxed probes); `perf_event_paranoid` was 4. Hardware numeric/derived values were
null. Both optional hardware tests returned explicit skip code 77. Successful mock
contracts do not establish permitted-host PMU fidelity or real cache-miss values.

Release smoke observations (three repetitions, one warmup, seed 1):

| Experiment | Reads or edge visits per trial | Median wall ns |
| --- | ---: | ---: |
| 1 MiB sequential indexed array | 131,072 data + 131,072 index | 125,807 |
| 1 MiB strided indexed array, stride 16 | 131,072 data + 131,072 index | 181,500 |
| 1 MiB random indexed array | 131,072 data + 131,072 index | 220,278 |
| 1 MiB allocation, 4 KiB temporal prefix | 1,048,576 data + 1,048,576 index | 1,042,591 |
| 1 MiB allocation, 1 MiB temporal prefix | 1,048,576 data + 1,048,576 index | 1,720,491 |

The three spatial checksums were identical: `9573378334292377600`. This validates
consumption/equal full-sweep sums, not equal instructions or any measured cache-hit
ratio. Tiny-chain graph traversals both visited 21 edges (three passes over seven
edges) and produced checksum `360777253350`; their tiny timings are not useful for
performance inference.

For the deterministic eight-vertex chain, useful edge payload was 56 bytes in both
layouts. Accounted totals were CSR 200 bytes (three vector buffers) and adjacency
280 bytes (eight vector buffers), excluding unknown allocator overhead. Neither is
physical RSS. A larger 128x128 bidirectional grid had 16,384 vertices and 65,024
edges; complete SSSP vectors matched. Medians were 4,012,222 ns CSR and 3,925,343 ns
adjacency. Fixed order, tiny sample count and shared environment preclude a speedup
claim. The graph file SHA-256 was
`7723913cc25a6507797ce31dc6d23290fda057f649dc4d3270e24d7a26523215`.

To reproduce that optional grid recipe after generating the chain:

```sh
python3 - <<'PY'
import json
from pathlib import Path
spec = json.loads(Path('benchmarks/configs/chain-v1.json').read_text())
spec['workload_id'] = 'phase3-grid-demo'
spec['graph'] = {'family':'grid','rows':128,'columns':128,'bidirectional':True}
Path('data/phase3-grid-spec.json').write_text(json.dumps(spec)+'\n')
PY
python3 -B benchmarks/python/generate.py generate --spec data/phase3-grid-spec.json --output data/phase3-grid
python3 -B benchmarks/python/generate.py verify --manifest data/phase3-grid/manifest.json
build/phase3-release/archgraph compare-layouts --input data/phase3-grid/graph.txt \
  --source 0 --runs 3 --hardware-counters
```

Timing values will vary; reproducibility means deterministic inputs, parameters,
checksums and verification, not identical elapsed durations. Configure-time build
metadata accurately recorded the main base revision and dirty=true for these local
precommit binaries. Reconfigure after changes to refresh that metadata.

## Known limitations

No cold-cache guarantee, per-level timing attribution, controlled bandwidth/NUMA
study, worker PMU aggregation, exclusive-core ownership, verified virtualization
fidelity, race-freedom claim or cross-platform compiler validation is established.
Array index storage and scalar volatile accesses change the workload relative to
an optimized direct scan. Graph and array kernels do different work. Layout SSSP
runs have fixed order, both layouts coexist, and allocator/physical memory cannot
be attributed per layout from RSS. Unsupported PMU metrics remain null. No large
generated input or raw machine-specific run is committed as an authoritative result.
