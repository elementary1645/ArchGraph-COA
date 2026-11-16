# Phase 1 validation

Executed locally on 2026-11-16. GCC 13.3.0, CMake 3.28.3, Python 3.14.2,
OpenMP 4.5 (`_OPENMP=201511`), Linux. The reported CPU model is AMD EPYC 9V74
80-Core Processor; the runtime's logical concurrency hint is 2. This is a shared
container and does not establish exclusive cores or stable performance conditions.

## Commands and actual outcomes

```sh
cmake -S . -B build/debug -DCMAKE_BUILD_TYPE=Debug -DARCHGRAPH_WARNINGS_AS_ERRORS=ON
cmake --build build/debug --parallel 2
ctest --test-dir build/debug --output-on-failure
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DARCHGRAPH_WARNINGS_AS_ERRORS=ON
cmake --build build/release --parallel 2
ctest --test-dir build/release --output-on-failure
```

Both build trees started absent. Debug was rebuilt after separating timing from
CLI parsing. Final Debug and Release builds succeeded with all warnings treated as
errors under `-Wall -Wextra -Wpedantic -Wconversion -Wshadow`; no compiler warnings
were observed. [Raw local logs](validation/) record compilation and test outcomes.

| Configuration | Registered | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Debug | 14 | 14 | 0 | 0 |
| Release | 14 | 14 | 0 | 0 |

Exactly 28/28 CTest executions passed across the two configurations. CTests are:
`project_info`, `openmp`, `csr_graph`, `edge_list_io`, `dijkstra`, `delta_stepping`,
`cli_help`, `cli_version`, `cli_cpu`, `cli_invalid`, `cli_sssp`,
`workload_artifacts`, `workload_loader`, `benchmark_integration`.

Each configuration includes six original native test executables, five CLI checks,
and three Python suites. Python suites contain 22 artifact methods, 1 loader method
and 2 new metadata/benchmark methods: 25 Python methods per configuration, nested
inside CTest rather than additional CTests. Native harnesses contain multiple
assertions/cases, not individually registered tests. A focused verbose rerun of the
three Debug Python suites also passed 3/3 CTests (25 methods); this is additional
verification, not an increase in registered coverage.

## Coverage and CLI checks

- Dijkstra is checked against independent synchronous Bellman–Ford on hand-built
  and deterministic random cases, including unreachable vertices and large weights.
- Delta-stepping is compared against the oracle and Dijkstra, with multiple delta
  values, worker counts, repeated calls and original edge-case/metric checks.
- The original CLI integration checks exact JSON, uint64 paths, null infinity,
  invalid files/numbers, duplicate options and requested/observed worker bounds.
- Artifact tests retain fixed fingerprints, recipe verification and deterministic
  generation; loader integration checks all generated graph families and final
  graph states against a Python Bellman–Ford oracle.
- New benchmark tests verify both algorithm paths, repeat counts, nonnegative wall
  samples, explicit unknown timed team size, metadata and invalid repetition limits.

All README quick-start commands were executed successfully: generation/verification,
help/version/CPU, both SSSP commands and both five-sample benchmark commands.
The chain graph produced identical distances with both algorithms:
`[0,32,51,76,100,119,139,162]`; SSSP observed two OpenMP workers for a request of two.
Benchmark numbers from this tiny smoke input are diagnostics only and are not
published as performance results.

## Limits and exclusions

No retained test was skipped. Upstream adaptive, incremental, research campaign,
publication, combined-system and failure-injection suites were excluded with their
modules and were not executed or counted as passing. The original full research
suite is not claimed for this reduced project. Hardware counters, controlled
scaling, cache studies, sanitizers and TSan were not executed in Phase 1. Hosted
GitHub Actions has been configured but no hosted success is claimed. Other
compilers/platforms are not validated. Source licensing remains unresolved as
recorded in IMPORT_PROVENANCE.md. Timing is wall time, with no hardware-cycle,
IPC, speedup or race-freedom claim.
