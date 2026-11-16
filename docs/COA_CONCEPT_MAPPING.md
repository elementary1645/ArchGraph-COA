# COA concept mapping

| COA concept | Implemented connection | Deferred measurement |
| --- | --- | --- |
| Instruction execution | Sequential Dijkstra can collect real cycles/instructions and IPC/CPI when permitted; software work counts remain separate | Cross-platform PMU fidelity and controlled architectural comparisons |
| Cache hierarchy | Discovered level/line/sharing metadata sizes bounded studies; optional generic and L1D/LL read pairs retain availability status | Validated PMU fidelity and evidence-supported capacity/latency attribution |
| Memory organization | CSR/adjacency accounting and equal-edge traversal; indexed spatial and temporal kernels record reads/checksums/footprints | Peak bandwidth, NUMA placement and controlled physical-memory attribution |
| Multicore processing | OpenMP teams, barriers and atomic relaxation implement parallel SSSP; correctness is checked against Dijkstra | Exclusive-core isolation and validated worker PMU totals |
| Performance analysis | Repeated monotonic wall timing, deterministic input hashes and CPU/build metadata | Validated worker aggregation and statistically qualified conclusions |

Wall time includes OS scheduling and runtime overhead. Algorithm work counts are
software events, not retired instructions. CPU/model hints are metadata, not
measurements of cache behavior or exclusive physical-core allocation.

Phase 2's Linux user-thread PMU module maps branch instructions/misses to a branch
miss ratio, and generic cache misses/references to a cache miss ratio. It keeps
paired events grouped, records multiplexing times and leaves missing/invalid ratios
null. Neither generic cache counters nor retired instruction counts reveal per-level
cache behavior or individual instruction latency. OpenMP hardware totals are
explicitly unsupported; see [counter scope](PERFORMANCE_COUNTERS.md).


Phase 3 connects spatial locality to sequential/strided/random index permutations,
and temporal locality to repeated reads of a configurable prefix. The index stream
has its own cache footprint; volatile scalar loads ensure consumption while limiting
vectorization. Metadata-derived studies span data sizes near reported capacities
where the configured cap permits; they report omitted targets and do not prove
cache-level transitions from timing. The separate DTLB pair concerns address
translation. Memory reports distinguish logical bytes, capacity/control estimates,
unknown allocator overhead and coarse whole-process RSS. Both graph layouts reject
duplicate directed edges and produce the same verified shortest paths.

Phase 4 maps SISD to the sequential oracle and MIMD to independent OpenMP workers.
Physical cores, SMT contexts and software threads are reported separately where
observable. Seeded blocks demonstrate thread scheduling and granularity; equal-work
reduction, atomic and critical kernels expose synchronization costs. Optional
worker affinity uses sparse allowed CPU IDs and restores original masks. Median
same-algorithm speedup and efficiency accompany explicitly assumed Amdahl curves.
The validation machine has one visible physical core with two SMT contexts, so
these results demonstrate methodology and overhead, not independent-core scaling.
