# Interactive performance dashboard

The optional Phase 5 dashboard reads actual ArchGraph receipts; it never runs
benchmark commands, changes permissions or fabricates unavailable PMU values.
It is a locally runnable Streamlit application with Pandas transformations,
Plotly charts and pytest contracts. The C++ graph algorithms are unchanged.

## Setup and launch

Use Python 3.11 or newer, starting in the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dashboard.txt
python -m streamlit run dashboard/app.py --server.address 127.0.0.1
```

On Windows, activate with `.venv\Scripts\activate`. Open the local address printed
by Streamlit (normally http://127.0.0.1:8501). Remote Codespaces users must forward
the port to their browser. Bind to loopback for local use; this application does
not add authentication for public hosting. No Site or cloud deployment is needed.
Stop the owned server with Ctrl-C. C++ builds and CTests use the existing separate
requirements and do not install/import this optional stack.

Dependency ranges in `requirements-dashboard.txt` are deliberately separate:
Streamlit >=1.50,<2 supplies the layout/chart and AppTest APIs, Pandas >=2.2.3,<4
supports modern Python dataframes, Plotly >=6,<7 supplies interactive figures,
and pytest >=8.3,<10 supplies isolated processing and UI tests. Major upper bounds
avoid unreviewed major API changes. Installed versions are recorded in the
validation receipt, not claimed identical for every future install. AppTest file
upload tests explicitly skip on older permitted versions lacking its upload API;
byte-level upload contracts still run. See the official
[Streamlit chart API](https://docs.streamlit.io/1.50.0/develop/api-reference/charts/st.plotly_chart),
[AppTest reference](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
and [Plotly Express documentation](https://plotly.com/python/plotly-express/).

## Views

| Navigation | Purpose and interpretation |
| --- | --- |
| CPU overview | Recorded model, architecture/OS when present, physical/logical counts, SMT, mask, quota, cache entries and build facts. Unknown fields stay Unavailable; host Python platform is never substituted for the measurement host. |
| CPU performance | Per-trial real event values and validated same-group IPC/CPI/miss ratios, raw/scheduling/status details and independent wall-clock charts. Diagnostic probes are excluded. |
| Memory organization | CSR/adjacency payload, metadata, capacity and accounted footprint; whole-process measured RSS stays separate. Matching layout Dijkstra trials are shown when present. |
| Cache & locality | Access-pattern/working-set trials, medians and optional reported-capacity markers. Explicit compatible comparisons retain separate traces and do not pool files. |
| Multicore performance | Requested/observed teams, median/range/MAD, same-algorithm speedup/efficiency, individual warmup/measured trials, topology and affinity/quota caveats. |
| Amdahl’s Law | Explicitly theoretical f/thread controls and an optional compatible observed delta-stepping overlay. The assumed f is never estimated from measurements. |
| Experiment explorer | Metadata and trial filters, compatibility diagnostics, lossless original values, filtered CSV and reimportable JSON selection downloads. |

Select the active receipt in the sidebar. Build, experiment and environment filters
reduce the available list without merging it. Locality/explorer support pattern,
working-set, repetition and warmup controls. An empty access-pattern or working-set
selection intentionally yields no rows. Repetition filters affect descriptive
trial views; multicore ratios are calculated from the active receipt's full
selected measured blocks, not arbitrary display filters. JSON selections missing
baseline trials or complete blocks produce null ratios.

## Authentic demo sources

“Use archived validation receipts” loads a fixed allowlisted catalog at
`dashboard/data/receipts.json`. It checks each source file's byte SHA-256 before
loading; changed or missing receipts are shown as unavailable. All demo results
are labeled archived, including seven measurements captured during Phase 5 with
the existing Release CLI. They are not live views of the computer opening the UI.

- Phase 2 committed Dijkstra/delta-stepping benchmark and availability diagnostic.
- Phase 4 committed scaling, synchronization/scheduling kernels and CPU metadata.
- Phase 5 validation captures of Phase 3 memory/layout, sequential/strided/random/
  temporal locality and a configurable cache study. Commands, generator recipe,
  manifest and file hashes are committed with those captures.

The measured hosts can differ. Environment fingerprints include recorded CPU/build,
topology, runtime and available kernel fields; they are conservative compatibility
checks, not authenticated machine IDs or proof of controlled conditions. No file
is silently pooled with another. Explicit locality comparisons require matching
recorded environment/build/scope, seed and data/index read counts, and keep their
configuration labels; footprint and pattern differences remain visible. Missing
machine/build identity never authorizes pooling. Standalone CSV lacks provenance
and is restricted to raw inspection, even when its basename matches a JSON file.

## Generate fresh data

Build the core without installing dashboard dependencies if desired:

```sh
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DARCHGRAPH_WARNINGS_AS_ERRORS=ON
cmake --build build/release --parallel 2
python3 -B benchmarks/python/generate.py generate --spec benchmarks/configs/chain-v1.json --output /tmp/dashboard-chain
python3 -B benchmarks/python/generate.py verify --manifest /tmp/dashboard-chain/manifest.json
build/release/archgraph --cpu > /tmp/cpu.json
build/release/archgraph bench --input /tmp/dashboard-chain/graph.txt --source 0 --algorithm dijkstra --repetitions 10 --hardware-counters > /tmp/bench.json
build/release/archgraph memory --input /tmp/dashboard-chain/graph.txt > /tmp/memory.json
build/release/archgraph compare-layouts --input /tmp/dashboard-chain/graph.txt --source 0 --runs 10 > /tmp/layouts.json
build/release/archgraph locality --pattern random --size 1048576 --accesses 131072 --seed 42 --runs 10 --hardware-counters > /tmp/locality.json
build/release/archgraph cache-study --sizes 4096,32768,262144,1048576 --accesses 131072 --seed 42 --runs 10 > /tmp/cache.json
build/release/archgraph scaling --input /tmp/dashboard-chain/graph.txt --source 0 --threads 1,2 --repetitions 15 --csv /tmp/scaling.csv > /tmp/scaling.json
```

Generation requires a new directory. Inspect `--cpu` first and use only thread
counts permitted by the current affinity/quota limits; use `--threads 1` if needed.
Upload the resulting JSON/CSV through the sidebar. Uploaded results are labeled
“capture time/environment unverified”; the UI does not assert they were captured
live or that uploaded claims are genuine. Retain the generator manifest separately.
No uploaded graph/path is read or executed. To add a new trusted archived demo,
a maintainer must audit the output and update the fixed catalog and its checksum.

## Supported import contracts

Only schema version 1 is supported. Validation recognizes:

- Phase 2 `bench` JSON: completed/verified algorithms, wall_ns runs/samples/median,
  caller-thread non-inherited PMU scope and CPU/build metadata.
- CPU metadata and separately labeled availability diagnostics. Their diagnostic
  arithmetic probe counters never enter workload charts.
- `archgraph-memory-experiments`: memory, compare-layouts, locality and cache-study,
  including storage accounting, optional PMU events and cache metadata.
- `archgraph-multicore-experiments`: scaling and parallel-kernels, theoretical
  assumptions, complete warmup/measured blocks and consistent timing summaries.
- Exact Phase 4 raw CSV header, version, numeric/boolean fields and strategy values.
  It has no machine, graph, baseline or scope information, so no scaling inference.
- Dashboard selection JSON v1, which embeds the unchanged source document, its
  canonical digest and selected row IDs. The source is revalidated on import.

Phase 3/4 producer documentation remains authoritative for workload boundaries.
Unsupported schemas, unknown units/scopes, mismatched samples/statistics, invalid
counter states/values/times and incomplete source documents are rejected with a
specific message. Raw Phase 4 CSV is not automatically paired with similarly named
JSON, and arbitrary tabular CSV is not treated as benchmark data.

## Quantities and exports

Wall time is shown in milliseconds with original ns retained in tables/downloads.
Memory bars show overlapping accounting categories side by side; never sum them
as a stacked footprint. Accounted totals include capacities and container estimates,
not unknown allocator overhead. Process RSS is a measured whole-process snapshot
with both layouts resident, not per-layout physical memory.

Counter values are charted only for available/multiplexed states. Failed permission,
unsupported scope, invalid timing and unreliable scheduling retain status and null
values; genuine measured zeros remain zero. Raw counts and enabled/running times
remain inspectable. Multiplexed scaled values must agree with raw * enabled/running
and meet the producer scheduling gate. Ratios require compatible same-group operands
and producer-derived arithmetic; wall time is never a cycles denominator. OpenMP
caller-only counts are rejected as multicore totals. No PMU data are invented.

Scaling recomputes S(p)=median T(1)/median T(p), E(p)=S(p)/p from complete measured
trials. Delta-stepping requires the exact documented one-thread delta-stepping
baseline; Dijkstra is not its same-algorithm baseline. Kernels require matching
strategy/chunk/workload baselines. Mismatched teams, incomplete selections, missing
baselines or invalid timing make ratios unavailable. Amdahl remains theoretical.

Filtered CSV is a stable normalized viewing table, not a producer schema and is
not reimported as Phase 4 output. It protects string cells against spreadsheet
formula interpretation. Reimportable selection JSON preserves uint64 integers and
unknown original fields; it does not rewrite producer summaries to fit a filter.
The source JSON values are displayed as text to avoid JavaScript integer rounding;
checksum/raw-counter table columns are decimal strings. Plot coordinates use
floating-point values for visualization. The displayed canonical document hash
ignores JSON whitespace/key order; catalog hashes authenticate exact archived bytes.

## Trust and limits

Uploads remain in the local Streamlit session and are not written to disk. The app
contains no eval, pickle, dynamic imports from uploads, shell execution or arbitrary
server-path selector. Fixed source imports are independent of uploaded paths.
Limit: 16 MiB per file, at most eight uploads/32 MiB total, 100,000 rows per array,
32 levels of nesting and a bounded structural budget. Duplicate keys, nonfinite
numbers and producer-bound violations are rejected. Schema validation checks
consistency, not whether a user forged a plausible measurement. This is a local
research viewer, not a sandboxed public upload service.

Shared hosts, SMT contention, frequency changes, migration and cached state remain
limitations. No significance, causal cache transitions, physical resource exclusivity
or browser visual QA is established by these plots. The dashboard cannot create
missing historical topology fields. When no suitable receipts exist, it shows an
empty state; only the explicitly theoretical Amdahl model remains available.
