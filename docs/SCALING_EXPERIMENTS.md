# Reproducible scaling and overhead experiments

Build Release for performance exploration; use Debug/sanitizers for correctness.
The existing generator, manifests, CSR fingerprint and steady-clock timing are
reused. Keep the generator manifest with exported results: the loaded-CSR FNV-1a
identity is not a cryptographic file digest.

## Professor's live demonstration

```sh
cmake -S . -B build/phase4-release -DCMAKE_BUILD_TYPE=Release -DARCHGRAPH_WARNINGS_AS_ERRORS=ON
cmake --build build/phase4-release --parallel 2
build/phase4-release/archgraph --cpu
python3 -B benchmarks/python/generate.py generate --spec benchmarks/configs/chain-v1.json --output /tmp/phase4-chain
python3 -B benchmarks/python/generate.py verify --manifest /tmp/phase4-chain/manifest.json
build/phase4-release/archgraph scaling --input /tmp/phase4-chain/graph.txt \
  --source 0 --algorithm delta-stepping --delta 16 --threads 1,2 \
  --repetitions 15 --warmups 2 --seed 42 --csv /tmp/scaling.csv > /tmp/scaling.json
python3 -m json.tool /tmp/scaling.json
build/phase4-release/archgraph parallel-kernels --threads 1,2 --size 65536 \
  --chunks 1,64 --workload irregular --repetitions 15 --warmups 2 \
  --seed 42 --affinity compact --csv /tmp/kernels.csv > /tmp/kernels.json
```

First inspect safe_thread_limit. Use `--threads 1` if only one CPU-time slot is
available. Thread lists accept unique positive decimal integers up to 4096; a
one-thread baseline is inserted if omitted. Default threads are 1,2 when safe,
otherwise 1. Lists are limited to 64 configurations and schedules to one million
trials. Larger thread counts such as 1,2,4,8 are supported only within the discovered
ceiling unless explicitly overridden. `--allow-oversubscription` warns and labels
results, and does not make them valid controlled scaling evidence.

Show `verified`, the complete vector comparison against Dijkstra, each trial's
requested/observed team, topology and counter status before showing timings.
Then compare medians and dispersion. Dijkstra is a correctness oracle here;
S(p) uses the median of **one-thread delta-stepping**, not Dijkstra. A chain can
have very little exploitable graph parallelism. A fixed generator grid workload
may expose different work, but changes to topology/weights/delta are new experiments.

## Trial scheduler and timing

One complete block runs every thread configuration once. Kernel blocks include
every strategy, chunk and thread combination. SplitMix64 plus rejection-sampled
Fisher–Yates shuffles each block; seeds reproduce order independently of standard
library RNG implementations. `--repetitions` is measured blocks (1–10000),
`--warmups` is warmup blocks (0–10000). Warmup blocks precede measured blocks,
use the same workload and are separately retained in `trials`; summaries exclude
them. Configuration order is randomized, not a random graph or changing query.
There is no cache flush or cold-cache guarantee.

Scaling loads the graph and computes reference Dijkstra once before all trials.
Each timed region is exactly a public uninstrumented delta-stepping call,
including its own allocation, team startup and synchronization. Full source and
distance comparison, checksum consumption, sample storage and serialization are
outside timing. Optional team-size output uses a single post-team store and
never enables per-edge instrumentation. Individual positive nanosecond durations
are retained. Nonpositive/nonfinite timings fail rather than generating invalid
ratios. Summaries report median (midpoint for even counts), min, max and unscaled
median absolute deviation (MAD). These are descriptive statistics, not confidence
intervals or significance tests.

Kernel data and reference checksums are allocated/computed before trials. A timed
kernel includes worksharing, synchronization and reduction, but excludes team
creation, affinity changes and validation. Thus its timings have different
boundaries from scaling. Static/dynamic strategies apply identical unsigned
transformations to every data element and sum modulo 2^64. Data values are
`index XOR seed`; uniform transforms use 32 rounds, irregular transforms use
`1 + 8*((value/256)%32)` rounds. These deterministic clustered costs make load
imbalance plausible without guaranteeing any scheduling outcome. Checksums from
every strategy must equal the sequential reference. The outputs are consumed,
so workload elimination cannot discard the computation.

The same configurations compare static and dynamic scheduling with reduction,
and static scheduling with per-item atomic or named critical updates. Chunk size
is iterations, bounded to 1–4096. Reduction accumulates locally then combines;
atomics/critical sections synchronize every item and can serialize execution.
Dynamic scheduling can improve irregular balance but adds dispatch overhead;
small chunks trade balance against more dispatches. Static chunks can be cheaper
on uniform work. The experiments measure combined costs, not isolated primitive
latencies or peak throughput. The production graph algorithm is not rescheduled.

## JSON and CSV contract

`docs/multicore-v1.schema.json` specifies the versioned envelope and trial/summary
records (`schema: archgraph-multicore-experiments`, `schema_version: 1`). CLI tests
validate both commands against its required fields/types/ranges without adding
runtime dependencies. Topology, CPU/build metadata, runtime environment, graph
path/identity/source/delta, workload/size, seed, warmup count, affinity flags,
raw trials and summaries are emitted. Build revision/dirty/flags are captured at
CMake configure time; reconfigure after edits. Quota/runtime version/physical
fields and PMU readings use explicit null/unavailable values as appropriate.
`source`, `delta`, and graph counts are inapplicable defaults for kernels; graph
path/identity are null. Thread counts are in trials and summaries.

Speedup and efficiency use matching strategy/chunk baselines for kernels; they
never compare different synchronization implementations as one algorithm.
If any measured requested team differs from observed in the matching baseline
or configuration, those speedup/efficiency values are null. Amdahl predictions
remain explicitly theoretical. Affinity applied/restored flags describe each
trial; false applied means no binding was requested or it could not be verified.
The affinity request and platform limitations disambiguate these cases.

`--csv path` exports every warmup and measured trial in JSON order, with a header,
schema version, block, warmup flag, strategy, chunk, requested/observed teams,
wall_ns, checksum and affinity flags. CSV is a raw-trial companion: preserve JSON
for metadata and summaries. Write/open failure is an error. Large uint64 checksums
require integer-preserving consumers, especially JavaScript.

Shared hosts, SMT contention, CPU quota throttling, migration, page faults,
frequency changes and background work can dominate differences. Randomization
reduces order confounding but does not isolate the system. No significance,
exclusive-core ownership, fixed-frequency, NUMA, or universal speedup claim is
made. Phase 3's fixed-order/cache-state limitations remain documented there;
this scheduler improves order balance without retroactively changing those results.
