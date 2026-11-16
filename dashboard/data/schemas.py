"""Supported producer contracts. Never identify a document by filename alone."""
MEMORY_SCHEMA = "archgraph-memory-experiments"
MULTICORE_SCHEMA = "archgraph-multicore-experiments"
SELECTION_SCHEMA = "archgraph-dashboard-selection"
CSV_COLUMNS = (
    "schema_version", "block", "warmup", "strategy", "chunk", "requested_threads",
    "observed_threads", "wall_ns", "checksum", "affinity_applied", "affinity_restored",
)
MEMORY_COMMANDS = {"memory", "compare-layouts", "locality", "cache-study"}
PATTERNS = {"sequential", "strided", "random", "temporal", "csr", "adjacency"}
STRATEGIES = {"delta-stepping", "static-reduction", "dynamic-reduction", "static-atomic", "static-critical"}
EVENTS = {"cpu_cycles", "instructions", "cache_references", "cache_misses", "branch_instructions", "branch_misses",
          "l1d_read_accesses", "l1d_read_misses", "ll_read_accesses", "ll_read_misses", "dtlb_read_accesses", "dtlb_read_misses"}
VALID_COUNTER_STATES = {"available", "multiplexed"}
MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100_000
