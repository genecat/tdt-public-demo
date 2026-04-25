"""Stage 6: minimal rule-bundle-driven evaluation (sham comparison → operational tag).

Rules bundle JSON contract (Stage 6)
------------------------------------
The file at ``rules.rules_path`` (resolved with ``inputs.workspace_root`` when relative)
must be a single JSON **object** with:

* ``rule_set_id`` (string, non-empty): must equal ``rules.rule_set_id`` in the run config.
* ``tag_when_sham_comparison`` (object): maps sham outcomes to operational tags:

  * ``\"beat\"`` → tag string
  * ``\"tie\"`` → tag string
  * ``\"fail\"`` → tag string

Optional:

* ``blocked_tag`` (string): reserved for future blocked-run handling; not used in this slice.
* ``notes`` (string): human-readable bundle metadata; not interpreted by the evaluator.

The evaluator reads ``diagnostics[\"sham_comparison\"]`` (``beat`` / ``tie`` / ``fail``) and
selects ``final_tag`` from the mapping. No precedence engine, no reporting, no dynamic policy merge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_SHAM_KEYS = ("beat", "tie", "fail")


class RuleEvaluationError(Exception):
    """Raised when the rules bundle is invalid or evaluation cannot complete."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _resolve_rules_path(cfg: dict[str, Any]) -> Path:
    path = Path(cfg["rules"]["rules_path"])
    if path.is_absolute():
        return path
    workspace = cfg["inputs"].get("workspace_root")
    if workspace:
        return (Path(workspace) / path).resolve()
    return path.resolve()


def _load_rules_bundle(cfg: dict[str, Any]) -> dict[str, Any]:
    rules_path = _resolve_rules_path(cfg)
    if not rules_path.is_file():
        raise RuleEvaluationError(f"Rules file not found: {rules_path}")

    try:
        with rules_path.open(encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        raise RuleEvaluationError(f"Invalid JSON in rules file {rules_path}: {e}") from e

    if not isinstance(payload, dict):
        raise RuleEvaluationError("Rules file must contain a JSON object at the top level.")

    if "rule_set_id" not in payload or not isinstance(payload["rule_set_id"], str):
        raise RuleEvaluationError("Rules bundle missing non-empty string field 'rule_set_id'.")
    if not payload["rule_set_id"].strip():
        raise RuleEvaluationError("Rules bundle field 'rule_set_id' must be non-empty.")

    if "tag_when_sham_comparison" not in payload:
        raise RuleEvaluationError("Rules bundle missing required field 'tag_when_sham_comparison'.")
    tag_map = payload["tag_when_sham_comparison"]
    if not isinstance(tag_map, dict):
        raise RuleEvaluationError("Rules bundle field 'tag_when_sham_comparison' must be an object.")

    for key in REQUIRED_SHAM_KEYS:
        if key not in tag_map:
            raise RuleEvaluationError(
                f"tag_when_sham_comparison missing required key {key!r}."
            )
        val = tag_map[key]
        if not isinstance(val, str) or not val.strip():
            raise RuleEvaluationError(
                f"tag_when_sham_comparison[{key!r}] must be a non-empty string."
            )

    return payload


def evaluate_rules(cfg: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Apply the rules bundle to Stage 5 *diagnostics*.

    Returns a plain dict with ``rule_set_id``, ``final_tag``, ``reason``, ``diagnostic_basis``.
    """
    bundle = _load_rules_bundle(cfg)
    bundle_id = bundle["rule_set_id"].strip()
    config_id = cfg["rules"]["rule_set_id"].strip()
    if bundle_id != config_id:
        raise RuleEvaluationError(
            f"rules.rule_set_id ({config_id!r}) does not match bundle rule_set_id ({bundle_id!r})."
        )

    sham = diagnostics.get("sham_comparison")
    if not isinstance(sham, str) or not sham:
        raise RuleEvaluationError(
            "diagnostics.sham_comparison is missing, empty, or not a string."
        )

    tag_map: dict[str, Any] = bundle["tag_when_sham_comparison"]
    if sham not in tag_map:
        raise RuleEvaluationError(
            f"diagnostics.sham_comparison {sham!r} is not mapped in tag_when_sham_comparison "
            f"(expected one of {list(REQUIRED_SHAM_KEYS)})."
        )

    final_tag = tag_map[sham]
    reason = (
        f"Mapped sham_comparison={sham!r} to {final_tag!r} via tag_when_sham_comparison."
    )

    basis: dict[str, Any] = {"sham_comparison": sham}
    if "pooled_S_live" in diagnostics:
        basis["pooled_S_live"] = diagnostics["pooled_S_live"]

    return {
        "rule_set_id": bundle_id,
        "final_tag": final_tag,
        "reason": reason,
        "diagnostic_basis": basis,
    }
