# Speedup, efficiency and Amdahl's Law

For a fixed graph, source, delta, build and algorithm, measured speedup is
`S(p) = T(1)/T(p)` and efficiency is `E(p) = S(p)/p`. This phase uses median
one-thread OpenMP delta-stepping for T(1). Sequential Dijkstra performs different
work and is only the correctness oracle; its runtime cannot establish
same-algorithm parallel speedup.

The CLI's `--parallel-fraction f` defaults to 0.95 and must be finite in [0,1].
It generates the theoretical curve `1 / ((1-f) + f/p)`. With f=0.95 and p=2,
the theoretical speedup is about 1.905 and efficiency about 0.952. For f=0 the
speedup is 1; for f=1 it is p. At arbitrarily many threads a nonzero serial
fraction limits speedup to `1/(1-f)`.

The fraction is assumed, not fitted or measured. Amdahl assumes fixed work and
ideal parallel execution with the specified serial portion. It omits extra
thread startup, bucket synchronization, atomic contention, dispatch costs,
cache effects and shared-host interference. A graph's frontier width and degree
skew also constrain available work. SMT threads share core resources, and extra
workers can cost more than the useful work they divide. More threads therefore
need not reduce runtime; speedup and efficiency can be below one. Superlinear
observations require investigation of cache/work changes and noise, not an
automatic architectural conclusion.

Arithmetic helpers return unavailable for zero, negative or nonfinite timings,
invalid fractions and nonpositive p. Summarization rejects invalid timing input.
Speedup/efficiency are null if observed teams differ from requests, avoiding a
false p-axis interpretation. Ratios of medians describe these samples and do
not provide a statistical significance test or a causal estimate.
