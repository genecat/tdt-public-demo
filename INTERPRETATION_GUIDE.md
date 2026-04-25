# TDT Interpretation Guide

## What TDT Measures

The Trinity Diagnostic Tool (TDT) measures **structural integrity** in language outputs.  
In plain terms, it checks how well an output holds together: whether it follows instructions, stays coherent, and provides meaningful content.

TDT is designed as a transparent, deterministic diagnostic system. It evaluates structure using explicit rules and reproducible scoring logic.

## What TDT Does Not Measure

TDT does **not** measure truth, factual correctness, or real-world validity.

- A response can score as structurally strong and still contain factual mistakes.
- A response can score as structurally weak and still contain some true statements.

TDT is therefore not a fact checker, not a truth engine, and not a final arbiter of correctness.

## How to Read the S-Metric

The **S-metric** is a **batch-level** indicator. It does not describe one single row; it describes the overall structural balance of a run.

Conceptually, S compares:

- **Concentration (c):** how tightly outputs cluster
- **Dispersion (d):** how widely outputs deviate

Formula:

`S = 1 - |c - d| / (c + d)`

Interpretation:

- Higher S suggests more stable structural behavior across the batch.
- Lower S suggests greater structural imbalance across the batch.

Important: S is a structural stability signal for the group, not proof of factual reliability.

## How to Read Row-Level Signals

Row-level signals identify **specific structural weaknesses** in individual outputs.

Typical examples include:

- Repetition or redundancy
- Topic drift
- Vagueness vs specificity problems
- Coherence breaks
- Internal consistency issues
- Instruction alignment failures
- Missing critical slots
- Low information density
- Weak reasoning progression
- Constraint instability

Use these signals to understand *why* a row appears strong or weak, and where intervention is needed.

## Low / Medium / High Risk Meaning

Risk levels are structural diagnostics, not truth labels.

- **Low risk** means the output appears structurally sound under TDT rules. It does **not** mean the output is true.
- **Medium risk** means mixed structural quality; targeted review is recommended.
- **High risk** means significant structural issues are present. It does **not** mean the output is false.

In short: risk indicates likely structural failure modes, not factual verdicts.

## How to Use `rows.csv`

Use `rows.csv` when you need per-item diagnostic detail.

- Review one row at a time.
- Compare signal patterns across rows.
- Identify recurring weaknesses (for example, repeated instruction misalignment).
- Use it for error triage, prompt refinement, and quality-control workflows.

`rows.csv` is usually the best place to start when investigating *what went wrong* in specific outputs.

## How to Use `summary.csv`

Use `summary.csv` for compact, aggregate metrics suitable for tracking and comparison.

- Monitor batch-level trends over time.
- Compare runs, models, prompts, or configuration changes.
- Check overall stability indicators such as S and risk distribution metrics.

`summary.csv` is ideal for dashboards, reporting pipelines, and regression detection.

## How to Use `summary.md`

Use `summary.md` for human-readable review and communication.

- Share findings with stakeholders who do not need raw CSV detail.
- Capture headline structural results and diagnostics in narrative form.
- Pair it with `rows.csv` when deeper investigation is required.

`summary.md` is generally the most accessible artifact for non-technical readers.

## Practical Interpretation Example

Suppose a run includes three outputs:

- One that clearly follows instructions with specific, coherent content
- One that is vague and generic
- One that ignores the task entirely

In TDT terms, you would typically expect:

- The first output to show lower structural risk
- The second to show elevated vagueness or density-related concerns
- The third to show instruction-alignment or integrity failures

At the batch level, the S-metric may drop if these outputs are structurally inconsistent with each other.  
This indicates instability across the set, not a direct statement about truth.

## Current Limitations

- TDT evaluates structure, not factual correctness.
- Diagnostic quality depends on the defined rule set and calibration assumptions.
- Batch-level metrics can hide row-level nuance unless `rows.csv` is reviewed.
- Phase 2 signals 6-10 are validated, but they may not yet affect `combined_row_risk` unless the current codebase already integrates them into that computation path.

Because of these limits, TDT should be interpreted as a diagnostic instrument, not a standalone decision authority.

## Recommended Use

Use TDT as a **diagnostic layer**, not a final judge.

Recommended workflow:

1. Run TDT on a batch.
2. Check `summary.csv` and `summary.md` for high-level stability and risk patterns.
3. Drill into `rows.csv` to inspect concrete failure modes.
4. Apply human review (and, when needed, factual verification) before making final decisions.

This approach combines deterministic structural diagnostics with expert judgment, which is the intended operational model for Phase 2.
