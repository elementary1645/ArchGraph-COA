# Five-minute COA professor demonstration

Before class, follow [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md), install the optional
requirements and run `streamlit run dashboard/app.py`. Keep “Use archived
validation receipts” enabled. The dashboard works without PMU permissions.
Have port forwarding ready if running remotely. These are archived authentic
measurements, not live results from the presenter's laptop.

## 0:00–0:45 — Architecture before performance

Open CPU overview with `scaling.json`. Show the recorded model, two logical CPUs,
one physical core and SMT. Explain physical cores versus logical contexts and
why CPU branding does not mean a container owns a full processor. OS/architecture
are unavailable in this receipt; select `diagnostic.json` or a Phase 3-style receipt
to show fields actually recorded there. Never combine old host metadata by guessing.

## 0:45–1:30 — What can we measure?

Open CPU performance and select `sequential-smoke.json`. Show permission_denied
and null PMU values, then individual wall-clock trials. IPC is instructions/cycles,
not instructions/elapsed time. The availability diagnostic is separate from the
workload. Show that delta-stepping counters are unsupported_scope because worker
aggregation has not been validated. No zeros or synthetic PMU graphs replace them.

## 1:30–2:15 — Memory organization

Select `memory.json` on Memory organization. Compare equal logical edge payloads
with different metadata/capacity accounting. Point out that accounted memory is an
estimate and that measured process RSS includes both layouts and runtime state.
Select `layouts.json` for matched-output Dijkstra trials and explain fixed-order
and cache-state limitations. This comparison is not thread speedup.

## 2:15–3:15 — Cache and locality

Open Cache & locality and select `cache-study.json`. Inspect median/range/MAD,
active working sets and reported cache-capacity markers. They are metadata, not
verified L1/L2/L3 transition points. Filter working-set size or repetition.
Select `locality-sequential.json` and explicitly add random/strided/temporal receipts
through the compatibility-checked comparison control. Equal data/index read counts
and seed support a limited comparison; traces retain their own configurations.
Explain spatial versus temporal locality and the index stream's extra footprint.

## 3:15–4:15 — Threads and Amdahl

Open Multicore performance and select `scaling.json`. Show requested and observed
teams, individual warmups/measured trials, medians and variability. State the
baseline: one-thread delta-stepping, not Dijkstra. Explain S(p) and E(p), bucket
barriers and atomic work; more threads can add overhead or contend on SMT resources.
The archived environment cannot establish independent-physical-core scaling.

Open Amdahl’s Law. Adjust f and the displayed/selected thread counts, and call the
curve theoretical. Toggle the compatible delta-stepping observation overlay;
f remains assumed, never fitted from those points. Real scheduling, memory and
synchronization costs violate ideal model assumptions.

## 4:15–5:00 — Reproducibility and questions

Open Experiment explorer. Show CPU/build/scope metadata, graph identity, individual
trials and the canonical document digest. Try another receipt in the compatibility
check and explain why different builds/environments/baselines must not be pooled.
Export a filtered CSV and lossless JSON selection; upload the JSON again to show
selected trials without altering original producer values. Use the guide's CLI
recipes after class for fresh data, keeping the generator manifest.

If demo files are missing or corrupted, the app reports them rather than replacing
them. Disable archived receipts to demonstrate the empty state and the still
available theoretical Amdahl explorer. Do not promise controlled scaling or
statistical significance from shared-host measurements.
