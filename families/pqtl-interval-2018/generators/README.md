# pqtl-interval-2018 Manifest Generator

This Store Family's Manifest Generator selects analyses from the
`gwas-catalog-ssf` Source Collection and emits a candidate release bundle
(`../releases/<family-release-id>/`).

It is a **thin family-specific wrapper** over the shared engine at
`resources/generators/gwas-ssf-ragged/`. The engine is generic across all
molecular GWAS-SSF ragged stores; only this family's inputs differ, held here as:

- `config.yaml` — the analyte selection (GWAS Catalog accessions), the
  authoritative gene / cis-coordinate source (SomaScan SeqId → gene → GRCh38 via
  Ensembl REST), the per-analysis metadata (N, ancestry, effect scale = sd_units,
  tissue), and the sparse-region filter policy (cis ±1 Mb; significant trans
  p≤5e-8, merged ±1 Mb; suggestive p≤1e-5, lead SNPs only; MHC analytes flagged).
- `generate.R` — a one-call driver that runs the shared engine with `config.yaml`
  and writes the release bundle.

The engine downloads each `<GCST>.h.tsv.gz`, filters it to the sparse regions
(deleting the full download as it goes), and emits `analyses.tsv` + `build.yaml`.
opengwasdb then builds the ragged store from that bundle via
`opengwasdb.layouts.ragged.build_ssf:build_ragged_from_ssf`.

> Prototype note: the working spike scripts live at
> `resources/scripts/ragged-spike/` (`download-filter.R`, `make-manifest.R`,
> `build-store.py`). Promoting them into this structure — generalising the engine
> and reducing this family to `config.yaml` + `generate.R` — is the remaining
> migration (see issue #8 resolution and #9).
