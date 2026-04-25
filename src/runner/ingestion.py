"""Stage 3: load and normalize inference records from disk (minimal slice).

Supported input contract (only one in this stage)
-------------------------------------------------
``input_contract_id`` must be exactly ``json_list_v1``:

* File format: JSON with a **top-level array**.
* Each element: a JSON object with:

  * ``item_id`` (string, non-empty after stripping leading/trailing whitespace)
  * ``response_text`` (string; may be empty — empty and whitespace-only strings are accepted)
  * ``benchmark_family`` (string, non-empty after stripping)

Optional keys (when present, strict types; omitted keys are not forwarded):

  * ``instruction_task_text`` (string or JSON null)
  * ``instruction_rubric`` (object / JSON null)

No other ``input_contract_id`` values are accepted until a future stage adds them.

Aggregation / filtering
-----------------------
* ``computation.aggregation_scope`` ``per_benchmark_family``: keep only rows whose
  ``benchmark_family`` equals ``computation.benchmark_family`` (compared after strip).
* ``computation.aggregation_scope`` ``aggregate_model_total``: keep all rows (model-total pool).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_INPUT_CONTRACT_ID = "json_list_v1"

AGG_PER_FAMILY = "per_benchmark_family"
AGG_MODEL_TOTAL = "aggregate_model_total"


class IngestionError(Exception):
    """Raised when records cannot be loaded or fail validation."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _resolve_records_path(cfg: dict[str, Any]) -> Path:
    """Resolve ``inputs.records_path`` using optional ``inputs.workspace_root``."""
    inputs = cfg["inputs"]
    records_path = Path(inputs["records_path"])
    if records_path.is_absolute():
        return records_path
    workspace = inputs.get("workspace_root")
    if workspace:
        return (Path(workspace) / records_path).resolve()
    return records_path.resolve()


def _normalize_record(raw: dict[str, Any], index: int) -> dict[str, Any]:
    for key in ("item_id", "response_text", "benchmark_family"):
        if key not in raw:
            raise IngestionError(f"record[{index}]: missing required field {key!r}.")

    if not isinstance(raw["item_id"], str) or raw["item_id"].strip() == "":
        raise IngestionError(f"record[{index}]: item_id must be a non-empty string.")
    if not isinstance(raw["response_text"], str):
        raise IngestionError(f"record[{index}]: response_text must be a string.")
    if not isinstance(raw["benchmark_family"], str) or raw["benchmark_family"].strip() == "":
        raise IngestionError(
            f"record[{index}]: benchmark_family must be a non-empty string."
        )

    out: dict[str, Any] = {
        "item_id": raw["item_id"].strip(),
        "response_text": raw["response_text"],
        "benchmark_family": raw["benchmark_family"].strip(),
    }

    if "instruction_task_text" in raw:
        v = raw["instruction_task_text"]
        if v is not None and not isinstance(v, str):
            raise IngestionError(
                f"record[{index}]: instruction_task_text must be a string or null, "
                f"not {type(v).__name__}."
            )
        out["instruction_task_text"] = v

    if "instruction_rubric" in raw:
        v = raw["instruction_rubric"]
        if v is not None and not isinstance(v, dict):
            raise IngestionError(
                f"record[{index}]: instruction_rubric must be an object or null, "
                f"not {type(v).__name__}."
            )
        out["instruction_rubric"] = dict(v) if isinstance(v, dict) else None

    return out


def _filter_rows(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    scope = cfg["computation"]["aggregation_scope"]
    if scope == AGG_MODEL_TOTAL:
        return list(rows)
    if scope == AGG_PER_FAMILY:
        target = cfg["computation"]["benchmark_family"].strip()
        return [r for r in rows if r["benchmark_family"] == target]
    raise IngestionError(
        f"Unsupported computation.aggregation_scope {scope!r}; "
        f"supported: {AGG_PER_FAMILY!r}, {AGG_MODEL_TOTAL!r}."
    )


def load_records(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Load records from disk per *cfg* (must already pass Stage 2 validation).

    Returns a list of dicts with required keys ``item_id``, ``response_text``,
    ``benchmark_family``, plus optional ``instruction_task_text`` and/or
    ``instruction_rubric`` when those keys appear in the source JSON.

    Raises:
        IngestionError: contract mismatch, missing file, parse errors, schema violations,
            aggregation_scope not supported, or row count vs ``panel_size`` mismatch.
    """
    contract = cfg["inputs"]["input_contract_id"]
    if contract != SUPPORTED_INPUT_CONTRACT_ID:
        raise IngestionError(
            f"Unsupported inputs.input_contract_id {contract!r}; "
            f"Stage 3 only supports {SUPPORTED_INPUT_CONTRACT_ID!r}."
        )

    path = _resolve_records_path(cfg)
    if not path.is_file():
        raise IngestionError(f"Input records file not found: {path}")

    try:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        raise IngestionError(f"Invalid JSON in records file {path}: {e}") from e

    if not isinstance(payload, list):
        raise IngestionError(
            "Records file must contain a JSON array at the top level; "
            f"got {type(payload).__name__}."
        )

    rows: list[dict[str, Any]] = []
    for i, item in enumerate(payload):
        if not isinstance(item, dict):
            raise IngestionError(
                f"record[{i}]: must be an object, not {type(item).__name__}."
            )
        rows.append(_normalize_record(item, i))

    filtered = _filter_rows(rows, cfg)
    expected = cfg["computation"]["panel_size"]
    if len(filtered) != expected:
        raise IngestionError(
            f"Record count after filtering ({len(filtered)}) does not match "
            f"computation.panel_size ({expected})."
        )

    return filtered
