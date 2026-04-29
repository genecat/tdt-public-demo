# Trinity Diagnostic Tool (TDT) — Public Demo

This repository is a **sanitized public demo** of TDT.

TDT evaluates **structural integrity** in language outputs (instruction alignment, coherence, signal-level weaknesses).  
TDT does **not** determine truth and is **not** a fact-checker.

## What Is Included

- Streamlit demo app (`tdt_app.py`)
- CLI runner (`tdt_cli.py`)
- Minimal runtime code (`src/`)
- Demo inputs/config (`demo/`)
- Required rules and sham baseline files (`configs/`, `reference_data/`)
- Interpretation and walkthrough docs

## What Is Not Included

This public demo excludes the full private research/development repository, including broader experiments, historical outputs, research artifacts, and internal materials.

## Run Locally

From this folder:

```bash
pip install -r requirements.txt
streamlit run tdt_app.py
```

Then use:

- **Run demo (demo/run.json)** for the included sample batch
- **Try Your Own Input** for a single custom input

## Important Interpretation Note

A low-risk or stable structural result does **not** mean an output is true.  
A high-risk or unstable structural result does **not** mean an output is false.

TDT is best used as a diagnostic layer alongside human review.

## Copyright and Use Notice

Copyright © 2026 Eugene Catrambone. All rights reserved.

This repository is provided for demonstration and evaluation purposes only. No license is granted for commercial use, redistribution, modification, sublicensing, or derivative works without prior written permission.

This public repository is a sanitized demonstration version of TDT and does not include the full private research/development repository, broader experiments, historical artifacts, proprietary calibration materials, or internal implementation materials.
