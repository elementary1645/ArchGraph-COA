# Final academic delivery index

ArchGraph-COA is a fifth-semester Computer Organization and Architecture teaching
project with a verified C++17/OpenMP engine and a separate local analytics dashboard.
Phase 6 consolidates the existing implementation and evidence without rewriting
working algorithms. No institutional identity, approval or signature is invented.

## Submission and examination materials

| Deliverable | Contents |
| --- | --- |
| [PROJECT_REPORT.md](PROJECT_REPORT.md) | Complete 19-section academic report, accurate references, equations, authentic results and explicit limitations |
| [ARCHITECTURE_DIAGRAMS.md](ARCHITECTURE_DIAGRAMS.md) | Seven explained Mermaid flowcharts; syntax checked |
| [PRESENTATION.md](PRESENTATION.md) | 15-slide outline and full speaker notes |
| [Editable PRESENTATION.pptx](PRESENTATION.pptx) | 15 slides, notes and native editable charts; structural checks, not renderer QA |
| [LIVE_DEMO.md](LIVE_DEMO.md) | Exact 5–7-minute workflow, output structures and PMU-independent archive fallback |
| [VIVA_QA.md](VIVA_QA.md) | 60 numbered questions and clear oral-exam answers |
| [REPRODUCIBILITY.md](REPRODUCIBILITY.md) | Tools, fresh builds, tests, inputs, captures, dashboard and chart/slide regeneration |
| [FINAL_EVALUATION.md](FINAL_EVALUATION.md) | Evidence-based assessment against ten criteria and prioritized next actions |
| [FINAL_VALIDATION.md](FINAL_VALIDATION.md) | Exact executed commands, final counts, skips, sanitizer/startup/integrity outcomes and unverified areas |
| [LICENSING.md](LICENSING.md) | Preserved attribution and unresolved source-license/redistribution condition |

## Numerical evidence and figures

- [Complete derived results table](results/RESULTS.md), [machine-readable results/sources](results/RESULTS.json).
- [Representation accounting SVG](figures/archive-memory.svg) / [PNG](figures/archive-memory.png).
- [Locality medians/ranges SVG](figures/archive-locality.svg) / [PNG](figures/archive-locality.png).
- [Working-set observations SVG](figures/archive-cache-study.svg) / [PNG](figures/archive-cache-study.png).
- [Same-algorithm scaling and theoretical curve SVG](figures/archive-scaling.svg) / [PNG](figures/archive-scaling.png).
- [Figure source records](figures/sources.json), [13-receipt/import/CSV audit](../validation/phase6/evidence-audit.json).
- Complete delivery file inventory and SHA-256 values are in `docs/validation/phase6/DELIVERY_MANIFEST.json` (self-hash excluded).
- [Final validation evidence directory](../validation/phase6/): build/test logs, exact fresh demo commands/results, package/dependency checks and readiness results.

The four scientific plots derive from archived actual values. No historical
receipt is overwritten, no unsupported PMU values are fabricated and no samples
from different machines/builds are pooled. The Amdahl curve is explicitly assumed.
The eight-vertex memory example is instructional, not a large-graph performance study.

## Reusable scripts

| Script | Purpose |
| --- | --- |
| [verify_evidence.py](scripts/verify_evidence.py) | Read-only receipt hashes/schemas, 306 CSV/JSON row comparisons and historical import audit |
| [run_demo.py](scripts/run_demo.py) | Capture/verify fresh CLI outputs in a new directory, adapting the safe thread count |
| [results.py](scripts/results.py) | Derive non-pooled summaries and source metadata from archived receipts |
| [charts.py](scripts/charts.py) | Export four SVG/PNG figure pairs from authentic data; optional Matplotlib |
| [presentation.py](scripts/presentation.py) | Generate/reopen-check editable notes-bearing PPTX; optional python-pptx |
| [check_mermaid.mjs](scripts/check_mermaid.mjs) | Parse the seven diagrams using isolated Mermaid/jsdom |
| [check_delivery.py](scripts/check_delivery.py) | Check material counts, local link targets, source-derived results, PPTX structure and no-overwrite behavior |

The standard-library `scripts/package_manifest.py --check` verifies the complete final file inventory.

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) before executing. Scripts refuse to
replace existing capture/authoring targets. Dependencies for artifact generation
are isolated in [requirements-academic.txt](../../requirements-academic.txt);
the core and dashboard remain separately installable.

## Status and caveats

All requested material is delivered for technical academic review. The report
records actual verification rather than certifying hardware performance, universal
correctness or institutional acceptance. Manual browser/PowerPoint/projector QA
remains unperformed because those tools were unavailable. Licensing clearance is
unresolved; do not present this as an unrestricted licensed distribution.

For the software, begin with the [root README](../../README.md) and
[dashboard guide](../DASHBOARD_GUIDE.md). Phase-specific validation remains unchanged
as historical evidence and is linked from the report.
