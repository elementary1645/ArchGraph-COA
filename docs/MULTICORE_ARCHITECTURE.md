# Multicore architecture

A sequential Dijkstra query illustrates SISD: one instruction stream processes
one data stream in the architectural taxonomy. OpenMP delta-stepping uses MIMD:
workers independently execute instruction streams over graph work. OpenMP's
worksharing model does not imply SIMD or one physical core per worker.

A physical core contains execution resources. Logical processors are hardware
thread contexts; SMT contexts can share a core's pipelines and caches. Software
threads are scheduled onto those contexts by the OS. Increasing a team can add
parallel capacity, share existing capacity, or oversubscribe it. CPU model branding
is not the number of physical cores available to a container.

`archgraph --cpu` retains Phase 1 metadata and adds `topology`. Linux discovery
uses online CPUs, a dynamically sized `sched_getaffinity` mask, and sysfs package,
core and sibling records. CPU IDs may be sparse. Physical cores and sockets count
only the current affinity set; SMT detection uses the exposed sibling lists and
can include siblings outside that set. Missing/incomplete records yield null,
not logical-processor guesses. Affinity describes the calling thread, not a
system-wide process binding guarantee. OpenMP placement can narrow that mask.
Other platforms use available status metadata and otherwise a conservative
one-thread default; physical topology and affinity may be unavailable.

Cgroup v2 `cpu.max` and v1 CPU quota/period files are probed along visible current
cgroup ancestors. The strictest discovered finite quota is reported as CPU-time
capacity, including fractional values. `unlimited_visible` means a valid visible
unlimited quota, not proof that all ancestors or host constraints are visible.
Nonstandard cgroup mount locations are not resolved. Missing or malformed data is
reported as unavailable/limited discovery. Cpuset restrictions are reflected by
actual sched_getaffinity rather than assumed contiguous CPU numbers.

The default thread ceiling is the minimum of affinity CPU count, floored finite
quota (at least one worker) and OpenMP thread limit. Unknown affinity permits one
thread by default. This policy bounds logical concurrency, not physical cores or
exclusive execution capacity. `--allow-oversubscription` explicitly bypasses this
ceiling, emits a stderr warning and labels the JSON; it cannot bypass runtime
team limits. Dynamic teams are disabled during experiments and the previous
setting and runtime schedule are restored. Requested and observed teams are
recorded for every trial. The runtime maximum is a configuration value;
`omp_get_thread_limit` is a separate upper bound, not promised capacity.

Delta-stepping keeps its persistent team, dynamic edge-chunk scheduling, atomic
relaxation and bucket barriers. Its sole algorithm extension is an optional
call-owned team-size output pointer. Existing aggregate initializers and software
work metrics retain their behavior. No per-edge counters are enabled by scaling.
Synchronization makes published buckets and updates visible; barriers, serialized
merges and atomics can limit useful parallelism even on independent cores.

`parallel-kernels --affinity compact` binds each participating worker to an actual
CPU ID in the original available mask, checks the applied mask, and restores that
worker's original mask after each trial. Allocation, syscalls and restoration are
outside timing; failures appear in per-trial flags. Nothing requires root or
changes system settings. Unsupported platforms run unbound and report false.
The caller's mask and OpenMP configuration restoration have an in-process test.

Scaling does not install affinity hooks in the graph engine. Use externally
configured `OMP_PLACES` and `OMP_PROC_BIND` if desired; these strings are captured
but worker binding is not claimed verified. Scaling rejects `--affinity compact`
with a diagnostic; the dedicated kernels provide verified affinity experiments.
Library identity/version is null in portable JSON; this validation host linked
GNU `libgomp.so.1` (see validation observations), OpenMP specification 201511.

Phase 2 PMU scopes are unchanged. OpenMP commands return `unsupported_scope`
with null measurements when counters are requested. A caller-only counter is
never presented as an aggregate over worker execution.
