# Import provenance

Source: https://github.com/elementary1645/Dynagraph-HPC

Exact source commit: `1b5eaea38e4fdfb203ea4214f79f05c8e909c7e9`.
Source inspected read-only in `/tmp/Dynagraph-HPC` on 2026-11-16; `/tmp` was used
for the reference checkout because the workspace parent is outside writable roots.
No upstream file or branch was modified or pushed. The destination's Git history
was preserved. This is a selective source import, with no submodule or runtime
reference to that checkout.

## Attribution and licensing

The graph engine, metadata, deterministic generation and retained tests originate
from the DynaGraph-HPC contributors at the source URL and commit above. Preserve
this attribution and any notices within the files. No tracked LICENSE, COPYING or
NOTICE file was present in the inspected source tree. No third-party code or
license was added, and no license grant is invented here. This import records the
user-requested reuse; downstream redistribution requires resolving the upstream
licensing status. Dependencies are the C++/Python standard libraries and the
compiler's OpenMP/Threads runtime, supplied by the build environment.

[import-manifest.json](import-manifest.json) lists every copied upstream file,
its original SHA-256, destination and unchanged/adapted status. It separately
hashes build/workflow/timing files consulted for adaptations. The namespace and
upstream generator schema names remain stable to preserve compatibility.

## Reuse inventory (decided before importing)

| Module | Decision and reason |
| --- | --- |
| CSR, validation, edge-list loader | Import unchanged; core representation and strict input validation |
| Dijkstra | Import unchanged; sequential baseline with independent oracle tests |
| OpenMP delta-stepping | Import unchanged; validated atomic/bucket algorithm |
| Workload/resources instrumentation | Import unchanged; required symbols referenced by delta-stepping, optional at runtime |
| Project metadata | Retain implementation; update stale header comment |
| Core tests and SSSP CLI integration | Retain unchanged, including seeded Bellman–Ford comparisons and boundary cases |
| Deterministic Python generators/artifact verification | Retain unchanged with chain specification and 23 Python test methods |
| CLI | Adapt identity; add metadata and static benchmark commands |
| CMake and CI | Adapt core target definitions/warning policy; replace research validation dependencies with explicit retained tests |
| Timing | Adapt monotonic clock and verification-outside-brackets approach to static queries in src/benchmark/static.cpp |

## Exclusions and dependency check

Excluded incremental repair and adaptive engines, their tests, update replay,
campaign orchestration, evidence archives, statistical/publication tooling,
TSan experiments, historical documents/results, research plans, large data,
generated files and binaries. Source `.git`, source `AGENTS.md` phase gates and
research-specific presets were not imported. Historical results are not ArchGraph
measurements. Generated graph bundles and local build trees are ignored.

The source timing module depends on adaptive replay/update types. Importing it
unchanged would retain the research workflow solely to time static queries;
instead the small clock boundary was adapted without changing graph algorithms.
The pure generator retains traces and verification for format compatibility only.
Combined system/concurrency/failure tests depend on excluded adaptive/incremental
engines and were not imported or reported as passing. The standalone core tests
remain intact. All retained production translation units link in the standalone
build, proving there is no unresolved dependency on excluded engines.
