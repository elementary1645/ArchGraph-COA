# ArchGraph-COA

**CPU Architecture-Aware Graph Processing and Performance Analysis** — a
fifth-semester Computer Organization and Architecture project in C++17/OpenMP
with an optional Python analytics dashboard.

The project uses correct graph workloads to investigate instruction metrics,
memory layout, cache/locality opportunities and thread overhead. It records real
wall timing and available hardware events with explicit scope, provenance and
unavailable states. It does not infer cache misses from elapsed time or treat
shared-host SMT observations as controlled physical multicore scaling.

**Final academic materials:** [delivery index](docs/academic/README.md),
[project report](docs/academic/PROJECT_REPORT.md), [editable slides](docs/academic/PRESENTATION.pptx),
[demo](docs/academic/LIVE_DEMO.md), [60 viva answers](docs/academic/VIVA_QA.md),
[final verification](docs/academic/FINAL_VALIDATION.md).

**Licensing:** the selectively imported DynaGraph-HPC source is attributed to
commit `1b5eaea38e4fdfb203ea4214f79f05c8e909c7e9`. No upstream license grant was
recorded. Preserve [attribution](docs/IMPORT_PROVENANCE.md) and resolve
[licensing clearance](docs/academic/LICENSING.md) before claiming unrestricted
redistribution or an open-source license. No institutional approval is asserted.

## Problem and features

A graph algorithm's complexity alone does not explain CPU execution time. Loads,
branches, data representation, translation, scheduling and synchronization matter.
ArchGraph connects these COA concepts to reproducible, verified experiments:

| Feature | Implemented behavior |
| --- | --- |
| Correct graph processing | Strict directed weighted edge-list loader, CSR, lazy-heap Dijkstra, OpenMP delta-stepping and independent test oracles |
| CPU instrumentation | Repeated steady-clock timing; optional Linux calling-thread PMU pairs; validated multiplexing and honest null/status fallback |
| Memory/cache/locality | CSR/adjacency accounting, matched-output queries, indexed spatial/temporal kernels and metadata-sized working-set studies |
| Multicore analysis | Topology/mask/quota discovery, observed teams, seeded randomized blocks, correct baseline speedup/efficiency and dedicated synchronization kernels |
| Local dashboard | Seven Streamlit/Pandas/Plotly views, 13 authentic archived receipts, bounded JSON/CSV imports, filters and reproducible exports |
| Academic package | Report, seven diagrams, 15-slide notes/PPTX, scientific figures, 60 viva answers, fresh-output scripts and evaluation |

## Architecture and COA mapping

Deterministic graph specification → generator/manifest → validated C++ engine →
verified JSON/supported CSV → safe dashboard adapters → charts and exports.
The dashboard reads results; it does not execute uploads or launch benchmarks.
See [architecture](docs/ARCHITECTURE.md) and [seven diagrams](docs/academic/ARCHITECTURE_DIAGRAMS.md).

| COA topic | Project connection |
| --- | --- |
| Instructions and cycles | Optional real event pairs and same-scope IPC/CPI, distinct from software work and wall time |
| Memory organization | Contiguous CSR versus row-vector adjacency storage, capacity estimates and separate whole-process RSS |
| Cache hierarchy/locality | Spatial/temporal indexed reads, active working sets and metadata capacity markers, without unsupported miss attribution |
| Parallel execution | MIMD OpenMP teams, atomics/barriers, scheduling/reduction and physical/logical/SMT distinctions |
| Performance models | Same-algorithm median speedup, efficiency, descriptive variability and explicitly assumed Amdahl curves |

Full [COA concept mapping](docs/COA_CONCEPT_MAPPING.md) and [academic analysis](docs/academic/PROJECT_REPORT.md)
explain boundaries and actual results.

## Requirements and build

Core: CMake >=3.21, C++17 compiler, OpenMP and Threads runtime. Python >=3.8 is
used for core tests and generation; library-only builds can disable tests.
Validated platform: Linux x86_64/GCC. Dashboard: optional Python >=3.11 plus
`requirements-dashboard.txt`. Academic authoring: optional `requirements-academic.txt`.
No dashboard packages are required to compile or test the C++ engine.

From the repository root, using unused build directories for clean verification:

```sh
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/release --parallel 2
ctest --test-dir build/release --output-on-failure
build/release/archgraph --help
build/release/archgraph --version
build/release/archgraph --cpu
```

For Debug, use another directory and `-DCMAKE_BUILD_TYPE=Debug`.
`-DBUILD_TESTING=OFF` permits a core library/application build without Python tests.
Hardware tests explicitly skip when unavailable; a skip is not a measured event.

## Generate and run

Generation requires a new output directory. Bundles retain graph/trace seeds and
hash manifests; update traces are format-compatible artifacts, not replayed by
this static engine.

```sh
DEMO_PARENT=$(mktemp -d /tmp/archgraph-coa.XXXXXX)
python3 -B benchmarks/python/generate.py generate --spec benchmarks/configs/chain-v1.json --output "$DEMO_PARENT/graph"
python3 -B benchmarks/python/generate.py verify --manifest "$DEMO_PARENT/graph/manifest.json"
build/release/archgraph sssp --input "$DEMO_PARENT/graph/graph.txt" --source 0 --algorithm dijkstra
build/release/archgraph sssp --input "$DEMO_PARENT/graph/graph.txt" --source 0 --algorithm delta-stepping --delta 16 --threads 1
build/release/archgraph bench --input "$DEMO_PARENT/graph/graph.txt" --source 0 --algorithm dijkstra --repetitions 10 --hardware-counters
```

Input starts with `V E` and exactly E `source destination weight` records; vertices
are zero-based and weights are uint32 nonnegative. Invalid counts/numbers/endpoints
and duplicate directed edges are rejected. SSSP distances are uint64 with unreachable
values serialized as null. Delta-stepping requires positive delta.

Loading/oracle/verification/output are outside benchmark timing; graph algorithm
allocation and OpenMP startup are inside. Calling-thread PMU data for sequential
Dijkstra are not process-wide totals. Delta-stepping PMU aggregation is unsupported,
including one-thread requests. Wall timing continues with denied/unsupported events.

## Example experiments

```sh
build/release/archgraph memory --input "$DEMO_PARENT/graph/graph.txt"
build/release/archgraph compare-layouts --input "$DEMO_PARENT/graph/graph.txt" --source 0 --runs 5
build/release/archgraph locality --pattern sequential --size 1048576 --accesses 131072 --seed 42 --runs 5
build/release/archgraph locality --pattern random --size 1048576 --accesses 131072 --seed 42 --runs 5 --hardware-counters
build/release/archgraph locality --pattern temporal --size 1048576 --working-set 4096 --accesses 131072 --seed 42 --runs 5
build/release/archgraph cache-study --sizes 4096,32768,262144,1048576 --accesses 131072 --seed 42 --runs 5
build/release/archgraph scaling --input "$DEMO_PARENT/graph/graph.txt" --source 0 --threads 1 --repetitions 15 --csv "$DEMO_PARENT/scaling.csv"
```

Inspect topology before adding threads. Use `--threads 1,2` only within the safe
CPU/quota/runtime ceiling; explicit oversubscription warns. Scaling inserts a
one-thread delta-stepping baseline and observes actual teams. Dijkstra is an oracle,
not its same-algorithm thread baseline. A tiny chain may have little parallel work.
The [fresh demo script](docs/academic/scripts/run_demo.py) adapts worker counts and
captures all relevant output types into a new directory.

## Dashboard startup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dashboard.txt
python -m streamlit run dashboard/app.py --server.address 127.0.0.1
```

Open the printed local address; forward the port if remote. Navigation covers CPU
overview/performance, memory, cache/locality, multicore, theoretical Amdahl and
experiment explorer. Archive mode uses hash-checked actual receipts, not live host
measurements or synthetic substitutes. Uploaded results retain unverified provenance.
Unknown metadata/counters remain unavailable; standalone CSV enables raw inspection
without inferred speedup. See [dashboard guide](docs/DASHBOARD_GUIDE.md).

## Testing and reproducibility

```sh
ctest --test-dir build/release --output-on-failure
python -m pytest dashboard/tests -q
python3 docs/academic/scripts/verify_evidence.py
python3 docs/academic/scripts/run_demo.py --cli build/release/archgraph --output-dir "$DEMO_PARENT/capture"
```

The final local audit recorded 24 passes and two PMU skips per Debug/Release/
sanitizer CTest configuration, plus 102 dashboard pytest passes. No test weakening
or algorithm rewrite was used. See [exact final commands/results](docs/academic/FINAL_VALIDATION.md)
and [full reproduction/authoring guide](docs/academic/REPRODUCIBILITY.md).

## Evidence, status and limitations

All six phases are implemented as a technical academic delivery. See
[roadmap](docs/ROADMAP.md), [final evaluation](docs/academic/FINAL_EVALUATION.md),
[Phase 1 validation](docs/VALIDATION.md), [CPU instrumentation](docs/CPU_PROFILING.md),
[counter scope](docs/PERFORMANCE_COUNTERS.md), [Phase 3 validation](docs/PHASE3_VALIDATION.md),
[Phase 4 validation](docs/PHASE4_VALIDATION.md), and [Phase 5 validation](docs/PHASE5_VALIDATION.md).

- Hardware counters were denied or unsupported in recorded workload receipts;
  no measured IPC or verified L1/L2/L3 transition is claimed.
- Archived scaling exposes one reported physical core with two SMT contexts on
  shared/virtualized resources, not controlled independent-core scaling.
- Representation estimates differ from physical memory. Repeated medians/range/MAD
  are descriptive, not statistical significance or causal proof.
- Original imported-source attribution is retained; licensing clearance is unresolved.
- Browser and PowerPoint/projector rendering were unavailable for final visual QA.
  Programmatic tests, readiness checks and structural checks do not replace them.

The project is prepared for a qualified academic demonstration and viva. Resolve
licensing and perform manual display review before an unrestricted release or
formal presentation acceptance claim. No merge or automatic PR is part of delivery.
