# QC panel retention tests

Fixture-based test for the `gwas-ssf-ragged` generator's unconditional
QC-panel retention (issue #28/#29/#30): a Store Family that configures
`filter.qc_panel` retains that panel's variants in every Analysis's filtered
file regardless of `p_value`, additive to whatever signal-driven
(`cis`/`significant_trans`/`suggestive_trans`) regions that Analysis already
qualifies for.

Run from the repository root:

```sh
pixi run Rscript tests/qc-panel-retention/run_tests.R
```

This regenerates a single fixture Analysis with **zero** significant or
suggestive hits (so the existing signal-driven sparse-region policy alone
would retain nothing), 15 rows at positions also present in a small fixture
QC panel, and 15 unrelated "null" rows. It runs the real generator (`emit` ->
`validate` -> `filter`) twice against the same source data:

- with `filter.qc_panel` enabled, asserting exactly the 15 QC-panel positions
  are retained (not the 15 null positions), recorded in
  `sidecars/sparse_regions.tsv` as `region_kind: qc_panel`, with
  `sidecars/filter_summary.tsv`'s new `qc_panel_rows` column reading 15, and
  `build.yaml`'s `qc_panel` block round-tripping the family's config;
- with `filter.qc_panel` absent, asserting nothing is retained at all and
  `build.yaml` has no `qc_panel` key — proving retention is additive/opt-in,
  not a change to a Store Family's existing behaviour.

The existing pqtl-interval-2018 and metabolome-plasma-2023 families (which do
not configure `filter.qc_panel`) are unaffected by this change other than
gaining the new always-present `qc_panel_rows` column (reading `0`) in
`sidecars/filter_summary.tsv`; see `tests/no-cis-region-policy` and
`tests/effect-scale-validation` for the regression coverage proving that.
