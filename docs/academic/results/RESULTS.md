# Derived archived results

Generated from the 13 checksum-verified catalog receipts; nanoseconds are rounded only for table display.
These are descriptive summaries, not a new benchmark or significance analysis.

| Source | Configuration | Threads | Chunk | Active bytes | n | Median ns | Min ns | Max ns | MAD ns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| layouts.json | csr Dijkstra | N/A | N/A | N/A | 5 | 241 | 230 | 471 | 11 |
| layouts.json | adjacency Dijkstra | N/A | N/A | N/A | 5 | 170 | 160 | 241 | 10 |
| locality-sequential.json | sequential · set 1 | N/A | N/A | 1048576 | 5 | 81673 | 81312 | 114734 | 361 |
| locality-strided.json | strided · set 1 | N/A | N/A | 1048576 | 5 | 279482 | 273471 | 307746 | 6011 |
| locality-random.json | random · set 1 | N/A | N/A | 1048576 | 5 | 265837 | 156162 | 277829 | 11992 |
| locality-temporal.json | temporal · set 1 | N/A | N/A | 4096 | 5 | 82354 | 82344 | 82464 | 10 |
| cache-study.json | random · set 1 | N/A | N/A | 4096 | 5 | 82464 | 82374 | 128721 | 90 |
| cache-study.json | random · set 2 | N/A | N/A | 32768 | 5 | 81502 | 81443 | 81522 | 10 |
| cache-study.json | random · set 3 | N/A | N/A | 262144 | 5 | 93054 | 91491 | 122760 | 1563 |
| cache-study.json | random · set 4 | N/A | N/A | 1048576 | 5 | 162814 | 158707 | 258643 | 2325 |
| scaling.json | delta-stepping | 2 | 0 | N/A | 15 | 2690738 | 2425492 | 10924383 | 265246 |
| scaling.json | delta-stepping | 1 | 0 | N/A | 15 | 3512313 | 3448333 | 14749020 | 57297 |
| kernels.json | dynamic-reduction | 2 | 1 | N/A | 15 | 8076863 | 8010396 | 14059742 | 65531 |
| kernels.json | static-reduction | 2 | 1 | N/A | 15 | 8178422 | 8014215 | 21357067 | 164207 |
| kernels.json | static-critical | 2 | 1 | N/A | 15 | 8308698 | 8273710 | 20198302 | 31220 |
| kernels.json | static-atomic | 2 | 64 | N/A | 15 | 7701441 | 7625098 | 40788257 | 65813 |
| kernels.json | static-atomic | 1 | 1 | N/A | 15 | 14701420 | 13901937 | 23022419 | 49353 |
| kernels.json | static-atomic | 1 | 64 | N/A | 15 | 14051287 | 13873795 | 23884611 | 177492 |
| kernels.json | static-reduction | 1 | 64 | N/A | 15 | 14584793 | 13614089 | 19289114 | 188301 |
| kernels.json | static-reduction | 1 | 1 | N/A | 15 | 14588540 | 13593801 | 28295963 | 657569 |
| kernels.json | static-critical | 2 | 64 | N/A | 15 | 7980184 | 7952810 | 22166570 | 18582 |
| kernels.json | static-atomic | 2 | 1 | N/A | 15 | 7994035 | 7937843 | 18688073 | 51384 |
| kernels.json | static-critical | 1 | 1 | N/A | 15 | 15032349 | 14200926 | 27096602 | 774317 |
| kernels.json | static-reduction | 2 | 64 | N/A | 15 | 7858775 | 7635538 | 18086847 | 211175 |
| kernels.json | dynamic-reduction | 2 | 64 | N/A | 15 | 7762004 | 7619691 | 23019835 | 112884 |
| kernels.json | dynamic-reduction | 1 | 1 | N/A | 15 | 15183542 | 14206185 | 23639642 | 176770 |
| kernels.json | static-critical | 1 | 64 | N/A | 15 | 14250388 | 14197690 | 17566906 | 52698 |
| kernels.json | dynamic-reduction | 1 | 64 | N/A | 15 | 14834149 | 13621213 | 41464581 | 1200113 |
| sequential-smoke.json | dijkstra | 0 | N/A | N/A | 10 | 241 | 220 | 761 | 15 |
| parallel-smoke.json | delta-stepping | 2 | N/A | N/A | 10 | 57095 | 56474 | 126999 | 586 |

Source paths, hashes, CPU/build metadata, original memory accounting and independently recomputed scaling ratios are in RESULTS.json.
Phase 2 Dijkstra and delta-stepping entries are different algorithms, not a same-algorithm thread-speedup comparison.
No timing table rows from different source files were pooled.
