# Hardware performance counters

Linux exposes processor performance monitoring units (PMUs) through
[`perf_event_open`](https://www.man7.org/linux/man-pages/man2/perf_event_open.2.html).
ArchGraph uses that syscall directly; it does not invoke `perf`, require root or
change system settings. Hardware access depends on the processor, kernel,
hypervisor, container policy and permissions. A successful open does not guarantee
that a group can be scheduled onto the PMU.

## Events and COA interpretation

| JSON event | Linux hardware event | Meaning and limits |
| --- | --- | --- |
| `cpu_cycles` | `PERF_COUNT_HW_CPU_CYCLES` | Counted core clock cycles while this thread runs in the selected privilege scope; frequency changes affect interpretation |
| `instructions` | `PERF_COUNT_HW_INSTRUCTIONS` | Retired instructions, meaning instructions that complete architecturally; speculative discarded work is not a retired instruction |
| `cache_references` | `PERF_COUNT_HW_CACHE_REFERENCES` | Generic PMU cache-reference event; exact coverage depends on CPU |
| `cache_misses` | `PERF_COUNT_HW_CACHE_MISSES` | Generic PMU cache-miss event; not an L1/L2/L3 breakdown |
| `branch_instructions` | `PERF_COUNT_HW_BRANCH_INSTRUCTIONS` | Retired branch-instruction event as mapped by the platform |
| `branch_misses` | `PERF_COUNT_HW_BRANCH_MISSES` | Branch prediction misses as mapped by the platform |

Instruction counts are different from C++ operations or algorithm work counters.
A graph relaxation may compile to many instructions. Branch misses can force the
CPU to discard speculative execution and restart; cache misses may require slower
memory accesses. Neither observation alone proves the cause of a wall-time change.
Generic cache event semantics and ratios vary by processor and should be interpreted
with its PMU documentation. Values above a ratio of one are not silently clamped.

IPC is instructions divided by cycles; CPI is its reciprocal when both counts are
positive. Cache miss ratio is misses divided by references, and branch miss ratio
is branch misses divided by branch instructions. A missing/invalid operand or zero
denominator produces JSON `null`. IPC is never derived from wall-clock duration.

## Scope and grouping

Hardware measurement is supported **only for sequential Dijkstra** in Phase 2.
`pid=0, cpu=-1, inherit=0` follows the calling thread across CPUs. Kernel and
hypervisor activity are excluded (`exclude_kernel=1`, `exclude_hv=1`). The module
does not count existing OpenMP workers or descendant threads. Delta-stepping,
including requests for one worker, reports `unsupported_scope` and still runs
verified wall-clock benchmarks. No caller-thread proxy is presented as team totals.
A thread's CPU activity and elapsed wall time are different quantities: wall time
also includes descheduling. Migration and varying core frequencies can affect results.

Three groups keep ratio operands on the same PMU schedule: cycles/instructions,
cache references/misses and branch instructions/misses. A failed event does not
prevent attempts to open the other events. Surviving events can form singleton
groups, but a missing ratio operand still gives null. Independent diagnostic opens
are reported separately from actual grouped opens and probe readings. Group reads
use `PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED |
PERF_FORMAT_TOTAL_TIME_RUNNING`; values are mapped in event creation order. Group
reset/enable/disable operations are checked. Group intervals start/stop sequentially,
so counts from different groups do not have exactly identical boundary windows;
no cross-group ratios are computed.

## Multiplexing and validation

There may be fewer physical PMU slots than requested events. Linux may time-share
groups. Every run retains raw integer counts and nanoseconds enabled/running.
A valid event value is computed as `raw * time_enabled / time_running`, using a
wide floating-point intermediate to avoid integer overflow. When times differ,
status is `multiplexed`: this value is an explicit scaled estimate of observed
activity, not a fabricated reading for an unavailable event. Such extrapolation
assumes sampled periods represent the whole region; that assumption can fail.

Zero enabled/running time or running greater than enabled is `invalid_timing`.
A running fraction below 10% is conservatively rejected as `unreliable`, retaining
raw data but returning null for scaled/derived values. This project quality gate
does not make other readings scientifically reliable by itself. Short/EOF reads,
wrong group member counts and read failures are `invalid_read`; failed ioctls are
`control_error`. Unsupported event opens, permission failures and other syscall
errors retain distinct status, errno and diagnostic text. Interrupted reads retry;
malformed data is never partially accepted. Descriptor ownership is exception-safe
and descriptors are closed once, without retrying `close` after EINTR.

## Security and virtual machines

Use `archgraph --counter-diagnostics` to inspect individual opens, grouped opens,
a small labeled arithmetic probe, scheduling times, kernel/architecture, affinity
processor count and `/proc/sys/kernel/perf_event_paranoid`. `ready` means open
succeeded, not that hardware counting was validated. The diagnostic arithmetic
probe is not graph benchmark data. EPERM/EACCES yields `permission_denied`; events
may instead be unsupported or unscheduled. A null field is unknown, not zero.

The [kernel perf security guide](https://docs.kernel.org/admin-guide/perf-security.html)
explains access controls. ArchGraph never changes these controls. On restricted
Codespaces or CI, continue with wall timing and mocked contract tests, or run the
optional hardware test on a host whose existing policy permits PMU access. A
virtual CPU may expose no PMU, incomplete events or host-dependent semantics.
This project does not establish VM counter fidelity, exclusive CPU ownership,
race freedom or controlled scaling.
