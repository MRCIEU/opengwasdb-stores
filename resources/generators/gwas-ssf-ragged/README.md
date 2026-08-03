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

The sparse policy implemented here is:

- cis windows: every target gene span plus/minus `cis_flank_bp`, retained in
  full.
- significant trans: non-cis variants with `p_value <= significant_p`, expanded
  plus/minus `trans_flank_bp`, merged per chromosome, retained in full.
- suggestive trans: non-cis and non-significant-trans variants with
  `significant_p < p_value <= suggestive_p`, kept as distance-pruned lead
  variants only.

Large filtered files and stores are written under `resources/data/` and are
ignored by Git. The release bundle and small sidecars are tracked.
