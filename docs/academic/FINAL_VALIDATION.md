# Final validation report

## Scope and audit

Date: 16 November 2026. Delivery branch: `docs/phase6-final-academic-delivery`.
Fresh main base: `a3c8f24be9877d9f7ea4cbb5ccacbc124f5a83bb`.
The initial worktree was clean. Repository structure, CMake/CTest, both CI workflows,
CLI, generator, experiment runners, dashboard adapters and prior phase validation/
import records were reviewed. No repository AGENTS.md was present. The source
reference repository DynaGraph-HPC was not changed; this phase does not rewrite
algorithms, weaken tests or overwrite earlier benchmark receipts.

The audit identified two delivery issues to address: a missing consolidated academic
package and a historical import-status table that needed clarification about the
Phase 4 observed-team extension. Both are documented without changing the original
upstream manifest/hashes. No upstream license grant was invented.

## Environment

See [environment.json](../validation/phase6/environment.json) for captured facts.

| Field | Observed value |
| --- | --- |
| OS / architecture | Linux x86_64, kernel 6.8.0-1070-azure |
| Compiler | GCC 13.3.0, Ubuntu 13.3.0-6ubuntu2~24.04.1 |
| CMake | 3.28.3 |
| Python | 3.14.2 |
| OpenMP | Compile specification 201511; GNU libgomp runtime |
| CPU model string | AMD EPYC 7763 64-Core Processor |
| Visible contexts | Logical CPUs 0,1; one reported physical core/package; SMT |
| Affinity / quota | Caller mask [0,1]; no finite quota at visible cgroup locations; hidden limits possible |
| Core runtime | Default OpenMP maximum 2; safe logical thread ceiling 2 |
| Dashboard | Streamlit 1.67.0, Pandas 3.1.1, Plotly 6.9.0, pytest 9.2.0 |
| Authoring | python-pptx 1.0.2, Matplotlib 3.11.2, Mermaid parser 11.17.2 |

Physical topology is OS-reported; the model does not mean the environment owns a
64-core CPU. No controlled independent-core scaling, PMU fidelity, exclusive host,
fixed frequency or NUMA/cache state is established. Configure-time metadata in
fresh CLI receipts records the main base and dirty=true for this precommit academic
work. Core algorithms were unchanged; reconfigure to refresh metadata after checkout.

## Exact build and test commands executed

Commands ran from `/workspaces/ArchGraph-COA`. Phase 6 build directories were fresh.
Standard output/error logs are separate from prior evidence. The substantive commands
were:

```sh
git fetch origin
git switch main
git merge --ff-only origin/main
git switch -c docs/phase6-final-academic-delivery

cmake -S . -B build/phase6-debug -DCMAKE_BUILD_TYPE=Debug -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase6-debug --parallel 2
ctest --test-dir build/phase6-debug --output-on-failure

cmake -S . -B build/phase6-release -DCMAKE_BUILD_TYPE=Release -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase6-release --parallel 2
ctest --test-dir build/phase6-release --output-on-failure

cmake -S . -B build/phase6-sanitize -DCMAKE_BUILD_TYPE=Debug \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined -no-pie'
cmake --build build/phase6-sanitize --parallel 2
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ctest --test-dir build/phase6-sanitize --output-on-failure

python3 -m venv /tmp/archgraph-phase6-venv
/tmp/archgraph-phase6-venv/bin/python -m pip install --no-cache-dir -r requirements-dashboard.txt 'python-pptx>=1.0.2,<2' 'matplotlib>=3.10,<4'
/tmp/archgraph-phase6-venv/bin/python -m pip check
/tmp/archgraph-phase6-venv/bin/python -m pip freeze
/tmp/archgraph-phase6-venv/bin/python -m pytest dashboard/tests -q
```

Compiler flags include C++17, `-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror`.
All clean configurations/builds succeeded with no compiler warnings accepted.
Dashboard/authoring dependencies were freshly installed into an isolated temporary
environment using authorized network access; C++ tests used the ordinary Python
interpreter rather than requiring these UI packages. Installed versions are saved
in [installed.txt](../validation/phase6/installed.txt); pip check found no broken requirements.

## Results and explicit skips

| Verification | Registered | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Debug CTest | 26 | 24 | 0 | 2 |
| Release CTest | 26 | 24 | 0 | 2 |
| ASan + UBSan + leak-detection CTest | 26 | 24 | 0 | 2 |
| Dashboard pytest / AppTest | 102 | 102 | 0 | 0 |

Each CTest suite covers graph/CSR input validation, Dijkstra and delta-stepping,
independent shortest-path oracles, OpenMP, CLI, generator/loader, profiling contracts,
layout equivalence, locality/cache, quota/topology, scaling arithmetic/order and
JSON/CSV integration. The two skips are `perf_hardware` and `memory_hardware` due
to unavailable real PMU access. `multicore_hardware` passed with observed team/
affinity support. Skips are not hardware measurements.

The unchanged dashboard suite covers all seven views, real archived/JSON/CSV
loading, malformed data, missing/denied counters, IPC/CPI assumptions, memory labels,
locality grouping, scaling/model calculations, metadata filters, compatibility,
selection exports and exact original values. AppTest included actual upload controls
with this installed Streamlit version. Tests were not removed or relaxed.

ASan, UBSan and leak detection reported no findings in the final nontraced execution.
It ran outside the managed tracing sandbox because earlier phases established
LeakSanitizer's inability to inspect threads under that restriction. This is a
passing leak-enabled run, not a run with leaks disabled. No Phase 6 sanitizer failure
is concealed; previous-phase restricted attempts remain in their original logs.
Sanitizers do not establish race freedom or a formal proof.

Logs: [debug](../validation/phase6/debug-tests.log), [release](../validation/phase6/release-tests.log),
[sanitizers](../validation/phase6/sanitize-tests.log), [dashboard](../validation/phase6/dashboard-tests.log).

## Archive integrity and fresh demonstration

```sh
python3 docs/academic/scripts/verify_evidence.py --output docs/validation/phase6/evidence-audit.json
python3 docs/academic/scripts/results.py --output-dir docs/academic/results
python3 docs/academic/scripts/run_demo.py --cli build/phase6-release/archgraph --output-dir docs/validation/phase6/demo
```

The [audit](../validation/phase6/evidence-audit.json) validates all **13** archived
receipts against catalog byte SHA-256 and supported producer contracts. It compares
all **306** Phase 4 CSV rows (34 scaling + 272 kernels) field by field with JSON.
Historical import hashes still match files originally unchanged except the two
documented Phase 4 delta-stepping team-observation extensions. Initially adapted
imports remain explicitly classified, with original hashes preserved.

The new [demo summary](../validation/phase6/demo/demo-summary.json) reports full
Dijkstra/delta distance equality, safe thread list 1,2 and 12 scaling calls
(5 measured + 1 warmup block per count). All generated supported JSON/CSV outputs
passed loader validation. Memory/layout, sequential/random locality, explicit cache
study and dedicated kernel outputs were exercised. Exact CLI argv and stderr are
in [commands.json](../validation/phase6/demo/commands.json); the generated graph
manifest/specification trace back to the tracked deterministic chain configuration.
These tiny new captures are regression/demo evidence, not replacement historical
performance data or independent-core scaling results.

## Startup and browser status

```sh
/tmp/archgraph-phase6-venv/bin/python -m streamlit run dashboard/app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

A local Python urllib client requested `/` and `/_stcore/health` on
`http://127.0.0.1:8501`. Both returned HTTP 200; health returned `ok`.
See [startup server](../validation/phase6/startup-server.log) and
[HTTP checks](../validation/phase6/startup-http.log). Authorized nonrestricted
execution was used for local sockets. The owned Streamlit server was stopped
following verification; the application remains locally launchable via the guide.

**Actual browser validation: not performed.** Tool discovery exposed no browser
control, and no Chromium/Chrome executable or installed Playwright/Selenium browser
was available. No browser was installed solely to imply a preexisting capability.
No screenshots, visual navigation/chart/readability/empty-state/upload/download/
slider or classroom-projector verification is claimed. AppTest checks those
application paths programmatically but cannot certify visual rendering. A manual
seven-view checklist is in the demo/evaluation documents.

No PowerPoint or LibreOffice renderer was available. The editable PPTX passed
package/data checks, not a rendered-slide inspection. Four static scientific PNG
exports were inspected as image files; that does not imply dashboard or slide QA.

## Academic artifact commands and checks

```sh
MPLCONFIGDIR=/tmp/archgraph-phase6-mpl /tmp/archgraph-phase6-venv/bin/python docs/academic/scripts/charts.py --output-dir docs/academic/figures
/tmp/archgraph-phase6-venv/bin/python docs/academic/scripts/presentation.py --output docs/academic/PRESENTATION.pptx
npm install --prefix /tmp/archgraph-phase6-mermaid --cache /tmp/archgraph-phase6-npm-cache --no-audit --no-fund mermaid@11 jsdom
node docs/academic/scripts/check_mermaid.mjs /tmp/archgraph-phase6-mermaid/node_modules docs/academic/ARCHITECTURE_DIAGRAMS.md
python3 docs/academic/scripts/check_delivery.py
```

The presentation builder checks 15 editable slides, 15 notes pages, ZIP integrity,
reopenability and shape bounds. Package checks also compare the two native editable
chart datasets with receipt-derived values and speaker notes with the canonical
Markdown. The 19 report sections, 60 contiguous viva answers, seven diagram blocks,
local documentation target existence, derived-data repeatability and no-overwrite
behavior are checked. Four SVG/PNG scientific figure pairs are valid; they reproduce
archived data and explicitly labeled theory, not fabricated PMU series.

Mermaid 11.17.2 accepted all seven flowcharts. This is a syntax check of standard
GitHub-compatible Mermaid, not a browser/GitHub screenshot or a guarantee of the
exact current GitHub layout engine. See [parser log](../validation/phase6/mermaid-check.log)
and [package check](../validation/phase6/delivery-check.json).

`docs/validation/phase6/DELIVERY_MANIFEST.json` records file sizes and hashes for the
academic package and final Phase 6 evidence; its own hash is excluded. The command
`python3 docs/academic/scripts/package_manifest.py --check` verifies it without changing
previous receipts. Diagram/source syntax and artifact checks augment, rather than
replace, the original CTests/dashboard tests. Optional authoring packages are not
added to core or dashboard installation requirements.

## Failures, restrictions and readiness

There were no final software test/build/sanitizer failures. PMU skips remain explicit.
Optional compiler/platform/race-detector tests, actual PMU fidelity, controlled
independent-core performance, browser rendering and PowerPoint/projector rendering
are not verified. Publisher DOI endpoints restricted automated access for some
references; original/author copies and institutional records were consulted without
inventing citations or reproducing their figures as project evidence.

**Readiness:** technically prepared for a qualified academic demonstration and viva,
with the complete report/diagrams/slides/notes/demo/questions/reproduction package.
Manual display review is still required, and unresolved upstream licensing remains
a condition before claiming unrestricted redistribution. No perfect score,
institutional approval, automatic PR, merge or unsupported performance conclusion
is part of this delivery. See [FINAL_EVALUATION.md](FINAL_EVALUATION.md).
