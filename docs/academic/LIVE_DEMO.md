# Live demonstration: 5–7 minutes

This demo needs no usable PMU counters and can run with one allowed worker.
Prepare builds and dependencies beforehand; do not spend the presentation waiting
for installation. Use a new output directory so old evidence cannot be overwritten.
The small chain is a correctness/explanation example, not a scalability workload.

## Preflight, before class

From the repository root:

```sh
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DARCHGRAPH_WARNINGS_AS_ERRORS=ON
cmake --build build/release --parallel 2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dashboard.txt
python3 docs/academic/scripts/verify_evidence.py
DEMO_DIR=$(mktemp -d /tmp/archgraph-coa-demo.XXXXXX)
python3 docs/academic/scripts/run_demo.py --cli build/release/archgraph --output-dir "$DEMO_DIR/capture"
python -m streamlit run dashboard/app.py --server.address 127.0.0.1
```

`run_demo.py` chooses `1,2` only when the discovered safe thread limit permits it;
otherwise it uses `1`. It verifies the generated manifest, full Dijkstra/delta
outputs, supported JSON receipts and raw CSV. It reports a JSON summary with
`sssp_outputs_equal`, `thread_list`, `scaling_calls`, `topology` and purpose.
The script refuses an already-existing capture directory. Keep the printed
`DEMO_DIR` in your terminal to reuse the results.

Open Streamlit's printed address in a browser, with port forwarding if remote.
Manual browser/projector review is still required: Phase 6 had no browser available.
Keep the [slide deck](PRESENTATION.pptx), [results table](results/RESULTS.md) and
[report](PROJECT_REPORT.md) locally as fallbacks. No institutional logos or
permissions to change PMU security settings are needed.

## 0:00–0:45 — State the question and inspect the machine

Introduce the question: how do representation, locality and parallel overhead
change a correct workload? Run:

```sh
build/release/archgraph --version
build/release/archgraph --cpu
```

Expected structure: version/OpenMP date and CPU/build JSON with `topology`, logical
processors, physical cores where known, available CPU IDs, quota status and safe
thread limit. Unknown values stay null. Explain SMT and shared-host limitations;
do not call logical contexts dedicated physical cores.

## 0:45–1:30 — Show correct graph processing

```sh
cat "$DEMO_DIR/capture/graph/graph.txt"
cat "$DEMO_DIR/capture/sssp-dijkstra.json"
cat "$DEMO_DIR/capture/sssp-delta.json"
```

The graph starts with `V E` and contains directed weighted records. SSSP JSON has
algorithm/source/distances; delta output also has requested/actual threads.
The complete distance vectors match, including null unreachable values if any.
The prepared chain is connected from source zero, so do not expect nulls here.
Explain offsets and the independent test oracle, rather than claiming that one
matching example proves all correctness.

## 1:30–2:30 — Memory and locality, without invented counters

```sh
cat "$DEMO_DIR/capture/memory.json"
cat "$DEMO_DIR/capture/layouts.json"
cat "$DEMO_DIR/capture/locality-random.json"
```

Expected structures: per-layout logical/capacity/container accounting plus
whole-process `rss_bytes`; matched-output layout timing records; locality
pattern/active bytes/read counts/seed/checksum and individual `timing.runs`.
Do not read every number aloud. Upload the supported JSON files into the dashboard
and show the corresponding Memory organization and Cache & locality views.
Compare footprint estimates with measured whole-process RSS. Cache-capacity
markers are metadata; denied PMU events cannot establish miss rates.

## 2:30–3:30 — Thread scaling and synchronization

```sh
cat "$DEMO_DIR/capture/demo-summary.json"
cat "$DEMO_DIR/capture/scaling.csv" | head -5
```

Upload `scaling.json` and open Multicore performance. Show requested and observed
teams, individual trials, median/range/MAD, warmup exclusion and the baseline.
T(1) is one-thread delta-stepping, not Dijkstra. The tiny chain can be slower with
more workers and is not performance evidence. Use archived Phase 4 `scaling.json`
for the documented grid example, clearly retaining its archived label.
If using `kernels.json`, distinguish static/dynamic chunks, reduction, atomic and
critical strategies and explain their different timing boundary from SSSP.

## 3:30–4:30 — Hardware status and provenance

Open CPU performance with the archived sequential smoke receipt. Show
permission_denied/null events and the useful wall-clock chart. With a real PMU-
capable uploaded receipt, show actual status/scope/times before any numerical chart.
The OpenMP scope remains unsupported; no caller-only proxy is a worker total.

In Experiment explorer, inspect source/build/graph/scope, filter one repetition,
and download filtered CSV and a lossless JSON selection. The latter preserves
original values and source summaries. Incomplete selections disable scaling ratios.
Standalone raw CSV has insufficient provenance for inferred speedup.

## 4:30–5:30 — Amdahl and interpretation

Open Amdahl's Law, adjust assumed f, selected thread count and displayed maximum.
Explain `1/((1-f)+f/p)`. The optional compatible delta-stepping overlay is observed
while the curve stays theoretical; f is not fitted. More workers can add overhead,
share SMT resources or encounter insufficient work. Conclude with the observed
scope/uncertainty, not a claim of measured independent-core scaling.

## 5:30–6:30 — Evidence, questions and honest limits

Point to [FINAL_VALIDATION.md](FINAL_VALIDATION.md) and [VIVA_QA.md](VIVA_QA.md).
Explain tests, explicit PMU skips, sanitizers, 13 receipt hashes and browser limits.
State that upstream licensing is unresolved and that the project is technically
prepared for a qualified academic demonstration rather than an unrestricted release.
Reserve the final half-minute for one question about baseline or memory accounting.

## Archived fallback and failure plan

| Problem | Reliable response |
| --- | --- |
| No PMU permission | Continue with real wall timing and explicit unavailable counters; never change host security settings. |
| Only one effective worker | Use automatic one-thread capture; explain theoretical scaling and show archived results as archived. |
| Fresh build too slow | Use the already-validated binary or archived dashboard receipts. |
| Dashboard cannot start | Present the report's SVG/PNG figures, original JSON and Markdown results; Amdahl equations remain explicitly theoretical. |
| No suitable receipt | Show the empty state, not a substitute synthetic performance series. |
| Browser/chart issue | Use static figures and slides; describe the issue rather than claiming visual validation. |
| Need to rerun capture | Choose a new directory; never replace committed evidence. |

Stop the local Streamlit process with Ctrl-C after the demonstration. Do not
promise byte-identical timings: reproducibility means inputs/configuration,
verification and traceable methodology, not the same elapsed nanoseconds.

## Manual display checklist for the classroom machine (not executed in Phase 6)

- Open all seven navigation views and verify readable headings, correct units and
  visible source/archive/theory labels at the projector resolution.
- Inspect actual chart rendering, legends/axes, tables, empty states and denied
  counter messages; verify no numbers were substituted for unavailable metrics.
- Upload valid JSON and raw CSV, reject a malformed file, filter rows and download
  both exports; reimport a lossless JSON selection.
- Move all three Amdahl controls, test the compatible observation overlay and
  confirm the curve remains labeled assumed/theoretical.
- Open the editable PPTX in the target renderer, check every slide/notes page,
  fonts, native chart labels and any overflow, then rehearse the timing.

Record the actual machine/date/outcomes if this manual review is performed later;
do not reinterpret this checklist as completed visual verification.
