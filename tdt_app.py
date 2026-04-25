"""TDT App UI v1 — local Streamlit dashboard wrapping the existing CLI pipeline.

Run from the project root, e.g.:
    streamlit run tdt_app.py
"""

from __future__ import annotations

import os
import json
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent
DEMO_CONFIG_REL = "demo/run.json"
DEMO_OUT_DIR = REPO_ROOT / "outputs" / "demo"
SUMMARY_CSV = DEMO_OUT_DIR / "summary.csv"
ROWS_CSV = DEMO_OUT_DIR / "rows.csv"
SUMMARY_MD = DEMO_OUT_DIR / "summary.md"

CUSTOM_INPUT_REL = "demo/custom_input.json"
CUSTOM_RUN_REL = "demo/custom_run.json"
CUSTOM_OUT_DIR = REPO_ROOT / "outputs" / "custom"


def _tag_color(final_tag: str) -> str:
    return "#16a34a" if final_tag == "STABLE_CORE" else "#dc2626"


def _s_band(score: float) -> tuple[str, str]:
    if score < 0.33:
        return ("UNSTABLE", "#dc2626")
    if score < 0.66:
        return ("MIXED", "#f59e0b")
    return ("STABLE", "#16a34a")


def _s_cell_style(value: object) -> str:
    try:
        s = float(value)
    except (TypeError, ValueError):
        return ""
    if s < 0.33:
        return "background-color: rgba(220, 38, 38, 0.18); color: #7f1d1d;"
    if s < 0.66:
        return "background-color: rgba(245, 158, 11, 0.18); color: #78350f;"
    return "background-color: rgba(22, 163, 74, 0.18); color: #14532d;"


def _pill_badge(text: str, *, bg: str, fg: str = "white") -> str:
    safe = (text or "—").replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<span style='display:inline-block;padding:0.22rem 0.65rem;"
        f"border-radius:9999px;background:{bg};color:{fg};"
        "font-weight:800;font-size:0.85rem;letter-spacing:0.02em;'>"
        f"{safe}</span>"
    )


def _metric_card(label: str, value: str, *, big: bool = False, extra_html: str = "") -> str:
    v = (value or "—").replace("<", "&lt;").replace(">", "&gt;")
    l = (label or "").replace("<", "&lt;").replace(">", "&gt;")
    size = "3.2rem" if big else "1.35rem"
    weight = "900" if big else "800"
    return (
        "<div style='background:#f6f8fb;border:1px solid rgba(15,23,42,0.10);"
        "border-radius:14px;padding:14px 16px;min-height:92px;'>"
        f"<div style='color:rgba(15,23,42,0.65);font-size:0.78rem;font-weight:700;"
        f"letter-spacing:0.03em;text-transform:uppercase;margin-bottom:6px;'>{l}</div>"
        f"<div style='color:#0f172a;font-size:{size};font-weight:{weight};line-height:1.05;'>{v}</div>"
        f"{extra_html}"
        "</div>"
    )


def _s_interp_bar(active: str, score: float) -> str:
    active = (active or "").upper()
    def _lab(name: str) -> str:
        is_on = name == active
        bg = "rgba(15,23,42,0.08)" if is_on else "transparent"
        bd = "1px solid rgba(15,23,42,0.18)" if is_on else "1px solid transparent"
        fw = "900" if is_on else "700"
        return (
            f"<span style='padding:0.15rem 0.55rem;border-radius:9999px;{bd};"
            f"background:{bg};font-weight:{fw};font-size:0.82rem;'>"
            f"{name}</span>"
        )

    marker_left = max(0.0, min(100.0, score * 100.0))
    return (
        "<div style='margin-top:10px;'>"
        "<div style='position:relative;height:10px;border-radius:9999px;"
        "background: linear-gradient(90deg, #dc2626 0%, #f59e0b 50%, #16a34a 100%);"
        "border:1px solid rgba(15,23,42,0.18);'>"
        f"<div style='position:absolute;left:calc({marker_left}% - 5px);top:-4px;width:10px;height:18px;"
        "border-radius:8px;background:#0f172a;border:2px solid #ffffff;"
        "box-shadow:0 1px 3px rgba(0,0,0,0.35);'></div>"
        "</div>"
        "<div style='display:flex;gap:10px;justify-content:space-between;margin-top:8px;color:#0f172a;'>"
        f"{_lab('UNSTABLE')}{_lab('MIXED')}{_lab('STABLE')}"
        "</div>"
        "</div>"
    )


def _run_cli_demo() -> int:
    """Same entry as `python3 tdt_cli.py demo/run.json` with cwd = repo root."""
    old = os.getcwd()
    try:
        os.chdir(REPO_ROOT)
        from tdt_cli import main  # local import after chdir; adds src/ on sys.path
    except Exception:
        os.chdir(old)
        raise
    try:
        return int(main([DEMO_CONFIG_REL]))
    finally:
        os.chdir(old)


def _run_cli_config(config_rel_path: str) -> int:
    """Run the existing CLI pipeline for an arbitrary config path (relative to repo root)."""
    old = os.getcwd()
    try:
        os.chdir(REPO_ROOT)
        from tdt_cli import main  # local import after chdir; adds src/ on sys.path
    except Exception:
        os.chdir(old)
        raise
    try:
        return int(main([config_rel_path]))
    finally:
        os.chdir(old)


def _load_artifacts(out_dir: Path) -> dict:
    out: dict = {"errors": []}
    summary_csv = out_dir / "summary.csv"
    rows_csv = out_dir / "rows.csv"
    summary_md = out_dir / "summary.md"

    if not summary_csv.is_file():
        out["errors"].append(f"Missing: {summary_csv}")
    else:
        out["summary_df"] = pd.read_csv(summary_csv)
    if not rows_csv.is_file():
        out["errors"].append(f"Missing: {rows_csv}")
    else:
        out["rows_df"] = pd.read_csv(rows_csv)
    if not summary_md.is_file():
        out["errors"].append(f"Missing: {summary_md}")
    else:
        out["summary_md"] = summary_md.read_text(encoding="utf-8")
    return out


def main() -> None:
    st.set_page_config(
        page_title="Trinity Diagnostic Tool",
        page_icon=None,
        layout="wide",
    )

    st.markdown(
        """
<style>
/* Slightly roomier rows + centered numeric cells (applies to st.dataframe output) */
div[data-testid="stDataFrame"] div[role="row"] { align-items: center; }
div[data-testid="stDataFrame"] thead tr th { background: #f8fafc !important; }
div[data-testid="stHorizontalBlock"] { gap: 0.7rem !important; }
</style>
""",
        unsafe_allow_html=True,
    )

    # --- Top banner (product-like header) ---
    st.markdown(
        """
<div style="
  background:#0b1e2d;
  padding:18px 20px;
  border-radius:16px;
  border:1px solid rgba(255,255,255,0.10);
  margin-bottom:14px;">
  <div style="color:white;font-size:1.75rem;font-weight:900;line-height:1.15;">
    TDT Diagnostic Output (MWP)
  </div>
  <div style="color:rgba(255,255,255,0.82);font-size:1.02rem;font-weight:650;margin-top:6px;">
    Batch-level S-metric + row-level diagnostic signals
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Keep disclaimer visible but subtle
    st.markdown(
        "<div style='color:rgba(15,23,42,0.55);font-weight:650;margin:2px 2px 10px 2px;'>"
        "TDT is not a truth engine. It evaluates structural integrity."
        "</div>",
        unsafe_allow_html=True,
    )

    st.header("Try Your Own Input")
    response_text = st.text_area("Paste a response to evaluate", value="", height=140)
    instruction_text = st.text_area(
        "Paste the instruction (optional but recommended)", value="", height=90
    )
    st.caption(
        "Single input runs will show limited structural signals. TDT is strongest on batches."
    )
    if st.button("Run TDT on this input"):
        if not response_text.strip():
            st.warning("Please paste a response before running TDT.")
        else:
            # Build single-row dataset (json_list_v1) and matching run config.
            records = [
                {
                    "item_id": "custom_1",
                    "benchmark_family": "custom",
                    "instruction_task_text": instruction_text.strip() or None,
                    "response_text": response_text,
                }
            ]

            input_path = (REPO_ROOT / CUSTOM_INPUT_REL).resolve()
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

            run_cfg = {
                "run": {
                    "run_schema_version": "1.0",
                    "run_id": "custom_1x",
                    "title": "Custom single-item run",
                },
                "inputs": {
                    "records_path": CUSTOM_INPUT_REL,
                    "input_contract_id": "json_list_v1",
                },
                "computation": {
                    "model_id": "custom",
                    "benchmark_family": "custom",
                    "panel_size": 1,
                    "aggregation_scope": "per_benchmark_family",
                    "pipeline_lock_id": "mwp_demo_lock",
                },
                "diagnostics": {
                    "sham_mode": "refined_magnitude_aware",
                    "sham_baseline": "use_precomputed_file",
                    "sham_baseline_path": "reference_data/mwp_demo_sham.json",
                },
                "rules": {
                    "rule_set_id": "mwp_demo_v1",
                    "rules_path": "configs/mwp_demo_rules.json",
                },
                "outputs": {
                    "output_dir": str(CUSTOM_OUT_DIR.relative_to(REPO_ROOT)),
                },
            }

            run_path = (REPO_ROOT / CUSTOM_RUN_REL).resolve()
            run_path.write_text(json.dumps(run_cfg, indent=2) + "\n", encoding="utf-8")

            with st.spinner("Running TDT on your input…"):
                try:
                    code = _run_cli_config(CUSTOM_RUN_REL)
                except Exception as e:  # noqa: BLE001
                    st.error(f"Pipeline error: {e}")
                    st.session_state["last_run_exit"] = 1
                else:
                    st.session_state["last_run_exit"] = code
                    st.session_state["active_out_dir"] = str(CUSTOM_OUT_DIR)
                    if code == 0:
                        st.success("Run completed successfully.")
                    else:
                        st.error(f"Run exited with code {code}.")

    st.markdown("---")
    st.subheader("Run demo")
    if st.button("Run demo (demo/run.json)"):
        with st.spinner("Running TDT via CLI pipeline…"):
            try:
                code = _run_cli_demo()
            except Exception as e:  # noqa: BLE001 — surface any failure in UI
                st.error(f"Pipeline error: {e}")
                st.session_state["last_run_exit"] = 1
            else:
                st.session_state["last_run_exit"] = code
                st.session_state["active_out_dir"] = str(DEMO_OUT_DIR)
                if code == 0:
                    st.success("Run completed successfully.")
                else:
                    st.error(f"Run exited with code {code}.")

    if "last_run_exit" in st.session_state and st.session_state["last_run_exit"] != 0:
        st.warning("Fix errors above, then re-run. Expected outputs are under `outputs/demo/`.")

    active_out_dir = Path(st.session_state.get("active_out_dir", str(DEMO_OUT_DIR)))
    data = _load_artifacts(active_out_dir)
    for msg in data.get("errors", []):
        st.warning(f"Output not available: {msg}")

    if "summary_df" in data and not data["summary_df"].empty:
        row = data["summary_df"].iloc[0]
        final_tag = str(row.get("final_tag", ""))
        run_id = str(row.get("run_id", ""))
        pooled_s = row.get("pooled_S_live", None)
        pooled_s_value = float(pooled_s) if pooled_s is not None and pd.notna(pooled_s) else None
        row_count = int(row.get("row_count", 0)) if pd.notna(row.get("row_count")) else None

        st.markdown("---")
        st.header("Run Summary")

        # Determine tag badge + S interpretation
        if final_tag == "STABLE_CORE":
            tag_badge = _pill_badge(final_tag, bg="#16a34a")
        elif final_tag.strip() == "":
            tag_badge = _pill_badge("—", bg="#64748b")
        else:
            tag_badge = _pill_badge(final_tag, bg="#f59e0b", fg="#0b1e2d")

        s_label = None
        s_bar_html = ""
        if pooled_s_value is not None:
            s_label, _ = _s_band(pooled_s_value)
            s_bar_html = _s_interp_bar(s_label, pooled_s_value)

        # Metric cards row (S visually dominant)
        c1, c2, c3, c4 = st.columns([1.2, 1.1, 1.6, 1.1], gap="small")
        with c1:
            st.markdown(_metric_card("Run ID", run_id), unsafe_allow_html=True)
        with c2:
            st.markdown(
                _metric_card(
                    "Final Tag",
                    " ",
                    extra_html=f"<div style='margin-top:6px;'>{tag_badge}</div>",
                ),
                unsafe_allow_html=True,
            )
        with c3:
            s_value_text = f"{pooled_s_value:.2f}" if pooled_s_value is not None else "—"
            st.markdown(
                _metric_card("S (pooled)", s_value_text, big=True, extra_html=s_bar_html),
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                _metric_card("Rows processed", str(row_count) if row_count is not None else "—"),
                unsafe_allow_html=True,
            )

    if "rows_df" in data:
        st.markdown("")
        st.markdown("---")
        st.header("Row-Level Diagnostics")
        rows_df = data["rows_df"]
        minimal_cols = [
            "item_id",
            "S",
            "information_density_score",
            "reasoning_progression_score",
            "constraint_stability_score",
            "primary_weakness",
        ]
        show_full = st.checkbox("Show full signal table", value=False)
        display_df = rows_df if show_full else rows_df[[c for c in minimal_cols if c in rows_df.columns]]

        # Polished table: center numeric cols, bold S, roomier rows, keep S color banding
        numeric_cols = [c for c in display_df.columns if c != "item_id" and c != "primary_weakness"]
        styler = display_df.style
        if "S" in display_df.columns:
            styler = styler.applymap(_s_cell_style, subset=["S"])
            styler = styler.set_properties(subset=["S"], **{"font-weight": "800"})
        if numeric_cols:
            styler = styler.set_properties(subset=numeric_cols, **{"text-align": "center"})
        styler = styler.set_properties(**{"padding": "10px 8px"})
        st.dataframe(styler, use_container_width=True, hide_index=True)

    if "summary_md" in data:
        st.markdown("")
        st.markdown("---")
        st.header("Detailed Report")
        st.markdown(data["summary_md"])


if __name__ == "__main__":
    main()
