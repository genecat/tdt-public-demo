"""Load and structurally validate TDT v1 run configuration JSON (Stage 2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = ("run", "inputs", "computation", "diagnostics", "rules", "outputs")


class ConfigValidationError(Exception):
    """Raised when run configuration fails structural validation."""

    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("\n".join(messages))


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_panel_size(value: Any) -> bool:
    # Reject bool (subclass of int in Python).
    return type(value) is int and not isinstance(value, bool)


def _collect_validation_errors(data: Any) -> list[str]:
    errors: list[str] = []

    if not isinstance(data, dict):
        errors.append("Top-level JSON value must be an object.")
        return errors

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"Missing top-level group: {key!r}.")
        elif not isinstance(data[key], dict):
            errors.append(f"Top-level group {key!r} must be an object.")

    if errors:
        return errors

    run = data["run"]
    inputs = data["inputs"]
    computation = data["computation"]
    diagnostics = data["diagnostics"]
    rules = data["rules"]
    outputs = data["outputs"]

    if not _is_nonempty_string(run.get("run_id")):
        errors.append("run.run_id is required and must be a non-empty string.")
    if not _is_nonempty_string(run.get("run_schema_version")):
        errors.append("run.run_schema_version is required and must be a non-empty string.")

    if not _is_nonempty_string(inputs.get("records_path")):
        errors.append("inputs.records_path is required and must be a non-empty string.")
    if not _is_nonempty_string(inputs.get("input_contract_id")):
        errors.append("inputs.input_contract_id is required and must be a non-empty string.")

    if not _is_nonempty_string(computation.get("model_id")):
        errors.append("computation.model_id is required and must be a non-empty string.")
    if not _is_nonempty_string(computation.get("benchmark_family")):
        errors.append("computation.benchmark_family is required and must be a non-empty string.")
    if not _is_panel_size(computation.get("panel_size")):
        errors.append("computation.panel_size is required and must be an integer.")
    if not _is_nonempty_string(computation.get("aggregation_scope")):
        errors.append("computation.aggregation_scope is required and must be a non-empty string.")
    if not _is_nonempty_string(computation.get("pipeline_lock_id")):
        errors.append("computation.pipeline_lock_id is required and must be a non-empty string.")

    if not _is_nonempty_string(diagnostics.get("sham_mode")):
        errors.append("diagnostics.sham_mode is required and must be a non-empty string.")
    if not _is_nonempty_string(diagnostics.get("sham_baseline")):
        errors.append("diagnostics.sham_baseline is required and must be a non-empty string.")

    sham_base = diagnostics.get("sham_baseline")
    if isinstance(sham_base, str) and sham_base == "use_precomputed_file":
        if not _is_nonempty_string(diagnostics.get("sham_baseline_path")):
            errors.append(
                "diagnostics.sham_baseline_path is required and must be a non-empty string "
                'when diagnostics.sham_baseline is "use_precomputed_file".'
            )

    if not _is_nonempty_string(rules.get("rule_set_id")):
        errors.append("rules.rule_set_id is required and must be a non-empty string.")
    if not _is_nonempty_string(rules.get("rules_path")):
        errors.append("rules.rules_path is required and must be a non-empty string.")

    if not _is_nonempty_string(outputs.get("output_dir")):
        errors.append("outputs.output_dir is required and must be a non-empty string.")

    return errors


def load_and_validate_run_config(config_path: str | Path) -> dict[str, Any]:
    """Load JSON from *config_path* and return the object if structurally valid.

    Raises:
        FileNotFoundError: If *config_path* is not a file.
        json.JSONDecodeError: If the file is not valid JSON.
        ConfigValidationError: If required groups or fields are missing or invalid.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    errors = _collect_validation_errors(data)
    if errors:
        raise ConfigValidationError(errors)

    return data
