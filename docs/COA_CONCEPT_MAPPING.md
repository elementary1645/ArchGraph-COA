# COA concept mapping

| COA concept | Implemented connection | Deferred measurement |
| --- | --- | --- |
| Instruction execution | Heap Dijkstra and bucket delta-stepping exercise distinct control flow; software work counts describe algorithm operations | Instructions, cycles, IPC and branch events |
| Cache hierarchy | CSR stores contiguous offsets, destinations and weights; indexed labels and heaps create other access patterns | Cache hits/misses and controlled locality experiments |
| Memory organization | Explicit CSR ownership, uint32 weights and uint64 labels expose representation and working-set choices | Bandwidth, NUMA and working-set sweeps |
| Multicore processing | OpenMP teams, barriers and atomic relaxation implement parallel SSSP; correctness is checked against Dijkstra | Controlled scaling, efficiency and synchronization costs |
| Performance analysis | Repeated monotonic wall timing, deterministic input hashes and CPU/build metadata | Hardware-counter collection and statistically qualified conclusions |

Wall time includes OS scheduling and runtime overhead. Algorithm work counts are
software events, not retired instructions. CPU/model hints are metadata, not
measurements of cache behavior or exclusive physical-core allocation.
