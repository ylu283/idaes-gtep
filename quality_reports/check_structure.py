"""Lightweight checker for quality_reports structure and naming hygiene.

This script is intentionally non-blocking: it prints warnings and exits 0.
Use it before commits that add/update quality report artifacts.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CANON_DIRS = {
    "reports",
    "decks",
    "lab_logs",
    "session_logs",
    "archive",
    "plans",  # temporary legacy folder during phased migration
}
NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9_]+_[a-z0-9_]+\.[A-Za-z0-9]+$")
LEGACY_NAME_ALLOWLIST = {
    "decks/2026-02-26_IDAES_Update_Kay.pptx",
    "decks/2026-03-03_Benchmarking_Update_PCM_vs_Paper.pptx",
    "decks/2026-03-03_Benchmarking_Update_PCM_vs_Paper_archive.pptx",
    "decks/src/2026-02-26_presentation-outline.md",
    "lab_logs/lab_log_2026-03-01.md",
    "reports/curtailment_penalty_experiment_setup_2026-02-28.md",
    "reports/model_comparison_prescient_vs_paper_uc_2026-02-28.md",
}


def main() -> None:
    warnings: list[str] = []

    for required in ["README.md", "INDEX.md", "reports", "decks", "lab_logs", "session_logs"]:
        if not (ROOT / required).exists():
            warnings.append(f"missing required path: {required}")

    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if path.is_dir():
            continue

        # skip hidden/system/temp/cache files
        if rel.name.startswith(".") or rel.name.startswith("~$") or "__pycache__" in rel.parts:
            continue

        rel_str = rel.as_posix()
        top = rel.parts[0]
        if top not in CANON_DIRS and rel.name not in {"README.md", "INDEX.md", "check_structure.py"}:
            warnings.append(f"non-canonical top-level location: {rel}")

        # naming check for report-like artifacts
        if top in {"reports", "decks", "lab_logs", "archive"} and rel.suffix in {".md", ".pptx", ".pdf"}:
            if rel_str not in LEGACY_NAME_ALLOWLIST and not NAME_RE.match(rel.name):
                warnings.append(f"non-canonical filename pattern: {rel}")

        if top == "session_logs" and "lab_log" in rel.name:
            warnings.append(f"lab log should be in lab_logs/: {rel}")

    if warnings:
        print("Quality report structure warnings:")
        for w in warnings:
            print(f"- {w}")
    else:
        print("Quality report structure check passed: no warnings.")


if __name__ == "__main__":
    main()
