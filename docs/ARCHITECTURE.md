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
of zero means the C++ runtime could not determine it. Phase 4 adds explicit
affinity, visible physical topology and quota discovery; these do not establish
exclusive resources or runtime library version.

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
Phase 4 adds thread scaling and kernel affinity experiments below; Phase 5 adds the visualization layer below.


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

## Phase 4 multicore experiments

`multicore.hpp`, `analysis/topology.cpp` and `experiments/multicore.cpp` add
Linux affinity/sysfs/cgroup discovery, conservative thread validation, deterministic
randomized complete blocks, descriptive statistics, scaling arithmetic and
versioned JSON/CSV. The original delta-stepping loop is preserved; an optional
team-size output store avoids enabling software edge counters. Dijkstra is the
untimed oracle, and one-thread delta-stepping is the speedup baseline.

Dedicated scheduling/synchronization kernels preserve useful work and validate
checksums while comparing static/dynamic chunks, reductions, atomics and critical
sections. Worker-local affinity RAII verifies and restores optional bindings.
The scaling command records external OpenMP placement without claiming binding
verification. Hardware counter worker aggregation remains unsupported. See
[MULTICORE_ARCHITECTURE.md](MULTICORE_ARCHITECTURE.md) and
[SCALING_EXPERIMENTS.md](SCALING_EXPERIMENTS.md) for boundaries and limitations.

## Phase 5 optional analytics dashboard

`dashboard/app.py` is a local Streamlit entrypoint; `views.py` presents seven
navigation views. `components/ui.py` handles reusable provenance, facts and filters.
`charts/` contains CPU, memory, locality, scaling and theoretical Amdahl Plotly
figures. `data/schemas.py`, `validation.py` and `loader.py` recognize bounded
producer contracts and a checksum-checked repository-local catalog; uploads are
bytes, never paths or executable objects. `transform.py` isolates pure calculations,
compatibility fingerprints, null-aware counters and non-pooled grouping.
`export.py` provides deterministic formula-safe CSV and lossless JSON selections.

The original producer document remains intact, including unknown fields and uint64
integers. Diagnostic PMU probes are excluded; failed events remain null; IPC/CPI
require validated same-group values and scheduling metadata. Wall time is distinct
from counts, memory accounting from whole-process RSS, and theory from observations.
Multicore ratios require complete measured blocks and the correct same-algorithm
baseline. Standalone producer CSV lacks provenance, so it enables raw inspection
without speedup inference. Explicit locality comparisons use compatibility checks
and separate configuration traces; documents are never silently pooled.

`requirements-dashboard.txt`, `.streamlit/config.toml`, pytest tests and a separate
GitHub Actions dashboard workflow are optional. CMake, graph algorithms, imported
headers and existing CTests are unchanged. Demo sources reuse committed Phase 2/4
receipts plus actual Phase 3-style CLI captures under `docs/validation/phase5/`.
See [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) for the complete import/trust contract.

## Phase 6 academic delivery and read-only evidence analysis

`docs/academic/` consolidates the implemented system without changing engine or
dashboard algorithms. Standard-library audit/results/demo scripts verify immutable
receipts, derive non-pooled tables and capture fresh demo outputs into new directories.
Optional Matplotlib and python-pptx scripts export scientific figures and an editable
notes-bearing deck. Mermaid syntax and delivery checks complement the unchanged
CMake/CTest/pytest workflows. Requirements for authoring are separate from the core
and UI. See [academic index](academic/README.md) and [final validation](academic/FINAL_VALIDATION.md).

The import manifest remains historical; a final audit records the documented Phase 4
team-observation extension. No new license grant, browser rendering verification,
independent-core scaling or PMU fidelity is inferred from the academic package.
