# Memory organization and graph layouts

CSR stores one contiguous offset array and contiguous destination/weight arrays.
Offsets select each vertex's edge range. The experimental adjacency list stores a
vector of row vectors, each containing `{uint32 destination, uint32 weight}` pairs.
A row's edges are contiguous, but different rows have separate allocations. This
is a vector-based adjacency list, not a linked list with one allocation per edge.
Both layouts use the same vertex IDs, directed edges, uint32 weights, self-loops,
zero weights and disconnected vertices. **Duplicate directed edges are rejected**,
including duplicates with different weights, exactly as in the imported CSR API;
neither format supports parallel edges. No input is silently deduplicated.

Conversion copies canonical CSR rows in order. Conversion back uses the existing
validated CSR builder, preserving canonical offsets, destinations, weights and edge
ordering. The imported graph engine and its algorithms remain unchanged. An isolated
adjacency-list Dijkstra adapter in `src/experiments/layout.cpp` reuses the upstream
lazy-heap algorithm loop with only its graph/range types adapted. Its attribution
points to the unchanged import provenance. Every layout comparison verifies complete
distance vectors against the original Dijkstra baseline after timing; tests also
use independent Bellman–Ford oracles, including seeded graphs and boundary weights.

## Understanding the accounting

`archgraph memory --input graph.txt` builds both layouts and reports:

| Field | Meaning |
| --- | --- |
| `logical_payload_bytes` | E times the sizes of destination and weight fields; equal useful edge payload for both layouts |
| `used_metadata_bytes` | CSR's used offsets, or the adjacency list's used row-vector descriptors |
| `capacity_storage_bytes` | Actual vector capacities times ABI element sizes, including unused slots and row descriptors; allocated buffer accounting, not resident memory |
| `container_object_bytes` | `sizeof` the owning C++ graph object, including its vector control objects and padding |
| `container_overhead_estimate_bytes` | Object bytes plus used layout metadata, an ABI-based control-storage estimate; not measured allocator or physical overhead |
| `allocation_blocks` | Number of nonzero-capacity vector buffers: up to three CSR buffers, or outer adjacency buffer plus nonempty-capacity rows |
| `allocator_overhead_bytes` | Null: allocator headers, size-class rounding, fragmentation and retained arenas are not portably attributable |
| `accounted_total_bytes` | Capacity-storage bytes plus owner-object bytes; excludes unknown allocator overhead |
| `physical_memory_bytes` | Null per layout; vector capacity cannot determine resident pages |

Capacity already includes used payload/metadata; adding those fields again would
double-count. `sizeof`/capacity describe C++ storage for this build, not a universal
ABI. Allocation counts expose potential per-allocation overhead without inventing
an allocator-header size. Temporary conversion buffers, Dijkstra queues/results,
shared libraries and runtime state are outside per-layout accounting.

Where available, `process_memory.rss_bytes` reads Linux `/proc/self/statm` resident
pages multiplied by `_SC_PAGESIZE`. It is a coarse **whole-process** snapshot after
both representations coexist, including code, runtime and other allocations. It is
not a per-layout physical footprint and no RSS difference is used to infer one.
Unknown values are null. Larger capacity, more allocation blocks or higher RSS do
not alone establish slower execution.

## Professor demonstration

Generate the deterministic chain as in README, then run:

```sh
build/phase3-release/archgraph memory --input data/phase3-chain/graph.txt
build/phase3-release/archgraph compare-layouts --input data/phase3-chain/graph.txt \
  --source 0 --repetitions 3 --warmups 1
```

Explain which fields are counted storage, which are estimates and which are process
observations. Show `outputs_identical: true`, per-trial checksums and the two SSSP
medians. Conversion/loading occur before measurement; algorithm allocations remain
inside SSSP timing, consistently with Phase 2. Comparisons run all CSR trials before
adjacency trials (`order: csr_then_adjacency`); order/cache/allocator bias is a stated
limitation, not a controlled performance result. Empty graphs support accounting
and traversal; SSSP on an empty graph rejects every source, matching the baseline.
