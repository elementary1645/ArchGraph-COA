# Locality experiments and result contract

Spatial locality means nearby addresses may be used together, making transferred
cache lines useful. Temporal locality means data may be reused while still cached.
CSR places edge arrays contiguously; an adjacency list groups edges within a row
but requires another row's vector/pointer to find its allocation. Random indexing
adds an indirect address lookup and can spread reads across cache lines/pages.
These are opportunities and costs, not guaranteed hardware outcomes.

## Reproducible demonstration

Build as in README. All sizes below are **bytes**, aligned to eight; strides are
**elements**. These commands are runnable experiments, not illustrative results:

```sh
build/phase3-release/archgraph locality --pattern sequential --size 1048576 --runs 3
build/phase3-release/archgraph locality --pattern strided --size 1048576 --stride 16 --runs 3
build/phase3-release/archgraph locality --pattern random --size 1048576 --seed 1 --runs 3 --hardware-counters
build/phase3-release/archgraph locality --pattern temporal --size 1048576 \
  --working-set 4096 --accesses 1048576 --runs 3
build/phase3-release/archgraph locality --pattern temporal --size 1048576 \
  --working-set 1048576 --accesses 1048576 --runs 3
build/phase3-release/archgraph locality --pattern csr --input data/phase3-chain/graph.txt --passes 3 --runs 3
build/phase3-release/archgraph locality --pattern adjacency --input data/phase3-chain/graph.txt --passes 3 --runs 3
```

For array patterns, setup initializes `data[i] = (i * 0x9e3779b97f4a7c15) XOR seed`
with unsigned 64-bit wraparound, and builds a uint32 index sequence. Sequential
indices enumerate 0..N-1; strided indices enumerate residues then jumps by stride,
visiting every index once even when stride and N share factors. A stride at least
N degenerates to sequential order; a different stride need not imply different
locality. Random and temporal sequences use SplitMix64 with an unbiased bounded
draw and Fisher–Yates shuffle. The transition is attributed to the imported
Python generator. These definitions are independent of standard-library shuffle
implementation choices. The seed, sequence fingerprint and parameters are recorded.

All three spatial patterns use the **same indexed scalar kernel**, including one
index load and one uint64 data load per access. This controls the extra index-stream
work rather than comparing an optimized direct scan to an indexed random scan.
Volatile data/index reads force every load on every trial; they constrain compiler
vectorization, so this is an instructional scalar experiment, not peak bandwidth.
`--accesses` defaults to one full permutation, then cycles if more reads are requested.
Full permutation cycles produce equal checksum/useful data reads across spatial
patterns. Partial cycles may touch different subsets; `distinct_data_elements` and
read counts make that limitation explicit. A checksum is verified modulo 2^64,
stored for each trial and serialized, so results are consumed.

Temporal experiments allocate `--size` bytes but access a shuffled prefix of
`--working-set` bytes. They default to at least 1,048,576 reads and at least one full
prefix sweep; explicit `--accesses` overrides that count. Comparing the two commands
above keeps allocation size and read count fixed while changing active data and
index footprints. The larger allocation's inactive tail is not part of the accessed
working set. The sequence itself consumes memory/cache. Neither smallness nor prior
access proves a hit; no cache flushing, page eviction or guaranteed cold start occurs.

Graph patterns load both layouts before timing. Each pass visits every edge,
reading destination and weight; both produce the sum of `(destination << 32) | weight`
modulo 2^64. `edge_visits` and passes are recorded. CSR also reads offsets; adjacency
traversal reads row descriptors and follows row pointers. Equal edges/checksums do
not mean equal instructions, total memory traffic or loop overhead, and neither is
equivalent useful work to array traversal or SSSP. Both layouts coexist in memory.

## Timing boundaries

Initialization, input loading, layout conversion, index generation, expected checksums,
reference SSSP, warmups, sample allocation, result validation and serialization are
outside timing. Bounds validation of access sequences is setup work. Array and graph
traversals allocate nothing inside their clocks. SSSP layout comparisons include
algorithm allocation, like Phase 2. Warmup and measured repetitions execute identical
kernels. Every measured result is validated after counters/clocks stop. No completed
JSON is emitted if a checksum or full distance comparison fails.

Phase 2's monotonic wall clock, build metadata, graph identity and counter lifecycle
are reused. The shared runner opens fresh descriptor sessions per trial, avoiding
cumulative scheduling times. PMU windows slightly surround wall time and include
control/clock overhead. Timings are individual nanoseconds with an exact central
sample or arithmetic midpoint median. Debug is useful for checks, Release for
exploration; build type and flags are explicit. Do not compare Debug and Release
as if they were identical experiments. Fixed order, warm caches, page faults, thread
migration, shared hosts, prefetching, TLB and compiler choices limit interpretation.

## Versioned JSON schema

New commands use `schema: archgraph-memory-experiments`, `schema_version: 1`.
Existing `bench`/`sssp` schemas and option behavior remain intact.

- Common envelope: `command`, `status`, `verified`, `repetitions`, `warmups`,
  `hardware_counters_requested`, `measurement_scope`, CPU/build `metadata`,
  `cache_info`, `environment_diagnostic` and `warnings`. The environment diagnostic
  is a separately labeled platform probe outside timing, not a measured graph/array result.
- `memory`: graph counts, unchanged Phase 2 `input_identity`, two `layouts` accounting
  records and whole-process `process_memory`. It has no measured trials and rejects
  `--hardware-counters`; common repetition defaults describe configuration only.
- `compare-layouts`: adds source, `outputs_identical`, fixed trial order, and separate
  `csr_dijkstra`/`adjacency_dijkstra` timing records. Checksums consume full distance
  vectors; verification compares every element, not only the checksum.
- Array `locality`: `experiment` records pattern, data allocation/active bytes,
  sequence payload, combined vector capacity, actual distinct data elements, data
  and index read counts, stride, seed, `sequence_fingerprint_u64`, expected checksum,
  read/write pattern and `timing`.
- Graph `locality`: records pattern, passes, edge visits, expected checksum and timing
  beside graph identity/accounting. No array seed is used.
- `cache-study`: `plan_mode`, `omitted_capacity_targets`, maximum data bytes and an
  ascending-size `experiments` array with common read count and seed.
- A timing record contains `median_wall_ns`, overall `counter_status` and individual
  `runs` with wall ns, consumed checksum, six memory event records and derived
  same-pair L1D/LL/DTLB read-miss ratios. Raw counts, enabled/running times, scaled
  values, errno/status and diagnostics follow Phase 2. Missing/invalid numbers and
  zero-denominator ratios are null; actual measured zero counts remain zero.

`sequence_fingerprint_u64` is FNV-1a over each sequence index encoded as uint64
little-endian. Graph fingerprints retain `fnv1a64-csr-le-u64-v1`. These are
noncryptographic; keep generator manifests for file SHA-256 and seed provenance.
Raw checksums/counts can exceed JavaScript's exact integer range, so consumers must
preserve uint64 JSON integers. No timings are interpreted as cache misses or cycles.
Use `archgraph --help` or any new command's `--help` for the complete interface.
Limits: data size at most 256 MiB, reads at most 100 million, repetitions/passes at
most 10,000, warmups at most 10,000, and at most 64 explicit study sizes. These are
input bounds, not automatic workload isolation or a time-budget guarantee.

For a professor: first show equal graph outputs and equal full-cycle checksums,
then explain controlled reads, extra index/representation work and footprint
accounting. Finally inspect actual cache metadata and counter status before
comparing wall medians. A restricted machine still demonstrates reproducibility,
correctness and honest null metrics.
