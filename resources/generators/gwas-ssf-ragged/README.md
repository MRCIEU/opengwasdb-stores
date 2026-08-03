# GWAS-SSF Ragged Generator

Shared generator for molecular GWAS Catalog harmonised GWAS-SSF releases that
should be stored as ragged observed-only OpenGWASDB stores.

The generator is deliberately split into three steps:

```sh
Rscript resources/generators/gwas-ssf-ragged/generate.R \
  --config=families/pqtl-interval-2018/generators/config.yaml \
  --mode=emit

Rscript resources/generators/gwas-ssf-ragged/generate.R \
  --config=families/pqtl-interval-2018/generators/config.yaml \
  --mode=filter

OPENGWASDB_REPO=/path/to/opengwasdb
PYTHONPATH="${OPENGWASDB_REPO}" \
  "${OPENGWASDB_REPO}/.venv/bin/python" \
  resources/generators/gwas-ssf-ragged/build-store.py \
  --release-dir=families/pqtl-interval-2018/releases/2018-sun-pilot-100
```

`emit` freezes the selected analyses and writes a release bundle. `filter`
downloads each full harmonised GWAS-SSF file transiently, writes a filtered
GWAS-SSF-shaped file containing the configured sparse regions, deletes the full
download, and stamps checksums/sizes back into `analyses.tsv`. `build-store.py`
passes the filtered files to OpenGWASDB and records a small read-back report.
`refresh-artifacts` updates artifact paths in an existing release bundle after
changing `output.artifact_root` or `output.artifact_subdir`. `refresh-build`
re-writes `build.yaml` from the current config (for example after adding or
changing `reference_resources`/`effect_scale_validation`) without touching
`analyses.tsv`.

Run reference-AF effect-scale validation after `filter` and before
`build-store.py` (issue #16):

```sh
Rscript resources/generators/gwas-ssf-ragged/generate.R \
  --config=families/pqtl-interval-2018/generators/config.yaml \
  --mode=effect-scale
```

This uses the shared engine at `resources/lib/effect_scale_validation.R` to
choose an allele-frequency source per Analysis (source AF when usable,
otherwise a configured `reference_resources` fallback keyed by the assigned
ancestry), align alleles conservatively, compute implied phenotype-SD
diagnostics from standard error/N/MAF, and write
`sidecars/sd_estimation.tsv`. It updates `original_sd`/`original_sd_method` in
`analyses.tsv` only for Analyses that needed estimation (not
`declared_standardised` ones, which keep their source declaration and gain QC
evidence instead), and merges empirical `checks.effect_scale`/
`checks.sd_estimation` into `validation.yaml` without discarding the
schema/files/reader-smoke-test/sparse-regions checks that `build-store.py`
separately maintains. A release only needs this step when its config declares
`effect_scale_validation`; otherwise those checks remain `not_run`, as before.
See `docs/release-metadata-schema.md` for the config and sidecar field
reference, and `tests/effect-scale-validation/` for fixture coverage.

The sparse policy implemented here is:

- cis windows: every target gene span plus/minus `cis_flank_bp`, retained in
  full.
- significant trans: non-cis variants with `p_value <= significant_p`, expanded
  plus/minus `trans_flank_bp`, merged per chromosome, retained in full.
- suggestive trans: non-cis and non-significant-trans variants with
  `significant_p < p_value <= suggestive_p`, kept as distance-pruned lead
  variants only.

Large filtered files, transient downloads, and stores are written under the
configured `output.artifact_root` plus `output.artifact_subdir`. The release
bundle and small sidecars are tracked in this repository.
