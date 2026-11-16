# Architecture

## Graph engine (implemented)

`include/dynagraph/graph` and `src/graph` own validated CSR offsets, destinations,
weights and stable edge IDs. The loader validates counts, endpoint bounds and
numeric syntax. Topology is fixed; the retained storage API supports weight
replacement between queries. No concurrent mutation is supported.

`src/algorithms/dijkstra.cpp` is the unchanged lazy-heap correctness baseline.
Its uint64 distances represent every supported simple shortest path; the reserved
maximum value denotes unreachable. Tests use an independent synchronous
Bellman–Ford oracle over input records, including seeded graphs and boundary cases.

`delta_stepping.cpp` retains the original persistent OpenMP team, atomic label
relaxation, explicit bucket synchronization, exception containment and optional
software work counters. Delta must be positive. Worker requests can differ from
actual teams. `instrumentation/workload` and `resources` remain because the unchanged
parallel implementation references them; they are optional diagnostics, not hardware
performance counters. Adaptive and incremental SSSP are excluded.

## Architecture analysis (implemented)

`src/analysis/cpu.cpp` reports CPU model from Linux `/proc/cpuinfo` where available,
logical concurrency hint, OpenMP configuration/specification, compiler and build type.
Unknown CPU model and hardware-counter availability are null. A concurrency hint
of zero means the C++ runtime could not determine it. These facts do not establish
physical-core count, affinity, exclusivity or runtime library version.

## Experiment framework (implemented)

`src/benchmark/static.cpp` runs static queries with preallocated sample storage.
Each measured region brackets exactly one uninstrumented public algorithm call with
`std::chrono::steady_clock`; duration conversion yields wall nanoseconds, not CPU
cycles. A reference Dijkstra result is computed once outside timing. All warmups
and measured results must match its complete distance vector before any result
JSON is emitted. Result destruction, checks and output are outside the brackets;
algorithm allocation, scheduling and OpenMP startup remain inside.

The CLI in `apps/archgraph.cpp` handles strict option parsing and loading. Repetition
counts are bounded to 1–10000 and warmups to 0–10000. Results preserve individual
samples without inferring statistical confidence or speedup. Timed actual team
size is null rather than inferred from the request. Graph fingerprints and generator
seeds live in the deterministic bundle manifest; save it with benchmark output.
`benchmarks/python` retains the upstream standard-library generator and hash/recipe
verification. Traces are generated and tested for compatibility, never applied by
this Phase 1 engine. CTest covers core, CLI, generator/loader and measurement contracts.

## Future interfaces

Phase 2 adds `include/archgraph/perf.hpp` and `src/profiling/perf.cpp`: a Linux
perf_event_open backend, injectable syscall boundary, descriptor-owning sessions,
three event-pair groups, validation/scaling and diagnostic JSON. Static benchmarks
optionally collect calling-thread user-space counters for sequential Dijkstra;
OpenMP hardware aggregation remains unsupported. Median wall time, per-run counter
records, loaded-CSR identity and build provenance extend the existing JSON format.
See CPU_PROFILING.md and PERFORMANCE_COUNTERS.md for exact scopes and boundaries.
Affinity-aware scaling and visualization remain future work.


## Phase 3 cache and memory experiments

`include/archgraph/layout.hpp` and `src/experiments/layout.cpp` add a vector-of-vectors
adjacency list, deterministic CSR conversion, explicit storage accounting and an
isolated adapter of the imported lazy-heap Dijkstra loop. Imported algorithm and
CSR sources remain unchanged; full outputs are checked against the baseline and
independent test oracles. Duplicate edges remain rejected in both representations.

`src/analysis/cache.cpp` discovers per-CPU sysfs cache metadata and creates bounded
half/near/double-capacity data-array plans with explicit/fallback size support.
`src/experiments/locality.cpp` creates reproducible permutations and read-only
checksum kernels. `runner.hpp` brackets kernels with the existing monotonic clock
and optional Phase 2 RAII sessions, validates results outside timing and records
individual trials/medians. `commands.cpp` builds versioned experiment JSON and
`cli.cpp` handles strict options separately. Phase 2 graph identity is now shared
through `identity.hpp`, with its byte encoding unchanged.

The perf backend accepts a separate memory event set (L1D, last-level and DTLB
read/access-miss pairs) through the existing grouping/error/scaling/cleanup path.
Generic Phase 2 defaults and old schemas remain unchanged. All Phase 3 kernels
are single-threaded; elapsed time and counted activity retain distinct scopes.
See MEMORY_ORGANIZATION.md, CACHE_HIERARCHY.md and LOCALITY_EXPERIMENTS.md for
accounting, setup boundaries, schema and interpretation limits.
