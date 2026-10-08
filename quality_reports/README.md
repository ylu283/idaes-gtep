# Quality Reports Governance

This folder stores analysis deliverables for model debugging, benchmarking, and collaborator updates.

## Canonical Structure

- `reports/`
  - Finalized markdown reports (reference-quality writeups).
- `decks/`
  - Final presentation outputs (`.pptx`, optional `.pdf`).
- `decks/src/`
  - Slide/deck generation scripts.
- `decks/data/`
  - Deck input datasets (JSON/CSV) used by deck generators.
- `lab_logs/`
  - Chronological lab notes with experiment/process context.
- `session_logs/`
  - Short-lived process/debug logs; do not store final reports here.
- `archive/`
  - Superseded artifacts retained for traceability.

## Naming Convention

For all newly created files, use:

`YYYY-MM-DD_<topic>_<artifact>.<ext>`

Rules:
- Use lowercase snake_case for `<topic>` and `<artifact>`.
- Keep names stable and descriptive.
- Avoid suffixes like `final2`, `new`, `latest`.

Examples:
- `2026-03-05_prescient_vs_paper_model_comparison_report.md`
- `2026-03-05_curtailment_penalty_benchmark_deck.pptx`
- `2026-03-05_hydro_q1_lab_log.md`

## Lifecycle

- `draft`: working material under active edits.
- `reviewed`: technically checked for internal use.
- `final`: share-ready canonical artifact.
- `archived`: retained old versions moved to `archive/`.

## Maintenance Rules

1. Put finalized reports in `reports/`, never `session_logs/`.
2. Keep `session_logs/` for transient debugging notes only.
3. Update `INDEX.md` when adding a new report/deck/notebook-level summary.
4. Keep `PROJECT_MEMORY.md` lean by linking to reports instead of duplicating long narratives.
5. Keep repository noise low via `.gitignore` (for example `.DS_Store`, `~$*.pptx`).

## Lightweight Check

Run this before committing report-organization changes:

```bash
python quality_reports/check_structure.py
```

The checker is warning-only (non-blocking) and highlights non-canonical paths/names.
