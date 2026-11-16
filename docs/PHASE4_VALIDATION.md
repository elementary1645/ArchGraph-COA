# Phase 4 validation

Validation date: 16 November 2026. Branch: `feature/phase4-multicore-analysis`,
created from freshly fetched main `0fa39363775133feb1dae9480ca4852881d059c6`.
The initial worktree was clean. Only ArchGraph-COA was modified; DynaGraph-HPC
was not accessed or changed. No merge or pull request was created.

## Implemented and inspected

Reviewed the imported lazy-heap Dijkstra and persistent-team delta-stepping,
Phase 2 caller-only PMU limitations, Phase 3 experiment runner, CLI, generator,
cache/locality boundaries and fixed-order limitations. Reused these components
rather than replacing algorithms. Delta-stepping now optionally writes actual
team size after its existing team exits, without enabling software edge counters.

CPU reporting adds sparse affinity masks, physical package/core/sibling records,
visible cgroup v1/v2 ancestor quotas, explicit unknown values, OpenMP limits and
conservative concurrency policy. Scaling adds seeded complete randomized blocks,
warmup records, full correctness checks, same-algorithm speedup, efficiency and
explicitly theoretical Amdahl assumptions. Dedicated checksum kernels compare
static/dynamic scheduling, chunk sizes and reduction/atomic/critical strategies;
optional worker binding is verified and restored. JSON schema v1 and raw CSV
exports retain all samples. No caller-only multicore PMU totals are collected.

## Environment

GCC 13.3.0, C++17, OpenMP specification 201511; executable links GNU
`libgomp.so.1`. Runtime library version is unavailable in portable JSON.
Reported CPU model: AMD EPYC 7763 64-Core Processor. This model string is not an
allocation description. Visible Linux topology reports:

- 2 online logical CPUs, available affinity IDs `[0,1]`.
- 1 physical core and 1 package in that mask; exposed SMT siblings.
- No additional restriction between online CPUs and caller mask.
- Visible cgroup quota `max 100000` (unlimited_visible), quota_cpus null.
- OpenMP default maximum 2; thread limit 2147483647 outside test overrides.
- Safe default logical thread counts: 1 and 2. Higher counts require explicit
  `--allow-oversubscription`, warn, and may still be reduced by runtime limits.

Only one physical core is exposed; **this environment cannot establish scaling
across independent physical cores**. Virtualization/topology fidelity, host
sharing, hidden quotas, frequencies and dedicated resources are unverified.
Topology describes visible records, not proof of exclusive hardware.

## Build and tests

Clean Debug and Release builds used `ARCHGRAPH_WARNINGS_AS_ERRORS=ON` and
`ARCHGRAPH_HARDWARE_TESTS=ON`; final incremental rebuilds verify the final clock
implementation. Both strict builds passed. Compile options include `-Wall
-Wextra -Wpedantic -Wconversion -Wshadow -Werror`.

ASan/UBSan Debug used `-fsanitize=address,undefined -fno-omit-frame-pointer
-fno-pie` and linker `-fsanitize=address,undefined -no-pie`. The initial sandbox
attempt failed because LeakSanitizer cannot operate under tracing; its diagnostics
are retained in `sanitize-sandbox-attempt.log`. The final run outside that tracing
restriction used `ASAN_OPTIONS=detect_leaks=1` and `UBSAN_OPTIONS=halt_on_error=1`
and passed, including leak detection. No sanitizer finding was observed in that run.

| Final configuration | Passed | Failed | Skipped | Registered |
| --- | ---: | ---: | ---: | ---: |
| Debug | 24 | 0 | 2 | 26 |
| Release | 24 | 0 | 2 | 26 |
| ASan + UBSan + LSan | 24 | 0 | 2 | 26 |

The two skips in each suite are `perf_hardware` and `memory_hardware`: PMU access
is unavailable. `multicore_hardware` passed with observed two-worker teams and
verified/restored binding. It explicitly skips on insufficient capacity or runtime
support and makes no performance claim.

All previous CTests passed, including core algorithms, independent shortest-path
oracles, workload artifacts/loader and Python benchmark/profiling/memory suites.
The new deterministic unit tests cover sparse/malformed CPU lists, v1/v2 quotas,
fractional and ancestor limits, missing topology, thread validation, oversubscription,
speedup/efficiency/Amdahl boundaries, invalid timings, seeded balanced schedules,
and in-process affinity/OpenMP configuration restoration. Python integration tests
cover complete vector equivalence, warmups, schema-required fields/types/ranges,
CSV row equality, reproducible order, invalid CLI inputs, every kernel checksum,
and runtime team reduction with null scaling ratios. They use tiny workloads and
do not require dedicated multicore hardware. JSON validation uses a standard-library
validator for the keywords used by the checked-in schema, not an external package.

## Actual Release observations

These are descriptive shared-environment samples, not statistically significant
or controlled physical-multicore results. Builds/tests had stopped before the
benchmark observation run. Graph: deterministic 128x128 bidirectional grid,
16,384 vertices and 65,024 edges; source 0, delta 16, generated weights 16–32.
Seeded trial order 42, 15 measured blocks and 2 warmup blocks per configuration.
All 34 scaling calls matched Dijkstra's full source and distance vector.
Requested/observed teams were consistently 1/1 and 2/2.

| Threads | Median ms | Min ms | Max ms | MAD ms | Speedup | Efficiency |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3.512313 | 3.448333 | 14.749020 | 0.057297 | 1.0000 | 1.0000 |
| 2 | 2.690738 | 2.425492 | 10.924383 | 0.265246 | 1.3053 | 0.6527 |

Amdahl f=0.95 predicts 1.904762 at p=2; f is assumed, not inferred.
Large maxima and shared/SMT resources limit interpretation of the median ratios.
Graph file SHA-256: `7723913cc25a6507797ce31dc6d23290fda057f649dc4d3270e24d7a26523215`. The committed
`graph-provenance.json` contains the complete deterministic generator spec and
manifest, including file provenance; no generated graph needs to be committed.

To regenerate the exact graph from the saved recipe:

```sh
python3 - <<'PYRECIPE'
import json
from pathlib import Path
p = json.loads(Path('docs/validation/phase4/graph-provenance.json').read_text())
Path('/tmp/phase4-grid-spec.json').write_text(json.dumps(p['spec']) + '\n')
PYRECIPE
python3 -B benchmarks/python/generate.py generate --spec /tmp/phase4-grid-spec.json --output /tmp/phase4-grid
build/phase4-release/archgraph scaling --input /tmp/phase4-grid/graph.txt --source 0 --delta 16 --threads 1,2 --repetitions 15 --warmups 2 --seed 42 --hardware-counters --csv /tmp/phase4-scaling.csv
```


Kernel run: 65,536 elements, irregular deterministic transformation, chunks 1/64,
all four synchronization/scheduling strategies, threads 1/2, seed 42, 15 measured
and 2 warmup blocks: 272 total calls. All checksums matched; every compact worker
binding and restoration was verified. Kernel timings exclude allocation, team
creation and binding; graph timings include algorithm allocations and team startup.
Raw summaries in `kernels.json` describe combined workload/dispatch/synchronization
costs and are not isolated overhead estimates.

## Reproduction and artifacts

Use [SCALING_EXPERIMENTS.md](SCALING_EXPERIMENTS.md) for the live demonstration,
[MULTICORE_ARCHITECTURE.md](MULTICORE_ARCHITECTURE.md) for discovery/binding scope
and [AMDAHLS_LAW.md](AMDAHLS_LAW.md) for arithmetic assumptions.

```sh
cmake -S . -B build/phase4-debug -DCMAKE_BUILD_TYPE=Debug -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase4-debug --clean-first --parallel 2
ctest --test-dir build/phase4-debug --output-on-failure
# Repeat with build/phase4-release and CMAKE_BUILD_TYPE=Release.
cmake -S . -B build/phase4-sanitize -DCMAKE_BUILD_TYPE=Debug \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined -no-pie'
cmake --build build/phase4-sanitize --parallel 2
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ctest --test-dir build/phase4-sanitize --output-on-failure
```

`docs/validation/phase4/` contains configure/build/final-build/test logs for all
three configurations, the failed sandbox sanitizer attempt, CPU JSON, scaling and
kernel JSON/CSV, graph provenance/verification and a text summary. CMake's build metadata records
the main base revision and dirty=true for these precommit builds. Reconfigure after
checkout/commit to refresh revision metadata; elapsed durations are not reproducible
constants. Tests validate contracts, not repeatability of wall times.

## Files created and modified

Created:

- `include/archgraph/multicore.hpp`
- `src/analysis/topology.cpp`, `src/experiments/multicore.cpp`
- `tests/test_multicore.cpp`, `tests/test_multicore.py`, `tests/test_multicore_hardware.py`
- `docs/MULTICORE_ARCHITECTURE.md`, `docs/SCALING_EXPERIMENTS.md`,
  `docs/AMDAHLS_LAW.md`, `docs/PHASE4_VALIDATION.md`, `docs/multicore-v1.schema.json`
- Evidence files under `docs/validation/phase4/` as listed above.

Modified:

- `CMakeLists.txt`, `tests/CMakeLists.txt`, `apps/archgraph.cpp`
- `include/dynagraph/algorithms/delta_stepping.hpp`, `src/algorithms/delta_stepping.cpp`
- `src/analysis/cpu.cpp`, `README.md`, `docs/ARCHITECTURE.md`,
  `docs/COA_CONCEPT_MAPPING.md`, `docs/ROADMAP.md`

## Remaining limitations

OpenMP worker PMU aggregation is unsupported; requested counters remain
unsupported_scope/null. Cgroup detection uses standard Linux mount locations;
hidden/nonstandard ancestors cannot be ruled out. No root privileges, system-wide
settings, production races, cold-cache protocol, NUMA placement or frequency
controls are introduced. Portable physical-topology/binding fields can be
unavailable. Kernel compact binding is verified; scaling supports external runtime
placement only and explicitly rejects compact binding. Library ABI consumers must
rebuild for the extended options structure; existing source aggregate initializers
retain their meaning. No cross-platform compiler, race-detector or statistical
significance claim is established. Professor-facing examples explain these limits.
