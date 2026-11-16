# Phase 5 validation

Validated on 16 November 2026, branch `feature/phase5-performance-dashboard`.
The branch was created from freshly fetched main
`e50b30e43c1a0e63c0ab1318f2ebeac34cc4e875`. The initial worktree was clean.
Graph algorithms, C++ headers/sources, CLI, CMake and existing tests were not
modified. No merge, automatic pull request or hosted deployment was performed.

## Implemented views and stack

Seven local navigation views: CPU overview, CPU performance, memory organization,
cache/locality, multicore performance, Amdahl's Law and experiment explorer.
Python 3.11+ is the documented dashboard requirement; the validated interpreter
was Python 3.14.2. Installed direct dependencies were Streamlit 1.67.0,
Pandas 3.1.1, Plotly 6.9.0 and pytest 9.2.0. Complete installed versions are retained
in `validation/phase5/dashboard-installed.txt`; pip check found no broken requirements.
The stack was installed into an isolated temporary virtual environment. Initial
sandbox network access was unavailable; installation succeeded with authorized
network access. Dashboard dependencies remain separate from the core build.

Implementation separates byte loading, bounded producer validation, pure
transformations, chart creation and Streamlit presentation. A fixed local catalog
checks exact archived file hashes; uploads never select or execute server paths.
Filters/downloads preserve recorded values and environments. Null/unavailable
hardware metrics, estimates, measured memory and theoretical models have distinct
labels and empty states.

## Actual data sources

The demo catalog has 13 authentic JSON receipts:

| Sources | Files | Interpretation |
| --- | ---: | --- |
| Committed Phase 2 | 3 | Sequential/parallel benchmark smoke and independent availability diagnostic; recorded CPU differs from Phase 4. |
| Committed Phase 4 | 3 | Scaling, scheduling/synchronization kernels and CPU metadata, including the one-visible-core/SMT limitation. |
| Phase 5 captures using existing Phase 3 CLI | 7 | Memory, layout comparison, four locality patterns and cache-study measurements, never synthetic. |

The new captures are under `docs/validation/phase5/receipts/`. The eight-vertex
chain recipe and generator manifest are preserved in `generation-provenance.json`.
Memory/layout outputs retain loaded-CSR identity. Every capture records the CLI
command and source-file hash. Five measured trials per configuration and default
warmups were used for these tiny demonstration measurements; they are not
representative performance evidence. Locality configurations allocate 1 MiB and
perform 131,072 data/index reads with seed 42; temporal active data is 4 KiB;
strided access uses stride 16. The cache study uses 4 KiB, 32 KiB, 256 KiB and 1 MiB
active data with the same read count. Hardware requests returned permission_denied.

New receipts record GCC 13.3.0 Release, main base revision and dirty=true at CMake
configuration time. The source tree changes were dashboard work; core sources
were unchanged. Reconfigure after committing to refresh build revision metadata.
Temporary graph paths in command provenance are historical capture paths and are
never opened by the dashboard. Keep the retained manifest to regenerate the input.

Archived rows remain archived even when the UI is run on a different machine.
Uploaded metadata are unverified claims; structural checks are not authentication.
No synthetic PMU counts or timed workloads are substituted. Numerical test fixtures
exercise available/multiplexed counters but are confined to tests and never enter
the catalog or demo UI.

## Tests and build results

| Verification | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Dashboard pytest suite | 102 | 0 | 0 |
| Existing C++ Debug CTest suite | 24 | 0 | 2 |
| Existing C++ Release CTest suite | 24 | 0 | 2 |

Debug and Release were configured in fresh `build/phase5-debug` and
`build/phase5-release` directories with `ARCHGRAPH_WARNINGS_AS_ERRORS=ON` and
`ARCHGRAPH_HARDWARE_TESTS=ON`. GCC strict warning flags remained enabled. All
previous core, CLI, workload generation, profiling, memory and multicore tests
passed. Both skips are the existing unavailable-PMU integration tests
`perf_hardware` and `memory_hardware`. `multicore_hardware` passed. CTest's original
Python tests ran without the optional dashboard environment.

Dashboard coverage includes all 18 requested processing areas: JSON and exact CSV
loading; supported schemas; malformed/oversized/nested/duplicate-key input;
missing/denied/unreliable/unsupported metrics; same-group IPC/CPI validation and
multiplexing arithmetic; memory labels; locality groups; speedup/efficiency;
baseline compatibility; theoretical Amdahl arithmetic and invalid parameters;
metadata filters; deterministic/round-trip exports; empty states; incompatible
machine/build/scope detection; preservation of original uint64 values. Additional
contracts cover genuine zero counts, producer bounds before range allocation,
formula-safe CSV, source checksums and caller-only OpenMP counter rejection.

Streamlit AppTest exercised all seven navigation views, relevant archived receipt
choices, metadata/access-pattern filtering, Amdahl controls and observation overlay,
empty mode, malformed uploads, actual JSON/CSV uploads and warnings. Chart tests
checked empty states, accounting labels, metadata-only capacity markers and theory
labels. The initial suite found a JSON-selection source-name round-trip mismatch;
source-name preservation was corrected and the complete final suite passed.

Test/build/configure logs and the installed environment are under
`docs/validation/phase5/`. Separate dashboard CI is configured for Python 3.11 and
3.14; remote CI execution and local Python 3.11 validation are not claimed.
Older permitted Streamlit AppTest versions without upload support explicitly skip
that interaction test; byte-loader tests remain mandatory. There were no skips
with the installed Streamlit version.

## Startup verification and limits

A real Streamlit process was started on loopback port 8501. Both the HTML shell
`GET /` and readiness endpoint `GET /_stcore/health` returned HTTP 200; health body
was `ok`. Evidence is in `startup-server.log` and `startup-http.log`. The managed
sandbox disallowed local sockets; authorized execution outside that restriction
was used for startup and HTTP checks. AppTest verifies application execution;
HTTP checks alone only prove server readiness. The owned server was stopped after
verification. Launch it again using the guide.

**No visual browser test, screenshot review or pixel-layout verification was
executed.** Plotly construction, Streamlit interactions and server startup were
verified programmatically. Projector/browser appearance remains a manual check.

## Scientific and import contracts

- PMU charts use only available/multiplexed actual event values, with matching
  raw/enabled/running arithmetic and scheduling validity. IPC/CPI require compatible
  same-group operands and original derived arithmetic. Missing values stay null;
  genuine measured zero remains zero. Diagnostic probes never enter workload plots.
- Counter statuses and scope/multiplexing metadata remain inspectable. OpenMP
  hardware aggregation remains unsupported; caller-only values cannot become
  process-wide totals. Wall-clock trials remain useful when counters are denied.
- Memory/accounted footprint estimates are separate from measured whole-process
  RSS. Overlapping categories are grouped, not stacked. Unknown allocator and
  per-layout physical memory are never manufactured.
- Locality markers are OS-reported capacities, not verified cache transitions.
  Explicit compatible comparisons keep separate traces and do not pool documents.
  Equal read counts do not establish equal instructions or exclusive cache ownership.
- Delta-stepping ratios use one-thread delta-stepping. Kernel ratios use matching
  strategy/chunk/workload. Original summary fields are retained; displayed ratios
  are recomputed from complete measured blocks. Missing baselines, reduced observed
  teams, incomplete selections or invalid timing make ratios unavailable.
- The Amdahl curve is theoretical. An f assumption is not a measured serial fraction.
  Only compatible delta-stepping observations can be overlaid, with distinct labels.
- Standalone Phase 4 CSV lacks machine/build/graph/baseline/scope metadata and permits
  raw inspection only. It is not implicitly paired with similarly named JSON.
- Downloads are deterministic. JSON selections embed the original document and row
  IDs, preserving uint64 values and unknown fields; source summaries are not rewritten.
  Filtered normalized CSV is a viewing export, not a producer receipt. String cells
  are protected against spreadsheet formula interpretation.

File limits are 16 MiB each, at most eight uploads/32 MiB total, 100,000 rows per
array, 32 nesting levels and a bounded node budget. NaN/infinity, duplicate keys,
invalid producer bounds and unsupported schemas/scopes are rejected. No unsafe
object deserialization, code evaluation, user-controlled file access or benchmark
subprocess launch is included in the app.

## Files created and modified

Created:

- `requirements-dashboard.txt`, `.streamlit/config.toml`, `.github/workflows/dashboard.yml`
- `dashboard/app.py`, `dashboard/views.py` and package initializers
- `dashboard/components/ui.py`
- `dashboard/data/loader.py`, `schemas.py`, `validation.py`, `transform.py`, `export.py`, `receipts.json`
- `dashboard/charts/common.py`, `cpu.py`, `memory.py`, `locality.py`, `scaling.py`, `amdahl.py`
- `dashboard/tests/conftest.py`, `test_data.py`, `test_charts.py`, `test_app.py`
- `docs/DASHBOARD_GUIDE.md`, `docs/DEMO_WORKFLOW.md`, `docs/PHASE5_VALIDATION.md`
- Build/test/startup/dependency evidence and actual measurement receipts under `docs/validation/phase5/`.

Modified: `.gitignore`, `README.md`, `docs/ARCHITECTURE.md`,
`docs/COA_CONCEPT_MAPPING.md`, `docs/ROADMAP.md`. Core algorithms and previous
Phase 2–4 receipts are unchanged.

## Reproduction

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dashboard.txt
python -m pip check
python -m pytest dashboard/tests -q
python -m streamlit run dashboard/app.py --server.address 127.0.0.1
cmake -S . -B build/phase5-debug -DCMAKE_BUILD_TYPE=Debug -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase5-debug --parallel 2
ctest --test-dir build/phase5-debug --output-on-failure
# Repeat with build/phase5-release and CMAKE_BUILD_TYPE=Release.
```

See [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) for fresh benchmark recipes and
[DEMO_WORKFLOW.md](DEMO_WORKFLOW.md) for the five-minute professor demonstration.
Neither the dashboard nor these receipts establish PMU availability, statistical
significance, controlled physical multicore scaling or causal cache transitions.
