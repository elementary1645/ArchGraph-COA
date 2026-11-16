# COA concept mapping

| COA concept | Implemented connection | Deferred measurement |
| --- | --- | --- |
| Instruction execution | Sequential Dijkstra can collect real cycles/instructions and IPC/CPI when permitted; software work counts remain separate | Cross-platform PMU fidelity and controlled architectural comparisons |
| Cache hierarchy | CSR gives contiguous arrays; generic hardware cache references/misses are available when supported | Per-level cache events and controlled locality experiments |
| Memory organization | Explicit CSR ownership, uint32 weights and uint64 labels expose representation and working-set choices | Bandwidth, NUMA and working-set sweeps |
| Multicore processing | OpenMP teams, barriers and atomic relaxation implement parallel SSSP; correctness is checked against Dijkstra | Controlled scaling, efficiency and synchronization costs |
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
