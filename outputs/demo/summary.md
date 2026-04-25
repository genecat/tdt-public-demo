# TDT v1 run summary

This report separates **measured quantities** produced by the audit pipeline from the **operational classification** assigned by the configured rule bundle.

## Run identity

- **run_id**: `demo_3x`
- **model_id**: `demo`
- **benchmark_family**: `demo`
- **panel_size**: `3`

## Measured values (core and diagnostics)

- **pooled_S_live**: `0.5246964633939397`
- **refined_sham_score**: `0.55` (from precomputed sham file)
- **legacy_sham_score**: `0.45` (from precomputed sham file)
- **D_refined_minus_legacy**: `0.10000000000000003`
- **sham_comparison** (diagnostic enum): `beat`
- **row_count**: `3`

## Classification (rule bundle)

- **rule_set_id**: `mwp_demo_v1`
- **final_tag**: `STABLE_CORE`

*Reason:* Mapped sham_comparison='beat' to 'STABLE_CORE' via tag_when_sham_comparison.
