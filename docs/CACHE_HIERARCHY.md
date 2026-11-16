# Cache hierarchy

A CPU executes instructions faster than many main-memory accesses can complete.
Caches retain copies of recently used memory in smaller storage nearer the core.
L1 is usually nearest/smallest; L2 and, where present, L3 provide progressively
larger capacity. Exact organization, sizes and sharing vary by processor. A cache
line is a block transferred and tracked together: accessing neighboring bytes can
benefit from a line already brought in. A hit finds data in the relevant cache;
a miss requires another level or memory. Writes, coherence and replacement policy
also matter; these Phase 3 traversal kernels perform data reads only.

## Observing this machine

Phase 3 reads Linux cache metadata from the current logical CPU's
`/sys/devices/system/cpu/cpuN/cache/index*` directories. It records level, type,
capacity, coherency line size, sharing CPU list and exact source path, alongside
Phase 1/2 CPU/build metadata and the platform diagnostic. The
[kernel sysfs ABI](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-devices-system-cpu)
defines these files. Fields that cannot be read/parsed remain null; metadata status
is `available`, `partial` or `unavailable`. No hardcoded universal cache sizes or
line size are substituted. Sharing lists are preserved as reported and may include
CPUs outside this process's affinity. They do not promise private/exclusive capacity.

Discovery is a snapshot, not pinning. Migration, shared-core activity and virtual
hardware can make it incomplete or unrepresentative. `--cache-root DIRECTORY` can
select another sysfs-style cache directory, including fixture data for reproducible
metadata tests; its source path is always recorded.

## Working-set study

```sh
build/phase3-release/archgraph cache-study --runs 3 --hardware-counters
build/phase3-release/archgraph cache-study --sizes 4096,65536,1048576 \
  --runs 3 --seed 1
```

For usable Data/Unified entries, automatic plans target data-array sizes of 0.5x,
1x and 2x each reported capacity, rounded down to eight bytes, sorted and deduplicated.
Instruction-only entries are reported but do not size a data-cache experiment.
`--max-size` defaults to 64 MiB and is configurable up to 256 MiB. This bounds each
data array, not total allocation. Targets above the bound are counted in
`omitted_capacity_targets`; such a plan does **not** claim to span those capacities.

When no usable targets fit or discovery fails, explicitly labeled configurable
fallback data sizes are used. They are not guessed cache capacities. `--sizes`
provides an explicit aligned byte list regardless of metadata; `plan_mode` records
whether sizes are discovered, explicit or fallback. Default reads per trial equal
the largest planned array's element count. The same read count is used at each size
and must cover the largest array at least once; override with `--accesses` when
needed. Every array uses deterministic random permutation cycles with recorded seed,
individual timings, median, checksum and footprint information.

The index sequence adds four bytes per active element to the eight-byte data array;
its storage also consumes cache and translation resources. Thus a data-array size
of one reported capacity does not mean the complete working set fits that cache.
Other live graph/program/runtime data consume resources too. Warming and repeated
cycles offer reuse opportunities but never guarantee cache residency.

## Hardware evidence and limits

The Phase 2 RAII backend now optionally selects `PERF_TYPE_HW_CACHE` read-access/
read-miss pairs for L1 data cache, last-level cache and data TLB. The encoding is
`cache_id | (READ << 8) | (ACCESS_or_MISS << 16)`, as specified by
[`perf_event_open`](https://www.man7.org/linux/man-pages/man2/perf_event_open.2.html).
The last-level event is named `ll_*`, not assumed universally to be L3. DTLB events
concern address translation, not a cache-level data-miss breakdown. There is no
portable L2-specific counter or invented L1/L2/L3 decomposition of generic events.
CPU mappings/support vary. Each pair keeps operands grouped, with the same
multiplexing scaling, quality gate, per-event errors and null semantics as Phase 2.
Existing generic profiling commands retain their six original events and schema.

Phase 3 experiments are single-threaded calling-thread user-space measurements,
with no inheritance, kernel activity or worker aggregation. Counter windows include
clock/control overhead; a scaled multiplexed value is an estimate, not a direct
full-window reading. Diagnostics distinguish independent opens from grouped readings.
Unavailable/denied/unscheduled metrics remain null while verified wall timing runs.
No root access or kernel-security changes are needed or performed.

A timing increase can reflect capacity pressure, translation, prefetching, bandwidth,
frequency, scheduling or other effects. Timing alone never proves a particular
cache-level transition. To demonstrate to a professor, show discovered entries,
planned sizes, sequence/data footprints and explicit counter status before looking
at medians. Phase 3's local validation records actual permission denial; mock tests
do not establish real PMU fidelity or measured cache misses.
