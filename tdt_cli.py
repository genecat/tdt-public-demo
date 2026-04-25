"""TDT v1 CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `import runner`, `import trinity_core`, etc. when running from repo root without install.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from diagnostic_engine import DiagnosticError, run_diagnostics
from reporting import write_run_reports
from runner.config_loader import ConfigValidationError, load_and_validate_run_config
from runner.ingestion import IngestionError, load_records
from rules import RuleEvaluationError, evaluate_rules
from trinity_core import compute_rows, pool_pooled_S


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tdt",
        description="Trinity Diagnostic Tool v1 — CLI.",
    )
    parser.add_argument(
        "config",
        nargs="?",
        metavar="CONFIG",
        help="Path to run configuration JSON.",
    )
    args = parser.parse_args(argv)
    if args.config is None:
        parser.print_help()
        return 0

    config_path = Path(args.config)
    try:
        cfg = load_and_validate_run_config(config_path)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in config file: {e}", file=sys.stderr)
        return 1
    except ConfigValidationError as e:
        print("error: configuration validation failed:", file=sys.stderr)
        for line in e.messages:
            print(f"  - {line}", file=sys.stderr)
        return 1

    run_id = cfg["run"]["run_id"]

    try:
        records = load_records(cfg)
    except IngestionError as e:
        print(f"error: ingestion failed: {e.message}", file=sys.stderr)
        return 1

    try:
        computed = compute_rows(records)
        agg = pool_pooled_S(computed)
    except TypeError as e:
        print(f"error: core computation failed: {e}", file=sys.stderr)
        return 1

    pooled_S_live = float(agg["pooled_S"])

    try:
        diag = run_diagnostics(cfg, pooled_S_live=pooled_S_live, computed_rows=computed)
    except DiagnosticError as e:
        print(f"error: diagnostics failed: {e.message}", file=sys.stderr)
        return 1

    try:
        ruled = evaluate_rules(cfg, diag)
    except RuleEvaluationError as e:
        print(f"error: rule evaluation failed: {e.message}", file=sys.stderr)
        return 1

    try:
        paths = write_run_reports(
            cfg,
            computed_rows=computed,
            pool_aggregate=agg,
            diagnostics=diag,
            rule_result=ruled,
        )
    except (OSError, ValueError) as e:
        print(f"error: reporting failed: {e}", file=sys.stderr)
        return 1

    csv_p = paths["csv"]
    md_p = paths["markdown"]
    print(
        f"ok: run_id={run_id!r} final_tag={ruled['final_tag']!r} "
        f"outputs: {csv_p} ; {md_p}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
