# TDT Demo Walkthrough

## Purpose

This demo shows how TDT distinguishes strong, weak, and failed outputs by structure, not truth.

## Demo Inputs

The demo uses three items:

1. good_1 — clear, complete photosynthesis answer
2. weak_1 — vague photosynthesis answer
3. failure_1 — fails the World War I instruction by answering about World War II

## How to Run

python3 tdt_cli.py demo/run.json

## Expected Outputs

The run produces (under `outputs/demo/` by default):

- `outputs/demo/rows.csv`
- `outputs/demo/summary.csv`
- `outputs/demo/summary.md`

## What to Look For

Compare these structural signals across the three items:

- instruction alignment
- specificity / vagueness
- information density
- topic drift
- reasoning progression
- constraint stability

## Key Lesson

A response can sound fluent but still be structurally weak.

TDT helps surface that weakness without using another AI judge.

## Current Limitations

- TDT does not check factual truth.
- TDT does not replace human review.
- TDT is a diagnostic layer.
- Phase 2 is CLI-based and not yet a polished user interface.

## Summary

TDT evaluates whether outputs hold together structurally. It does not decide whether they are true.
