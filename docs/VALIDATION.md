# Phase 2 validation

Executed locally on 2026-11-16. Phase 2 was branched from latest `origin/main`
`b241da5d68ba94017fcdc3ea17df1384be81f1d8`, which contains the Phase 1 merge.
All imported algorithm/graph sources, original test sources and import-provenance
files are unchanged. DynaGraph-HPC was not modified.

Environment: Linux x86_64, kernel `6.8.0-1070-azure`, GCC 13.3.0, CMake 3.28.3,
Python 3.14.2, OpenMP 4.5. CPU model reported AMD EPYC 9V74; affinity exposed two
logical processors. This is a shared/virtualized environment, not exclusive hardware.

## Final results

| Configuration | Registered | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Debug, warnings as errors | 17 | 16 | 0 | 1 hardware |
| Release, warnings as errors | 17 | 16 | 0 | 1 hardware |
| ASan + UBSan + leak detection, outside sandbox | 17 | 16 | 0 | 1 hardware |

Final suites total **48 passed, 0 failed, 3 hardware skips** across configurations.
These totals do not relabel skips as passes. The default build registers 16 tests;
`ARCHGRAPH_HARDWARE_TESTS=ON` adds the seventeenth. All original 14 CTests remain.
The additions are `perf_unit`, `profiling_integration` and optional `perf_hardware`.
Four Python suites contain 27 unittest methods per configuration (22 artifacts,
1 loader, 2 original benchmark, 2 profiling), nested within CTest counts. Native
assertions/subcases are not separate CTests. A final verbose Debug rerun of the
four Python suites and hardware test passed 4, failed 0, skipped 1; it is additional
verification, not additional registered coverage.

The initial sandboxed leak-detection run had 2 passing and 15 failing CTests
because LeakSanitizer could not inspect threads (`LeakSanitizer does not work under
ptrace`). Those failures are retained in `validation/phase2/sanitize-tests.txt`;
they are not described as passing or skipped. The same instrumented build was
rerun outside that sandbox with leak detection still enabled, giving the final
result above. No tests were weakened and no sanitizer suppression was added.
No hosted GitHub Actions result is claimed. CI now configures hardware tests
(with explicit skips) and adds an ASan/UBSan/leak-detection job.

## Build and test commands

```sh
cmake -S . -B build/phase2-debug -DCMAKE_BUILD_TYPE=Debug \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase2-debug --parallel 2
ctest --test-dir build/phase2-debug --output-on-failure
cmake -S . -B build/phase2-release -DCMAKE_BUILD_TYPE=Release \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON
cmake --build build/phase2-release --parallel 2
ctest --test-dir build/phase2-release --output-on-failure
cmake -S . -B build/phase2-sanitize -DCMAKE_BUILD_TYPE=Debug \
  -DARCHGRAPH_WARNINGS_AS_ERRORS=ON -DARCHGRAPH_HARDWARE_TESTS=ON \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined -no-pie'
cmake --build build/phase2-sanitize --parallel 2
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 \
  ctest --test-dir build/phase2-sanitize --output-on-failure
```

All three builds compiled successfully under `-Wall -Wextra -Wpedantic -Wconversion
-Wshadow -Werror`. No compiler warnings were observed. Raw local
[build/configuration/test logs](validation/phase2/) are retained, including the
initial sanitizer-environment failure and final successful rerun separately.

## Test coverage

- Injected syscall tests verify per-event availability, EPERM/EACCES fallback,
  unsupported events, resource exhaustion, singleton groups, exact group ordering,
  descriptor cleanup on success/partial failure/constructor exception/algorithm
  exception, session lifecycle and reset/enable/disable failures.
- Arithmetic tests check IPC, CPI, cache/branch ratios, zero/missing operands, real
  zero counts, multiplicative scaling without integer overflow, unscheduled and
  inconsistent times, and rejection below the 10% running-fraction gate.
- Invalid/partial reads, incorrect member counts, read errors and EINTR retry are
  covered without requiring PMU access. These synthetic values are software test
  fixtures, not claimed hardware observations.
- JSON integration verifies per-run records, per-event null/value semantics,
  derived-ratio gating, median, prior CLI behavior, flag placement/duplicates,
  unsupported OpenMP scope, build provenance and an independently computed loaded
  CSR fingerprint, including a changed-weight identity check.
- All retained sequential/parallel Bellman–Ford and Dijkstra comparison tests,
  graph input/output checks and deterministic artifact goldens passed unchanged.
- Optional real hardware integration performed a bounded arithmetic workload but
  could not obtain the cycle/instruction pair; it returned explicit skip code 77.
  Unexpected read/control/system failures would fail this test rather than skip.

## Actual hardware outcome and live commands

All six Linux event types are implemented: CPU cycles, retired instructions,
generic cache references/misses and branch instructions/misses. **None yielded a
valid hardware reading here.** Independent and grouped opens returned
`permission_denied` (sandboxed probes: EACCES, errno 13); `perf_event_paranoid` was 4.
This records observed denial, without attributing it exclusively to one security
layer or changing permissions. Hardware scheduling/multiplexing behavior on a
permitted real PMU remains unvalidated here; mocked contracts do not establish it.

All commands in CPU_PROFILING.md were executed successfully: generator/verification,
diagnostics, ten-repetition Dijkstra and delta-stepping counter requests. Both
algorithms returned `[0,32,51,76,100,119,139,162]` in separate SSSP smoke checks.
Help/version and original benchmarks are exercised by retained tests. Dijkstra
completed with `counter_status: permission_denied`, null counter/derived values and
verified wall samples; delta-stepping completed with `unsupported_scope`.

Retained actual diagnostic and full JSON output:
[diagnostic](validation/phase2/diagnostic.json),
[sequential smoke](validation/phase2/sequential-smoke.json),
[parallel smoke](validation/phase2/parallel-smoke.json).
These tiny-chain samples demonstrate interfaces and fallback only; they are not
qualified performance results or evidence of speedup. Their configure-time build
revision is the main base with dirty state true, accurately reflecting a local
precommit build. Reconfigure after changes to refresh build metadata.

## Remaining limits

Hardware counters are restricted to calling-thread user-space Dijkstra. OpenMP
aggregation, controlled scaling, per-level cache events, VM PMU fidelity, other
platforms/compilers and TSan race validation remain unestablished. Counter regions
include clock/control overhead; multiplexed values are explicitly scaled estimates,
not exact full-window observations. Input CSR fingerprints are noncryptographic;
retain deterministic generator manifests for SHA-256 and seed provenance. Source
licensing uncertainty remains as documented in IMPORT_PROVENANCE.md.

---

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
