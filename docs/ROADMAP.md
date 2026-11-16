# Roadmap

1. **Phase 1 — implemented:** standalone imported CSR/SSSP engine, deterministic
   generation, baseline correctness, CPU/build metadata and verified wall timing.
2. **Phase 2 — future:** availability-aware hardware counters for cycles,
   instructions and IPC, with permission failures reported explicitly.
3. **Phase 3 — future:** cache locality, memory organization, working-set and
   memory-access experiments with controlled inputs.
4. **Phase 4 — future:** OpenMP scaling, thread efficiency and overhead with observed
   team/affinity information and interference assessment.
5. **Phase 5 — future:** visualizations of actual CPU, memory, cache and multicore results.
6. **Phase 6 — future:** academic report, presentation, architecture diagrams,
   reproducible demonstration and viva preparation.

Each phase needs its own correctness and measurement validation. No historical
DynaGraph experiments establish ArchGraph performance. Dynamic graph repair and
adaptive selection are outside this project's current COA scope.
