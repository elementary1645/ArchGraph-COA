# Roadmap

1. **Phase 1 — implemented:** standalone imported CSR/SSSP engine, deterministic
   generation, baseline correctness, CPU/build metadata and verified wall timing.
2. **Phase 2 — implemented:** Linux calling-thread user-space counters for sequential
   Dijkstra (cycles, instructions, generic cache and branch events), valid derived
   ratios, multiplexing checks, independent availability diagnostics and permission
   fallback. Real PMU access is unavailable in this environment; software contracts
   are tested with a syscall abstraction. OpenMP hardware aggregation is deferred.
3. **Phase 3 — implemented:** vector-based adjacency-list/CSR comparison, explicit
   memory accounting, deterministic spatial/temporal read kernels, metadata-sized
   working-set plans and optional L1D/LL/DTLB read counters with honest fallback.
   Local timings do not establish cache transitions or controlled speedups.
4. **Phase 4 — implemented:** verified same-algorithm OpenMP scaling, randomized
   blocks, efficiency/Amdahl analysis, topology/quota reporting, equal-work scheduling
   and synchronization kernels, optional kernel affinity, JSON/CSV and validation.
   Shared-host SMT observations do not establish physical multicore scaling.
5. **Phase 5 — implemented:** local Streamlit/Pandas/Plotly dashboard, safe schema-aware
   JSON/CSV imports, seven views, authentic archived demo receipts, filtered exports,
   null-aware hardware metrics and explicitly theoretical Amdahl exploration.
   Visual browser QA and authenticated physical-host equivalence are not established.
6. **Phase 6 — implemented:** 19-section academic report, seven Mermaid diagrams,
   15-slide notes/editable PPTX, 60 viva answers, qualified final evaluation,
   PMU-independent demo and fresh-output reproduction/authoring scripts.
   Final builds/tests/sanitizers and archive integrity pass; manual browser/slide
   rendering and upstream licensing clearance remain explicit conditions.

Each phase needs its own correctness and measurement validation. No historical
DynaGraph experiments establish ArchGraph performance. Dynamic graph repair and
adaptive selection are outside this project's current COA scope.
