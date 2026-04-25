# TDT Demo

## Step 1: Run the CLI

The CLI takes a **run config** JSON (object), not the raw records file. From the project root, run:

python3 tdt_cli.py demo/run.json

## Step 2: View outputs

Check the generated files under `outputs/demo/`:

- `outputs/demo/rows.csv`
- `outputs/demo/summary.csv`
- `outputs/demo/summary.md`

## What to look for

- Compare good_1 vs weak_1 vs failure_1
- Notice how signals differ
- Observe how structural issues are surfaced
