# Architecture diagrams

These diagrams describe the implemented software and conceptual data paths.
They do not claim measured instruction latency, physical cache placement or
exclusive multicore resources. Plain Mermaid flowcharts and quoted labels use
GitHub-compatible fenced syntax; syntax-check results are in FINAL_VALIDATION.md.

## 1. Overall system architecture

```mermaid
flowchart TB
    S["Deterministic graph specification and seeds"] --> G["Python generator and manifest verification"]
    G --> L["Validated edge-list loader"]
    L --> C["C++17 CSR graph"]
    C --> D["Sequential Dijkstra"]
    C --> O["OpenMP delta-stepping"]
    C --> M["Memory and locality experiment adapters"]
    D --> B["Verified timing and scoped PMU runner"]
    O --> B
    M --> B
    B --> J["Versioned JSON and supported raw CSV"]
    J --> V["Validated Streamlit data adapters"]
    V --> P["Plotly views and reproducible exports"]
```

The C++ engine produces verified receipts. The dashboard consumes those receipts
without launching benchmarks. Generator manifests preserve deterministic input
provenance; the optional Python UI is not a core build dependency.

## 2. CPU profiling pipeline

```mermaid
flowchart TB
    A["Load graph and compute correctness reference"] --> Q{"Counter scope supported?"}
    Q -->|"Sequential calling thread"| F["Open fresh paired perf events"]
    Q -->|"OpenMP team"| U["unsupported_scope and null counters"]
    F --> E{"Events usable?"}
    E -->|"No"| N["Preserve status and null; continue wall timing"]
    E -->|"Yes"| R["Reset and enable groups"]
    R --> T["Steady-clock start; execute query; stop clock"]
    U --> T
    N --> T
    T --> X["Disable and read groups when opened"]
    X --> K["Validate enabled/running times and scale usable counts"]
    K --> Z["Verify complete distances outside timing"]
    Z --> JSON["Serialize samples, scope, statuses and ratios"]
```

Supported PMU collection follows the calling thread with inheritance disabled;
worker aggregation is absent. Multiplexing arithmetic cannot manufacture values
for events that failed. Wall duration and counted CPU activity remain distinct.

## 3. Graph-processing execution flow

```mermaid
flowchart TB
    I["Input: V E then directed nonnegative weighted edges"] --> V["Check counts, endpoints, duplicates and numeric bounds"]
    V --> CSR["Construct stable CSR arrays"]
    CSR --> SEL{"Selected algorithm"}
    SEL -->|"Dijkstra"| H["Lazy min-heap; discard stale entries; relax edges"]
    SEL -->|"Delta-stepping"| TEAM["Persistent OpenMP team"]
    TEAM --> BUCKET["Prepare current distance bucket and edge chunks"]
    BUCKET --> RELAX["Parallel scan and atomic label relaxation"]
    RELAX --> MERGE["Barrier; merge updates; publish next work"]
    MERGE --> MORE{"More buckets or passes?"}
    MORE -->|"Yes"| BUCKET
    MORE -->|"No"| OUT["Return source and full distance vector"]
    H --> OUT
    OUT --> VERIFY["Benchmark compares full result to Dijkstra outside clocks"]
```

The benchmark oracle is the existing Dijkstra implementation; independent
Bellman-Ford test oracles provide additional algorithm validation. Unreachable
distances use the reserved uint64 sentinel internally and JSON null in SSSP output.

## 4. CSR memory representation

```mermaid
flowchart TB
    E["Illustrative edges: 0 to 1 weight 4; 0 to 2 weight 7; 1 to 2 weight 2"] --> O["offsets: 0, 2, 3, 3"]
    E --> D["destinations: 1, 2, 2"]
    E --> W["weights: 4, 7, 2"]
    O --> RANGE["Row u occupies offsets[u] through offsets[u+1] exclusive"]
    RANGE --> SCAN["Scan corresponding destination and weight slices"]
    D --> SCAN
    W --> SCAN
    SCAN --> L["Contiguous edge arrays offer spatial locality"]
```

This three-vertex example is illustrative representation data, not benchmark
measurements. Logical edge payload uses two uint32 arrays; uint64 offsets require
8(V+1) bytes. Container/capacity and allocator costs are separate accounting terms.
The representation does not guarantee a cache hit or a faster shortest-path query.

## 5. Cache hierarchy and memory flow

```mermaid
flowchart LR
    EX["Core execution and load instructions"] --> REG["Registers"]
    EX --> L1["Conceptual L1 data cache"]
    L1 -->|"Miss may request lower level"| L2["Conceptual L2 cache"]
    L2 -->|"Miss may request lower level"| LL["Last-level cache when present"]
    LL -->|"Miss may request memory"| RAM["Main memory"]
    VA["Virtual address"] --> TLB["TLB and address translation"]
    TLB --> EX
    SYS["OS cache metadata"] -.-> MARK["Capacity reference markers only"]
```

The drawing is conceptual, not a topology or inclusion-policy claim for a
particular CPU. Caches move lines; translation uses a separate hierarchy. Prefetch,
sharing, coherence and memory-level parallelism complicate latency attribution.
The receipts lack usable PMU miss measurements, so timing is not labeled L1/L2/L3 hits.

## 6. Multicore scaling experiment workflow

```mermaid
flowchart TB
    ENV["Discover mask, SMT, quotas and OpenMP limits"] --> INPUT["Validate thread list; ensure one-thread delta baseline"]
    INPUT --> REF["Load fixed graph; run untimed Dijkstra oracle"]
    REF --> ORDER["Seeded randomized complete blocks"]
    ORDER --> WARM["Record warmup blocks separately"]
    WARM --> MEASURE["Time unchanged delta-stepping call; observe actual team"]
    MEASURE --> CHECK["Check full distances after each call"]
    CHECK --> SUMMARY["Measured medians, min, max and MAD"]
    SUMMARY --> RATIO["S(p) = T(1) / T(p); E(p) = S(p) / p"]
    RATIO --> GATE["Null ratios if baseline or observed teams incompatible"]
    GATE --> RECORD["JSON, CSV, assumptions and environment limitations"]
```

All configurations use the same algorithm and deterministic input. Requested
threads are not assumed to be physical cores. Amdahl curves are separate
predictions for an assumed parallel fraction, not fitted measurements.

## 7. Dashboard data pipeline

```mermaid
flowchart TB
    ARCH["Allowlisted archived receipts plus byte hashes"] --> LOAD["Bounded byte loader"]
    UP["Local JSON or supported CSV upload"] --> LOAD
    LOAD --> VAL["Version, structure, units, scope and arithmetic checks"]
    VAL --> RAW["Preserved producer document and provenance"]
    RAW --> ADAPT["Pure null-aware adapters and compatibility checks"]
    ADAPT --> VIEW["Seven Streamlit views and Plotly charts"]
    VIEW --> CSV["Filtered viewing CSV"]
    VIEW --> JSON["Lossless JSON selection with source and row IDs"]
    THEORY["Explicit assumed Amdahl parameters"] --> MODEL["Theoretical curve"]
    MODEL --> VIEW
```

Uploads are data rather than paths or executable objects. Diagnostic probe values
never enter workload charts. Real observations, unavailable metrics and theory
retain distinct labels; incompatible documents are not silently pooled.
