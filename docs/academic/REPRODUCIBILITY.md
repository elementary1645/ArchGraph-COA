# Reproducibility package

This guide reproduces software contracts and derives presentation artifacts from
existing evidence. It does not promise identical timing or authorize unrestricted
redistribution of imported code. See [licensing](LICENSING.md).

## 1. Tools and supported scope

- CMake >=3.21, C++17 compiler, OpenMP and Threads runtime.
- Python >=3.8 standard library for generation/core tests and receipt audit/scripts.
- Python >=3.11 for the optional dashboard stack in `requirements-dashboard.txt`.
- Optional `requirements-academic.txt`: python-pptx and Matplotlib, only for
  regenerating editable slides and scientific figure exports.
- Optional Node and Mermaid/jsdom, only for diagram syntax checks.

Validated locally: Linux x86_64, GCC 13.3.0 and GNU libgomp. Python 3.14.2 was used
for this delivery. Python 3.11/3.14 dashboard CI is configured, not claimed executed
remotely here. Linux perf/sysfs/cgroup metadata are platform-specific. Other systems
may build with a suitable OpenMP runtime, but cross-platform correctness/PMU/browser
validation is not established. Core builds do not install dashboard dependencies.

## 2. Checkout and clean builds

Use the desired reviewed commit; the delivery branch is
`docs/phase6-final-academic-delivery`. Do not merge a feature branch as a prerequisite.
Select new build-directory names to ensure fresh caches without deleting evidence.

```sh
cmake -S . -B build/check-debug -DCMAKE_BUILD_TYPE=Debug -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/check-debug --parallel 2
ctest --test-dir build/check-debug --output-on-failure
cmake -S . -B build/check-release -DCMAKE_BUILD_TYPE=Release -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/check-release --parallel 2
ctest --test-dir build/check-release --output-on-failure
```

These names must be unused for a clean configuration. Hardware test return code 77
is an explicit skip, not a numerical measurement. Current registration has 26 tests;
on the recorded environment 24 pass and two PMU tests skip. A different permitted
host may pass PMU tests, and a single-worker host may skip multicore hardware checks.

For a library-only build, `-DBUILD_TESTING=OFF` avoids the test Python requirement.
Warnings-as-errors use the repository's existing compiler flags, not weakened tests.

## 3. Sanitizers

```sh
cmake -S . -B build/check-sanitize -DCMAKE_BUILD_TYPE=Debug \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined -no-pie'
cmake --build build/check-sanitize --parallel 2
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ctest --test-dir build/check-sanitize --output-on-failure
```

These flags are GCC/Linux validation settings, not a portable universal recipe.
A tracing sandbox can prevent LeakSanitizer thread inspection. Record that
restriction; if an authorized nontraced execution is available, rerun there.
Do not describe a disabled leak detector as a passing leak check. Sanitizers are
not a race detector or formal proof.

## 4. Deterministic graph and fresh experiment capture

```sh
CAPTURE_PARENT=$(mktemp -d /tmp/archgraph-reproduce.XXXXXX)
python3 docs/academic/scripts/run_demo.py --cli build/check-release/archgraph --output-dir "$CAPTURE_PARENT/demo"
```

The standard-library script creates a new eight-vertex chain bundle from the
tracked specification, verifies its manifest, records every CLI command and saves
CPU/diagnostics, full SSSP outputs, benchmark/memory/layout/locality/cache/scaling
and kernel outputs. It checks full Dijkstra/delta equivalence and validates supported
JSON/CSV. Thread count defaults to 1,2 only when the actual safe ceiling permits it.
The small capture is a demo/regression workload, not controlled performance evidence.

For manual generation:

```sh
python3 -B benchmarks/python/generate.py generate --spec benchmarks/configs/chain-v1.json --output "$CAPTURE_PARENT/graph"
python3 -B benchmarks/python/generate.py verify --manifest "$CAPTURE_PARENT/graph/manifest.json"
build/check-release/archgraph --cpu
build/check-release/archgraph bench --input "$CAPTURE_PARENT/graph/graph.txt" --source 0 --algorithm dijkstra --repetitions 10 --hardware-counters
build/check-release/archgraph locality --pattern random --size 1048576 --accesses 131072 --seed 42 --runs 5 --hardware-counters
```

Full experiment definitions, units and bounds are in
[LOCALITY_EXPERIMENTS.md](../LOCALITY_EXPERIMENTS.md) and
[SCALING_EXPERIMENTS.md](../SCALING_EXPERIMENTS.md). To recreate the archived Phase 4
grid input, extract the spec in `docs/validation/phase4/graph-provenance.json`,
generate into a new directory and verify the graph SHA-256. The pinned source
manifest and recipe matter; temporary historical capture paths do not need to exist.

## 5. Dashboard environment and startup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dashboard.txt
python -m pip check
python -m pytest dashboard/tests -q
python -m streamlit run dashboard/app.py --server.address 127.0.0.1
```

In a second terminal, check `http://127.0.0.1:8501/_stcore/health` and the HTML root.
HTTP 200 proves readiness, not browser rendering. AppTest exercises controls and
uploads but is not a screenshot or projector test. Forward the port if remote.
The guide [DASHBOARD_GUIDE.md](../DASHBOARD_GUIDE.md) explains views, 16 MiB per-file
limits, provenance-aware imports and deterministic selection exports. Stop the owned
server after use. No dashboard subprocess runs an uploaded file as code.

## 6. Verify archived evidence and imports

```sh
python3 docs/academic/scripts/verify_evidence.py
```

It checks all 13 catalog byte hashes and producer schemas; Phase 4's 34 scaling
and 272 kernel CSV rows against JSON; and original imported hashes. Two files
originally unchanged were deliberately extended in Phase 4 for optional observed
team size. Initial adapted files retain their historical status. See
[IMPORT_PROVENANCE.md](../IMPORT_PROVENANCE.md), the original manifest and
[Phase 6 audit](../validation/phase6/evidence-audit.json). The script reads sources
only and refuses to replace an existing output file if `--output` is supplied.
Hashes establish integrity against the recorded catalog, not host authenticity or
copyright permission.

## 7. Regenerate report tables and charts

```sh
AUTHORING_PARENT=$(mktemp -d /tmp/archgraph-authoring.XXXXXX)
python3 docs/academic/scripts/results.py --output-dir "$AUTHORING_PARENT/results"
python -m pip install -r requirements-academic.txt
MPLCONFIGDIR="$AUTHORING_PARENT/mpl-cache" python docs/academic/scripts/charts.py --output-dir "$AUTHORING_PARENT/figures"
python docs/academic/scripts/presentation.py --output "$AUTHORING_PARENT/PRESENTATION.pptx"
```

The first script uses only the standard library and existing data adapters. It
produces complete timing tables, source hashes, memory accounting and same-algorithm
ratios, without pooling files. The chart script exports four SVG/PNG figure pairs
from those archived values. Curves are explicitly theoretical where applicable;
min/max whiskers are ranges, not confidence intervals. The presentation builder
uses 15 reviewed Markdown slides, full speaker notes and two native editable data
charts; its ZIP, reopen, notes and shape bounds are checked.

Each script refuses an existing target it would replace. Charts are regenerated
from the original receipts rather than measured again. Timings/table values are
reproducible inputs to authoring; font/ZIP/SVG metadata or rendering can differ by
tool versions. No bit-for-bit PPTX or screenshot reproducibility is claimed.
Use [check_delivery.py](scripts/check_delivery.py) for additional package checks and
`python3 docs/academic/scripts/package_manifest.py --check` to verify the complete
tracked delivery inventory. The manifest excludes its own hash; regeneration
refuses an existing manifest.

## 8. Mermaid syntax check

In an isolated temporary Node directory, install parser tools and run:

```sh
npm install --prefix "$AUTHORING_PARENT/mermaid" --cache "$AUTHORING_PARENT/npm-cache" --no-audit --no-fund mermaid@11 jsdom
node docs/academic/scripts/check_mermaid.mjs "$AUTHORING_PARENT/mermaid/node_modules" docs/academic/ARCHITECTURE_DIAGRAMS.md
```

This parses seven standard Mermaid flowcharts. It does not certify GitHub's exact
current renderer or substitute for visual layout review. GitHub supports fenced
Mermaid as described in its [official diagram guide](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams).

## 9. Differences to expect and preserve

Recorded Phase 2/4/5 machine/build environments differ. Do not pool them or fill
missing old topology from the current host. Wall times change with allocation,
OS load, migration, SMT contention, frequency, virtualized resources and warm state.
Permission_denied, unsupported and unreliable PMU values remain null. No security
setting changes are needed for the demo. Amdahl f remains an assumption; Dijkstra
is not delta-stepping's thread baseline. Repeated timing does not imply statistical
significance. Preserve old evidence and create a new output directory for every
capture or academic artifact regeneration.
