"""Stage 5: minimal diagnostics using precomputed sham scores only.

Precomputed sham file contract (``use_precomputed_file``)
-----------------------------------------------------------
Path: ``diagnostics.sham_baseline_path`` (resolved with ``inputs.workspace_root`` like records).

The file must be a single JSON **object** with at minimum:

* ``refined_sham_score`` (number): magnitude-aware sham-side score from archived lineage semantics.
* ``legacy_sham_score`` (number): label-only sham-side score.

Optional:

* `sham_comparison` (string): when present in the precomputed JSON and loaded as a string, the current MWP diagnostic layer uses it verbatim; this slice does not validate values against a fixed set such as `"beat"`, `"tie"`, or `"fail"`. If omitted, a placeholder enum is derived from `refined_sham_score` vs `legacy_sham_score` only.
* Any other metadata keys are ignored.

This slice does **not** load the full archived sham generator; it only merges live ``pooled_S_live``
(from Trinity Core) with scores read from this file. Repeat-stability (``range_D``) is not computed.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

STAGE5_SHAM_BASELINE = "use_precomputed_file"


class DiagnosticError(Exception):
    """Raised when diagnostics cannot run or inputs are invalid."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _resolve_sham_baseline_path(cfg: dict[str, Any]) -> Path:
    path = Path(cfg["diagnostics"]["sham_baseline_path"])
    if path.is_absolute():
        return path
    workspace = cfg["inputs"].get("workspace_root")
    if workspace:
        return (Path(workspace) / path).resolve()
    return path.resolve()


def _as_number(label: str, value: Any) -> float:
    if isinstance(value, bool):
        raise DiagnosticError(f"Precomputed sham field {label} must be numeric (got bool).")
    if isinstance(value, (int, float)):
        return float(value)
    raise DiagnosticError(f"Precomputed sham field {label} must be numeric.")


def _derive_sham_comparison(refined: float, legacy: float) -> str:
    if refined > legacy:
        return "beat"
    if refined < legacy:
        return "fail"
    return "tie"


def run_diagnostics(
    cfg: dict[str, Any],
    *,
    pooled_S_live: float,
    computed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build diagnostic output from live aggregates and precomputed sham JSON.

    *computed_rows* is accepted for forward compatibility; this minimal slice does not
    require it for calculations.
    """
    del computed_rows  # reserved for future diagnostics; explicitly unused in Stage 5

    diag = cfg["diagnostics"]
    if diag.get("sham_baseline") != STAGE5_SHAM_BASELINE:
        raise DiagnosticError(
            f"Stage 5 only supports diagnostics.sham_baseline == {STAGE5_SHAM_BASELINE!r}."
        )

    sham_path = _resolve_sham_baseline_path(cfg)
    if not sham_path.is_file():
        raise DiagnosticError(f"Precomputed sham file not found: {sham_path}")

    try:
        with sham_path.open(encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        raise DiagnosticError(f"Invalid JSON in sham file {sham_path}: {e}") from e

    if not isinstance(payload, dict):
        raise DiagnosticError("Precomputed sham file must contain a JSON object at the top level.")

    if "refined_sham_score" not in payload:
        raise DiagnosticError("Precomputed sham file missing required field 'refined_sham_score'.")
    if "legacy_sham_score" not in payload:
        raise DiagnosticError("Precomputed sham file missing required field 'legacy_sham_score'.")

    refined = _as_number("refined_sham_score", payload["refined_sham_score"])
    legacy = _as_number("legacy_sham_score", payload["legacy_sham_score"])
    for name, v in (("refined_sham_score", refined), ("legacy_sham_score", legacy)):
        if math.isnan(v) or math.isinf(v):
            raise DiagnosticError(f"Precomputed sham field {name} must be finite.")

    d_rl = refined - legacy

    if "sham_comparison" in payload and payload["sham_comparison"] is not None:
        sham_cmp = payload["sham_comparison"]
        if not isinstance(sham_cmp, str):
            raise DiagnosticError("Precomputed sham field 'sham_comparison' must be a string if present.")
        comparison = sham_cmp
    else:
        comparison = _derive_sham_comparison(refined, legacy)

    return {
        "pooled_S_live": float(pooled_S_live),
        "refined_sham_score": refined,
        "legacy_sham_score": legacy,
        "D_refined_minus_legacy": d_rl,
        "sham_comparison": comparison,
        "range_D": None,
        "repeat_stability_computed": False,
    }
