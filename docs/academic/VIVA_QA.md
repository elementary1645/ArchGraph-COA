# Viva preparation: 60 questions with answers

Answers describe this repository and its recorded evidence. When a measurement is
unavailable, say so directly; do not fill a conceptual explanation with invented
hardware numbers. Use PROJECT_REPORT.md for references and FINAL_VALIDATION.md
for exact test results.

## CPU architecture and instruction execution

### 01. Why is this a COA project rather than only a graph-algorithm project?

The graph queries are workloads for studying instruction metrics, memory layout,
locality, scheduling and synchronization. The project records scopes, topology,
repeated timings and limitations, and connects them to CPU/memory concepts through
experiments and a dashboard. It does not claim a new shortest-path algorithm.

### 02. What is the difference between a C++ operation and a retired instruction?

A compiler can translate an operation into several instructions, combine operations
or eliminate unused work. A retired instruction is a machine-level event that
completes architecturally. Software relaxations or edge visits cannot be reported
as retired instructions without an appropriate hardware measurement.

### 03. What does a CPU cycle count measure?

It counts the selected PMU cycle event while the measured execution context is
scheduled in the configured scope. Frequency, event mapping and virtualization
matter. The project's event is not automatically process-wide, and a wall-clock
nanosecond is not a CPU cycle.

### 04. Define IPC and CPI.

IPC is retired instructions divided by counted cycles. CPI is cycles divided by
instructions; each denominator must be positive and operands must have compatible
scope and scheduling. They are reciprocals when both counts are positive. Missing
counts produce unavailable ratios rather than values derived from wall time.

### 05. Does higher IPC always mean a faster program?

No. Programs can execute different instruction counts, frequencies and work. A
program with more instructions can have high IPC yet take longer. Compare useful
work, scope and wall/CPU timing separately; this host did not provide usable IPC
measurements for the archived workloads.

### 06. What do pipelining and out-of-order execution contribute?

They allow different operations to overlap while respecting dependencies and
architectural behavior. Data dependencies, cache delays, branches and execution
resources limit that overlap. This project motivates those effects but does not
measure pipeline-stage latency or reconstruct an instruction trace.

### 07. Why can branch prediction affect graph workloads?

Checks for stale entries, shorter distances and bucket work can lead to varying
branch outcomes. Mispredictions can discard speculative work. The optional branch
instructions/misses pair could investigate this, but denied counters mean the
project cannot assert a measured branch-miss rate from elapsed time alone.

### 08. Explain SISD and MIMD in this project.

Sequential Dijkstra is a SISD teaching example: one software instruction stream
executes the query. OpenMP workers provide a MIMD model with independent instruction
streams cooperating on shared graph state. This taxonomy does not establish
whether a compiler also uses SIMD instructions inside a worker.

## Memory organization and representations

### 09. What is CSR?

Compressed Sparse Row stores an offset per row boundary and contiguous edge
arrays. Outgoing edges for vertex u lie between offsets[u] inclusive and
offsets[u+1] exclusive. This implementation separates uint32 destination and
weight arrays and uses uint64 offsets.

### 10. Why are V+1 offsets required?

The extra offset marks the end of the last row. Each row length is
`offsets[u+1]-offsets[u]`, including empty rows. The final offset must equal the
edge count; validating these relationships prevents invalid slices.

### 11. What is CSR's logical storage formula here?

Destination and weight payloads require 8E bytes in total. Used offset metadata
requires 8(V+1) bytes. Actual vector capacities, container objects and unknown
allocator overhead are separate; the formula is not measured resident memory.

### 12. How does an adjacency list differ from CSR?

It uses a vector of rows, each with its own edge storage. This can add per-row
metadata and allocations. CSR groups its edge arrays contiguously. Both can
represent the same directed weighted graph, but footprint opportunities alone
do not guarantee which query implementation is faster.

### 13. What did the archived tiny memory example actually show?

Both representations held 56 bytes of logical edge payload for seven edges.
Accounted capacity-plus-container totals were 200 bytes CSR and 280 bytes adjacency.
Those are representation accounting, not per-layout physical memory measurements.
The eight-vertex example is too small for broad performance conclusions.

### 14. Why is RSS not per-layout memory usage?

RSS is a whole-process resident snapshot containing runtime, libraries, stacks,
working allocations and both layouts. The snapshot cannot identify which resident
pages belong exclusively to CSR. The dashboard therefore separates RSS from
representation accounting and leaves per-layout physical memory unavailable.

### 15. Are all memory-accounting fields additive?

No. Payload, used metadata, capacities and overhead estimates overlap. Accounted
total already includes vector capacity and container object terms; adding every
shown estimate again double-counts storage. The dashboard groups categories rather
than stacking them as independent memory contributions.

### 16. Why can a smaller representation still have a slower sample?

Runtime also depends on instructions, allocation, access pattern, branch behavior,
cache state and host interference. The archived tiny layout medians favored
adjacency despite its larger accounted footprint. Fixed CSR-then-adjacency order
and submicrosecond calls prevent a general causal conclusion.

## Cache hierarchy and locality

### 17. What is spatial locality?

It is reuse of nearby addresses, often making transferred cache-line contents
useful. Contiguous CSR edge arrays and sequential scans provide opportunities.
Whether accesses hit a specific cache depends on actual hardware, state and
sharing; contiguous storage alone is not a measured hit rate.

### 18. What is temporal locality?

It is reuse of data over time. The temporal kernel repeatedly visits a configurable
active prefix within a larger allocated array. A smaller active prefix can improve
reuse opportunities, but cache residence and the cause of a timing difference
must not be asserted without suitable evidence.

### 19. How do the spatial-pattern experiments control useful work?

They use the same indexed scalar load kernel and deterministic data, performing
the specified number of data and index reads. A full permutation visits each
active element once before repeating. Different sequences can still change
instruction/translation behavior, so equal reads do not mean identical hardware work.

### 20. Why use volatile loads and output checksums?

Volatile scalar reads require the accesses to occur, and consumed checksums verify
the result. Setup and expected checksum generation happen outside timing.
Volatile restricts optimization/vectorization, so this is an instructional kernel,
not a claim of peak vectorized memory bandwidth.

### 21. Why count the index stream's footprint?

Indexed access loads both an index and the addressed data. Indices occupy cache
and memory and can alter locality. Reporting only data-array size would omit part
of the working set and could misattribute a timing change to the data alone.

### 22. What is a cache line, and what is not known here?

A cache line is a unit of storage/transfer in a cache. Available OS metadata reports
line and capacity facts for a selected logical CPU. It does not prove exclusive
cache capacity, inclusion policy, current residence or the exact source of a load.
Do not assume every machine has the same line size.

### 23. Can a bend in a working-set timing plot identify L2 capacity?

Not by itself. Translation, prefetching, indexed storage, bandwidth and interference
can also change elapsed time. The dashboard's capacity markers are OS-reported
references. With denied hardware events, these results do not verify L1/L2/L3
miss rates or a specific cache transition.

### 24. What does the TLB do?

It caches address-translation information, distinct from caching application data.
A scattered access sequence can pressure translation structures as well as data
caches. Optional DTLB read/access-miss pairs remain separate metrics; the project
does not turn generic cache counters into TLB measurements.

## Graph algorithms and correctness

### 25. What graph inputs are supported?

The text format starts with V and E, then exactly E directed endpoint/weight
records. Vertices are zero-based and weights are supported uint32 nonnegative
integers. Numeric bounds, counts, endpoint validity and duplicate directed edges
are checked. Dynamic update replay is outside the retained engine's scope.

### 26. Why does Dijkstra require nonnegative weights?

Its greedy shortest-distance ordering relies on later extensions not improving a
settled distance through a negative edge. The project's supported weight domain
is nonnegative. Negative-edge shortest paths would need a different algorithm and
input contract, rather than disabling validation.

### 27. Why can a lazy heap contain stale entries?

An improved tentative distance is pushed without removing an older entry.
When the older entry is popped, it is skipped if its distance no longer matches
the current label. This is a common implementation tradeoff and a source of
extra work distinct from the abstract number of vertices.

### 28. How does delta-stepping expose parallelism?

It groups tentative distances into delta-sized buckets and repeatedly relaxes
appropriate light/heavy edges. Multiple workers scan independent work chunks,
while atomic labels and synchronized bucket publication coordinate progress.
Available parallelism depends on graph structure and bucket work, not only team size.

### 29. What does delta change?

Delta changes bucket width and the division between light and heavy edges.
It can affect work, synchronization and available parallelism. Changing it creates
a different experiment configuration; it is not valid to silently vary delta
while calling the result a pure thread-count comparison.

### 30. How is correctness checked beyond agreement between two algorithms?

Benchmarks compare full result vectors with Dijkstra, but retained algorithm tests
also use an independent synchronous Bellman-Ford oracle over input records,
including seeded and boundary cases. This reduces dependence on a single shared
reference, although finite tests are not a formal universal proof.

### 31. How are unreachable distances represented?

A reserved maximum uint64 value denotes unreachable internally. SSSP JSON emits
null for those entries. The distance arithmetic uses supported graph/weight bounds
to distinguish representable paths from that sentinel. Null is not a zero-length path.

### 32. Does a matching checksum prove shortest-path correctness?

No. Checksums can collide and do not compare each distance. Graph benchmark
correctness compares complete source/distance outputs. Dedicated traversal and
scheduling kernels use expected checksums for their defined operations, with
that narrower purpose and appropriate integer wraparound semantics.

## OpenMP and multicore architecture

### 33. What is the difference between a physical core and a logical CPU?

A physical core contains execution resources. A logical CPU is an exposed hardware
execution context; SMT can expose multiple contexts on one core. The OS schedules
software threads on those contexts. Logical count alone does not establish the
number of independent physical cores available to a container.

### 34. What hardware did the archived scaling environment expose?

The OS reported two allowed logical CPUs, IDs 0 and 1, one physical core and one
package with SMT. The model string was AMD EPYC 7763, but that branding is not an
allocation description. Hidden host sharing and virtualization fidelity remain unknown.

### 35. What is an OpenMP team, and why observe its actual size?

A team is the group of threads executing a parallel region. Runtime limits or
configuration can reduce a requested team. The scaling output records requested
and observed sizes and disables ratios when they differ, rather than assuming
that a request guarantees that many workers.

### 36. What is static versus dynamic scheduling?

Static worksharing assigns iteration chunks according to a predetermined mapping.
Dynamic scheduling hands out chunks as workers request more work. Dynamic dispatch
can help imbalance but adds overhead; static can be cheaper for uniform work.
The dedicated kernels compare them without rewriting the graph algorithm.

### 37. Why does chunk size matter?

Small chunks can improve balance but require more scheduling decisions. Large
chunks reduce dispatch frequency but can leave uneven work. The best choice is
workload- and runtime-dependent. The archived observations measure combined
computation, scheduling and synchronization, not a universal optimal chunk.

### 38. What is the difference between atomic, critical and reduction?

An atomic update protects a supported single shared update. A critical region
serializes a named block. Reduction gives workers partial state and combines it.
The kernels preserve useful transformations and checksums while changing the
combination strategy; they do not introduce races to make a comparison look faster.

### 39. Why are barriers necessary in delta-stepping?

Workers must finish producing updates before they are merged, and all must see
published bucket/work decisions consistently. Barriers provide ordering and
coordination but can add waiting when work is imbalanced. Removing them without
another valid synchronization design can break correctness.

### 40. What is CPU affinity, and how is it handled?

Affinity constrains eligible CPU IDs. IDs may be sparse and container restrictions
must be respected. The optional dedicated-kernel binding verifies applied masks
and restores each worker's original mask. Scaling records external OpenMP placement
but does not claim verified compact binding inside the graph engine.

### 41. What is a CPU quota?

It limits CPU time over a period, possibly to a fractional CPU-time capacity.
Visible cgroup ancestors can impose stricter limits than a child. A quota is not a
physical core count, and an unlimited visible quota does not prove that hidden
ancestors or host contention are absent.

### 42. What is oversubscription?

It requests more workers than the discovered affinity/quota/runtime ceiling.
The CLI rejects it by default, permits an explicit override with a warning and
records the condition. Oversubscription can increase waiting/context-switch costs;
it cannot bypass an OpenMP runtime thread limit.

## Performance analysis and instrumentation

### 43. What is the correct thread-scaling baseline?

For delta-stepping, T(1) is its own one-thread OpenMP execution on the same fixed
input/configuration. Sequential Dijkstra is a separate algorithm and an oracle.
Using its time as T(1) would mix algorithmic work differences with thread scaling.

### 44. Define speedup and efficiency using the archived result.

S(2) is 3.512313/2.690738, about 1.3053. E(2) is S(2)/2, about 0.6527. These use
medians of 15 measured delta-stepping calls per count. They are descriptive ratios
on shared SMT resources, not a controlled independent-core scalability claim.

### 45. State Amdahl's Law and its assumptions.

For assumed parallelizable fraction f and p ideal processors, speedup is
`1/((1-f)+f/p)`. It is a fixed-work theoretical model. The explorer labels f as
assumed and does not fit it from the samples; additional overhead and shared
hardware mean observed timings need not follow the curve.

### 46. Why might more threads be slower?

A graph may expose little concurrent bucket work, while team startup, allocation,
barriers, atomic contention and scheduling add cost. SMT contexts share resources,
and shared-host interference can dominate. The tiny Phase 2 Dijkstra/OpenMP times
compare different algorithms; they do not constitute a same-algorithm speedup test.

### 47. What does perf_event_open collect in this implementation?

The supported sequential scope follows the calling thread in user space with
inheritance disabled. Event pairs include cycles/instructions, cache references/
misses and branch instructions/misses. Phase 3 adds separate memory pairs. The
implementation does not aggregate existing OpenMP workers into a process-wide total.

### 48. Why are PMU events unavailable on this host?

Access depends on kernel policy, capabilities, CPU and virtualization. Recorded
opens returned permission_denied; OpenMP profiling additionally has unsupported_scope.
The project reports status/errno and null values without changing security settings.
The exact denied measurement cannot be recovered from wall time or CPU model hints.

### 49. What is multiplexing, and how is a usable value scaled?

When PMU events share hardware time, a usable count is `raw * enabled / running`.
The project checks nonzero consistent times and rejects running fractions below
10% as unreliable. Scaling is an explicit estimate for a scheduled event, not a
substitute for a denied or unsupported event.

### 50. Why group ratio operands?

Event groups schedule compatible operands together so the ratio concerns the same
counted activity window. A surviving singleton cannot create its missing partner.
The dashboard checks recorded statuses, times and derived arithmetic; it never
calculates IPC from instructions and wall-clock nanoseconds.

### 51. What is inside and outside the graph timing region?

The public algorithm call, including its own allocation and OpenMP startup, is
inside. Loading, oracle creation, result verification and serialization are outside.
Dedicated kernels have different documented boundaries, excluding allocation/team
setup. Therefore their times cannot be treated as interchangeable primitive costs.

### 52. Why use warmups and repeated trials?

Warmups reduce some startup effects without proving a stable or cold-cache state.
Repeated trials expose variability. Phase 4 stores warmups separately and excludes
them from measured summaries. The analysis uses median, range and MAD; it does not
select only a favorable run or claim a confidence interval.

### 53. What does randomized complete-block ordering improve?

Each block executes every configuration once, with a seeded shuffled order.
This reduces systematic order bias while preserving a reproducible schedule.
It cannot eliminate host interference, thermal/frequency changes, shared cache
state or SMT resource sharing. Earlier fixed-order phases retain that limitation.

### 54. What is MAD, and does it establish significance?

Median absolute deviation is the median of absolute differences from the sample
median. The reported MAD is unscaled and descriptive. It is not a confidence
interval, hypothesis test or proof that two sample medians differ causally or
statistically significantly.

## Dashboard, provenance and final delivery

### 55. How does the dashboard distinguish real, unavailable and theoretical data?

It shows integrity-checked archived receipts and labeled uploads,
keeps failed event values null and exposes their states, and labels Amdahl as a
model. Catalog hashes check file integrity, not physical hardware authenticity.
Diagnostic arithmetic is not placed on workload charts.

### 56. Why not infer speedup from a standalone CSV?

Phase 4 CSV has individual trials but lacks machine, build, graph, baseline and
scope metadata. The dashboard permits raw inspection only. Matching filenames
are not evidence that a CSV belongs to a particular JSON or algorithm experiment.

### 57. How are uploads and exports made safer?

Uploads are bounded UTF-8 JSON or exact supported CSV bytes, not executable objects
or server paths. Unsupported schemas/scopes, duplicate keys and nonfinite values
are rejected. Filtered CSV protects formula-like string cells; selection JSON
preserves the original document and exact integer values for reimport.

### 58. What do final tests and sanitizers establish, and what do they not?

They establish that the recorded builds and tested executions passed their defined
contracts. ASan/UBSan/leak detection help detect specific errors, but are not formal
proofs, a race detector or browser visual QA. Hardware skips and unavailable tools
must be reported instead of counted as passing measurements.

### 59. What is the project's source and licensing status?

The import is attributed to a pinned DynaGraph-HPC commit with a historical manifest.
No upstream license grant was recorded there. Phase 4's documented team-size
extension is audited separately. Preserve attribution and resolve licensing before
claiming unrestricted redistribution or an open-source license; do not invent one.

### 60. What should be improved before a stronger research or public release?

Resolve licensing, manually inspect browser/PowerPoint/projector presentation, and
run an authorized PMU-capable independent-core study with documented controls.
Plan statistical analysis, improve fixed-order experiments and consider race and
portability testing. New claims require new evidence rather than relabeling the
existing shared-host samples.
