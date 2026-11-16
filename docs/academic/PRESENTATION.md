# Academic presentation: 15 slides with speaker notes

Audience: fifth-semester COA examination. Suggested talk: 10–12 minutes, followed
by the separate 5–7-minute live demonstration and questions. The editable
[PRESENTATION.pptx](PRESENTATION.pptx) is generated from these on-slide bullets and
speaker notes. Do not insert institutional identity or approvals without actual
information. Use 16:9 presentation mode and perform a manual projector check.

## Slide 01 — ArchGraph-COA

### On slide

- CPU Architecture-Aware Graph Processing and Performance Analysis
- Correct workloads, visible measurement scope, honest limitations
- Final academic delivery · 16 November 2026

### Speaker notes

Introduce a COA project that uses graph queries as an observable systems workload.
The aim is to explain CPU execution, data layout, locality and parallel overhead,
not to claim a new optimal shortest-path algorithm. The software is runnable with
restricted PMU permissions, because wall timing and correctness remain available.
State that imported source is attributed and licensing clearance is unresolved.
No professor, institution, signature or approval is asserted. The report and
validation package are the detailed supporting materials.

## Slide 02 — Problem statement

### On slide

- Algorithm complexity alone does not explain wall-clock behavior
- Cache access, synchronization and OS scheduling affect execution
- Restricted/shared hosts make naive speedup claims unreliable

### Speaker notes

A relaxation can require several loads, branches and atomic operations rather than
one machine instruction. Memory placement and contention can change runtime even
when asymptotic work is similar. A classroom demo must distinguish logical threads
from physical cores and permission failures from measured zero counts. Frame the
problem as building a correct and explainable measurement pipeline under these
constraints. This avoids the misleading claim that more threads automatically
produce faster execution or that a timing change identifies a cache miss.

## Slide 03 — Objectives and deliverables

### On slide

- Validate sequential and OpenMP shortest paths on deterministic inputs
- Measure representation, locality, scheduling and thread-scaling behavior
- Deliver reproducible receipts, seven dashboard views and viva materials

### Speaker notes

Explain the six-phase progression: validated imported core, scoped PMU instrumentation,
locality/layout experiments, scaling methodology, dashboard and final academic
consolidation. Input generation retains seeds and a manifest. Every benchmark result
is checked before a completed receipt is published. This final phase preserves
working algorithms and historical results. The delivery includes the report,
diagrams, editable presentation, scripts, demo guide, final verification evidence
and 60 viva questions. Test counts and caveats are detailed in FINAL_VALIDATION.md.

## Slide 04 — COA concepts addressed

### On slide

- Instruction counts, cycles, IPC/CPI and measurement scope
- CSR layout, spatial/temporal locality, cache lines and translation
- MIMD workers, SMT, synchronization, speedup and Amdahl limits

### Speaker notes

Connect each term to an implemented boundary. Hardware cycles and retired instructions
are optional PMU events; software operation counters are different. CSR exposes
contiguous edge-array opportunities but does not prove a cache hit. OpenMP workers
cooperate with atomics and barriers; hardware logical contexts can share one
physical core. The theoretical Amdahl curve uses an assumed f, while measured
speedup requires the same algorithm and input. No usable PMU counters were present
in the archived workload receipts, so instruction and cache claims stay qualified.

## Slide 05 — System architecture

### On slide

- Seeded generator → validated CSR loader → query/experiment engine
- Verified steady-clock trials and optional scoped PMU records
- Versioned receipts → safe adapters → dashboard and exports

### Speaker notes

Walk through architecture diagram 1. The CLI runs the workload and emits results;
the dashboard reads data rather than executing uploaded code. Loading, oracle
construction and verification are outside benchmark clocks, while allocation
inside a graph algorithm is included. The Python UI is optional and isolated from
the CMake dependency graph. Trace a source manifest, loaded-CSR identity, build
metadata and receipt hash through the pipeline. Their roles differ: reproducible
input identity does not establish identical timing or dedicated hardware.

## Slide 06 — Graph representation and memory

### On slide

- CSR: offsets plus contiguous destination and weight arrays
- Archived chain: equal 56-byte edge payload in both layouts
- Accounted footprints: 200 B CSR, 280 B adjacency; RSS is separate

### Speaker notes

Use the illustrative CSR row slices in architecture diagram 4; the example is not
benchmark evidence. For the actual archived eight-vertex chain, metadata/capacity
and container terms explain the accounting difference. Whole-process RSS includes
both layouts and runtime allocations; it cannot be assigned to CSR alone. These
accounting categories overlap and are not additive stacks. Tiny layout query
medians favor adjacency in those samples, showing why smaller accounting size is
not a sufficient runtime prediction. Fixed order and submicrosecond calls limit inference.

## Slide 07 — CPU profiling pipeline

### On slide

- Real paired events: cycles/instructions, cache and branch events
- Preserve raw values, enabled/running times, status and scope
- Denied PMU values remain null; OpenMP aggregation is unsupported

### Speaker notes

Explain diagram 2 and the Linux perf_event_open backend. Sequential Dijkstra follows
the calling thread without inheritance; existing OpenMP workers are not included.
The project therefore refuses a caller-only proxy as a multicore total. Available
multiplexed values use raw times enabled divided by running, subject to scheduling
validation. IPC and CPI use compatible same-group operands, never elapsed time.
Permission-denied is an informative experimental outcome, not a reason to fabricate
counter graphs. Diagnostic probe arithmetic is separate from graph measurements.

## Slide 08 — Cache hierarchy and locality

### On slide

- Spatial locality: nearby addresses; temporal locality: repeated active data
- Archived sequential/strided/random/temporal medians: 81.673/279.482/265.837/82.354 us
- Capacity markers are metadata; these timings do not prove cache transitions

### Speaker notes

All four archived patterns perform 131,072 indexed reads with n=5 per configuration.
Temporal uses a 4 KiB active prefix while the other three use 1 MiB. The same scalar
load kernel controls the basic access mechanism; indices, reuse, translation and
shared-host effects remain. Cite the derived RESULTS.md and show the ranges rather
than treating the medians as precise architectural constants. The cache study
varies working set at fixed read count. No verified L1/L2/L3 miss count or transition
can be claimed from the available wall timing.

## Slide 09 — Multicore processing

### On slide

- Persistent OpenMP team with atomic labels and bucket barriers
- Separate equal-work scheduling/reduction/atomic/critical kernels
- More workers can add dispatch, contention and synchronization cost

### Speaker notes

The engine retains validated delta-stepping rather than altering its schedule for a
demo. Dedicated kernels isolate controlled useful work when comparing strategy and
chunk size. Reduction combines private partial sums, while atomic and critical
variants synchronize each item; measured totals also contain computation and
worksharing overhead. All checksums are consumed and verified. Close sampled timings
do not prove a universal strategy ranking. Optional kernel binding verifies sparse
allowed CPU IDs and restores masks; scaling records external placement separately.

## Slide 10 — Experimental setup and uncertainty

### On slide

- Release build, deterministic inputs, recorded machine/build/scope
- Phase 4: 15 measured + 2 warmup randomized blocks, seed 42
- One visible physical core, two SMT contexts; no dedicated-core proof

### Speaker notes

Distinguish the older Phase 2 recorded CPU from Phase 4/5 metadata; do not pool their
samples. The scaling graph is a 128x128 bidirectional grid with 16,384 vertices and
65,024 edges, source zero and delta 16. Requested and observed teams were 1/1 and
2/2. Trial order is reproducible but host timing is not. Report median, range and
MAD as descriptive statistics, not confidence or significance. Quota and affinity
are visible restrictions, not a promise of independent physical processors.

## Slide 11 — Measured scaling and assumed theory

### On slide

- One-thread delta-stepping median: 3.512313 ms
- Two-thread median: 2.690738 ms; S(2)=1.3053, E(2)=0.6527
- Assumed f=0.95 predicts 1.9048×; it is not a measured fraction

### Speaker notes

Show actual medians with the same-algorithm baseline. Dijkstra is an oracle and a
separate algorithm comparison, not T(1) here. The one-thread range reaches 14.749020 ms
and the two-thread range 10.924383 ms, so avoid implying low environmental noise.
Amdahl's curve omits extra overhead and assumes independent useful capacity.
Observed SMT timings cannot prove scaling across separate physical cores, nor does
the gap from a chosen curve identify a fitted serial fraction. Source: committed
Phase 4 scaling.json and independently derived academic results.

## Slide 12 — Interactive dashboard and reproducibility

### On slide

- Seven views: architecture, metrics, memory, locality, scaling, theory, explorer
- 13 authentic archived receipts; safe JSON/CSV imports and filtered exports
- Unknown ≠ zero; archived ≠ live; theoretical ≠ measured

### Speaker notes

Use the five-to-seven-minute LIVE_DEMO.md after the talk. Start with CPU metadata,
then denied counters and wall time, memory accounting, locality and same-algorithm
scaling. The dashboard exposes source/build/scope and checks archived hashes.
Standalone CSV permits raw inspection but lacks enough metadata for speedup inference.
Amdahl overlay is optional and compatibility-gated. JSON selections preserve original
values and selected row IDs. AppTest and HTTP startup were checked; a real browser
and classroom projector still require manual visual review.

## Slide 13 — Limitations and ethical reporting

### On slide

- PMU unavailable; no worker aggregation or verified cache-miss attribution
- Shared SMT environment, small/fixed-order samples and untested browser rendering
- Preserve upstream attribution; licensing clearance remains unresolved

### Speaker notes

State these limitations without treating them as hidden footnotes. Sanitizers and
correctness tests are evidence for tested executions, not formal proofs or a race
detector. Phase 2/3 order and small examples can bias performance comparisons.
No screenshots, visual dashboard QA, PowerPoint rendering or institutional approval
are claimed. The import has a pinned source commit but no recorded license grant;
technical reuse authorization does not invent downstream redistribution rights.
Resolve licensing before presenting this as an unrestricted open-source package.

## Slide 14 — Conclusion and future scope

### On slide

- A verified COA teaching workflow with explicit experimental boundaries
- Final report, diagrams, slides, demo, 60 viva answers and reproduction scripts
- Next: licensing, manual display review, authorized PMU and independent-core studies

### Speaker notes

The project's achievement is an understandable and reproducible connection between
software work and architectural concepts. It is not a claim of maximum hardware
performance or a new shortest-path algorithm. Prioritize licensing and manual
presentation/browser review before external distribution. A later performance study
should document dedicated independent cores, frequency/NUMA/cache controls,
validated PMU scope and a planned statistical analysis. Such future work must create
new receipts instead of retroactively changing historical evidence. Point reviewers
to FINAL_EVALUATION.md for a criterion-by-criterion assessment without perfect scores.

## Slide 15 — Questions

### On slide

- What is the baseline, scope and unit of each displayed quantity?
- Which outcomes were measured, unavailable or assumed?
- Academic index: docs/academic/README.md

### Speaker notes

Invite questions using the three distinctions on the slide. Be ready to explain
why logical CPUs differ from physical cores, why Dijkstra is not the scaling
baseline, why RSS differs from footprint accounting and why a theoretical Amdahl
curve is not a measurement. Use VIVA_QA.md for 60 prepared answers and the evidence
index for exact receipts and commands. If asked for cache misses or IPC on the
restricted host, explicitly answer that those measurements are unavailable rather
than converting wall time or software work into unsupported hardware metrics.
