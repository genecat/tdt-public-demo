"""Stage 7: minimal CSV and Markdown run summaries.

Writes ``summary.csv``, ``summary.md``, and ``rows.csv`` under ``outputs.output_dir`` (resolved with
``inputs.workspace_root`` when the path is relative, consistent with ingestion/diagnostics/rules).

Values are **serialized only**; nothing is recomputed from raw text here.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

# Per-item Phase 2 metrics (subset of ``trinity_core.compute_rows`` fields).
ROWS_CSV_FIELDS = [
    "item_id",
    "S",
    "semantic_repetition_score",
    "topic_drift_score",
    "specificity_vagueness_score",
    "structural_coherence_score",
    "internal_consistency_score",
    "instruction_alignment_score",
    "instruction_alignment_mode",
    "critical_slot_integrity_score",
    "critical_slot_integrity_mode",
    "information_density_score",
    "reasoning_progression_score",
    "constraint_stability_score",
    "combined_row_risk",
    "primary_weakness",
]


def _rows_csv_value(row: dict[str, Any], key: str) -> str:
    if key not in row or row[key] is None:
        return ""
    return str(row[key])


def resolve_output_dir(cfg: dict[str, Any]) -> Path:
    """Resolve ``outputs.output_dir``; create the directory if missing."""
    raw = Path(cfg["outputs"]["output_dir"])
    if raw.is_absolute():
        out = raw
    else:
        workspace = cfg["inputs"].get("workspace_root")
        if workspace:
            out = (Path(workspace) / raw).resolve()
        else:
            out = raw.resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_run_reports(
    cfg: dict[str, Any],
    *,
    computed_rows: list[dict[str, Any]],
    pool_aggregate: dict[str, Any],
    diagnostics: dict[str, Any],
    rule_result: dict[str, Any],
) -> dict[str, Path]:
    """Write ``summary.csv``, ``summary.md``, and ``rows.csv`` for one completed run.

    *pool_aggregate* is the dict returned by ``pool_pooled_S`` (``pooled_S``, ``n``); it is
    part of the pipeline contract but pooled scalars in the report come from *diagnostics*
    and are not recomputed here.

    Returns ``{"csv": path, "markdown": path, "rows_csv": path}``.
    """
    row_count = len(computed_rows)
    if "n" in pool_aggregate and int(pool_aggregate["n"]) != row_count:
        raise ValueError("pool_aggregate['n'] must match len(computed_rows).")

    out_dir = resolve_output_dir(cfg)
    csv_path = out_dir / "summary.csv"
    md_path = out_dir / "summary.md"

    run_id = cfg["run"]["run_id"]
    comp = cfg["computation"]

    csv_fields = [
        "run_id",
        "rule_set_id",
        "final_tag",
        "row_count",
        "pooled_S_live",
        "refined_sham_score",
        "legacy_sham_score",
        "D_refined_minus_legacy",
        "sham_comparison",
    ]
    row = {
        "run_id": run_id,
        "rule_set_id": rule_result["rule_set_id"],
        "final_tag": rule_result["final_tag"],
        "row_count": row_count,
        "pooled_S_live": diagnostics["pooled_S_live"],
        "refined_sham_score": diagnostics["refined_sham_score"],
        "legacy_sham_score": diagnostics["legacy_sham_score"],
        "D_refined_minus_legacy": diagnostics["D_refined_minus_legacy"],
        "sham_comparison": diagnostics["sham_comparison"],
    }

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerow(row)

    rows_path = out_dir / "rows.csv"
    with rows_path.open("w", encoding="utf-8", newline="") as f:
        rw = csv.DictWriter(f, fieldnames=ROWS_CSV_FIELDS)
        rw.writeheader()
        for crow in computed_rows:
            rw.writerow({k: _rows_csv_value(crow, k) for k in ROWS_CSV_FIELDS})

    md_lines = [
        "# TDT v1 run summary",
        "",
        "This report separates **measured quantities** produced by the audit pipeline from the **operational classification** assigned by the configured rule bundle.",
        "",
        "## Run identity",
        "",
        f"- **run_id**: `{run_id}`",
        f"- **model_id**: `{comp['model_id']}`",
        f"- **benchmark_family**: `{comp['benchmark_family']}`",
        f"- **panel_size**: `{comp['panel_size']}`",
        "",
        "## Measured values (core and diagnostics)",
        "",
        f"- **pooled_S_live**: `{diagnostics['pooled_S_live']}`",
        f"- **refined_sham_score**: `{diagnostics['refined_sham_score']}` (from precomputed sham file)",
        f"- **legacy_sham_score**: `{diagnostics['legacy_sham_score']}` (from precomputed sham file)",
        f"- **D_refined_minus_legacy**: `{diagnostics['D_refined_minus_legacy']}`",
        f"- **sham_comparison** (diagnostic enum): `{diagnostics['sham_comparison']}`",
        f"- **row_count**: `{row_count}`",
        "",
        "## Classification (rule bundle)",
        "",
        f"- **rule_set_id**: `{rule_result['rule_set_id']}`",
        f"- **final_tag**: `{rule_result['final_tag']}`",
        "",
        f"*Reason:* {rule_result['reason']}",
        "",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return {"csv": csv_path, "markdown": md_path, "rows_csv": rows_path}
