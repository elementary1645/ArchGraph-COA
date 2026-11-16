# ArchGraph-COA

A C++17/OpenMP CPU Architecture-Aware Graph Processing and Performance Analyzer.
Phase 2 extends the validated graph engine with optional Linux hardware counters
for sequential Dijkstra: cycles, instructions, generic cache and branch events,
and valid derived ratios. Repeated verified wall timing works for both algorithms,
including environments that deny counter access. No speedup claim is made.

The graph engine is imported from [DynaGraph-HPC](https://github.com/elementary1645/Dynagraph-HPC)
at `1b5eaea38e4fdfb203ea4214f79f05c8e909c7e9`; see
[provenance](docs/IMPORT_PROVENANCE.md) for attribution, file hashes and licensing status.
The original `dynagraph` C++ namespace is retained to minimize algorithm changes.

Requires CMake >=3.21, a C++17 compiler with OpenMP and Threads support, and
Python >=3.8 for tests and deterministic generation. No downloaded build dependencies,
source checkout or submodule is needed. GCC is validated; hosted CI is configured
for Ubuntu Debug and Release.

```sh
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DARCHGRAPH_WARNINGS_AS_ERRORS=ON
cmake --build build/release --parallel 2
ctest --test-dir build/release --output-on-failure
python3 -B benchmarks/python/generate.py generate --spec benchmarks/configs/chain-v1.json --output data/chain
python3 -B benchmarks/python/generate.py verify --manifest data/chain/manifest.json
build/release/archgraph --help
build/release/archgraph --version
build/release/archgraph --cpu
build/release/archgraph sssp --input data/chain/graph.txt --source 0 --algorithm dijkstra
build/release/archgraph sssp --input data/chain/graph.txt --source 0 --algorithm delta-stepping --delta 16 --threads 2
build/release/archgraph bench --input data/chain/graph.txt --source 0 --algorithm dijkstra --warmups 1 --repetitions 5
build/release/archgraph bench --input data/chain/graph.txt --source 0 --algorithm delta-stepping --delta 16 --threads 2 --warmups 1 --repetitions 5
```

Generation requires a new output directory. Bundles retain the upstream graph,
seed and manifest format, including unused update traces for format compatibility;
The current engine executes only static graphs. Repeating the same specification produces
identical graph/trace bytes and fingerprints. Save the manifest alongside results.
Library-only builds can use `-DBUILD_TESTING=OFF` without Python.

Graph files begin with `V E`, followed by exactly E records `source destination weight`.
Vertices are zero-based, edges directed, weights uint32 nonnegative integers;
comments are unsupported. Invalid graphs/options produce diagnostics and status 2.
Distances are uint64; unreachable vertices appear as JSON `null`.
SSSP JSON includes the actual OpenMP team size for delta-stepping.

Benchmark JSON contains individual `wall_ns` samples, configuration, verification,
and observed metadata. Loading, reference Dijkstra, warmups, verification and JSON
serialization are outside measured regions; allocation inside the algorithm is
included. Actual timed team size is unavailable because instrumentation is disabled.
Timing includes scheduler/runtime overhead; CPU hints do not imply exclusive cores.
No historical DynaGraph benchmark results are presented as ArchGraph measurements.

Optional profiling (the graph bundle above must exist):

```sh
build/release/archgraph --counter-diagnostics
build/release/archgraph bench --input data/chain/graph.txt --source 0 --algorithm dijkstra --repetitions 10 --hardware-counters
```

`--hardware-counters` reports per-event status and nulls when access is denied.
Delta-stepping hardware counters return `unsupported_scope`; OpenMP aggregation
is deferred. Wall time and correctness checks continue. Benchmarks now include
median wall ns, individual runs, a deterministic CSR fingerprint, raw scheduling
information, derived ratios and configure-time build provenance. Generic cache
events are not separate L1/L2/L3 measurements. No root access or permission changes
are needed. For optional real-PMU tests, configure with
`-DARCHGRAPH_HARDWARE_TESTS=ON`; inaccessible hardware is explicitly skipped.

See [CPU profiling](docs/CPU_PROFILING.md), [counter definitions](docs/PERFORMANCE_COUNTERS.md),
[architecture](docs/ARCHITECTURE.md), [COA mapping](docs/COA_CONCEPT_MAPPING.md),
[validation](docs/VALIDATION.md) and [roadmap](docs/ROADMAP.md).

Repository layout:

```text
.github/workflows/ci.yml       Debug/Release CI
apps/archgraph.cpp            CLI
include/archgraph/            analysis and benchmark interfaces
include/dynagraph/            retained graph-engine interfaces
src/graph/                    CSR and loading
src/algorithms/               Dijkstra and delta-stepping
src/instrumentation/          retained optional diagnostic dependencies
src/analysis/                 CPU/build metadata
src/profiling/                Linux PMU counters and diagnostics
src/benchmark/                static wall-clock experiments
benchmarks/python/            deterministic generation and verification
benchmarks/configs/            chain recipe
tests/                        native, CLI and Python tests
docs/                         architecture, provenance, roadmap and validation
docs/validation/              local build/test receipts
```
