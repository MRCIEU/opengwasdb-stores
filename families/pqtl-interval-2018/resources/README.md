# pqtl-interval-2018 Resources

`somascan-targets.tsv` records the local target-coordinate resource used by the
Sun et al. INTERVAL pQTL release generator.

The table is generated from SomaLogic's `SomaScan.db` SQLite annotations and
adds GRCh38 gene coordinates from Ensembl BioMart. It is intentionally separate
from release `analyses.tsv`: the release generator should parse the SomaScan
SeqId from each GWAS Catalog trait label, join to this target resource, and then
derive cis regions from the matched gene span(s).

Historical GWAS Catalog traits can carry older assay SeqIds that are absent from
the current `SomaScan.db` menu resource. Those rows should be handled by an
explicit study-specific override or fallback sidecar, not by silently swapping to
another SeqId with a similar target name.

Regenerate from the repository root with:

```sh
Rscript families/pqtl-interval-2018/resources/scripts/generate-somascan-targets.R
```

The generator caches the upstream SQLite database under `resources/cache/`,
which is ignored by Git. Set `REFRESH_SOMASCAN_DB=TRUE` to redownload it.

Columns:

- `seqid`: SomaLogic SeqId / `SomaScan.db` `PROBEID`, using the package's
  canonical hyphen form, for example `12651-21`.
- `target_full_name`: SomaScan target full name.
- `entrez_id`: Entrez Gene ID from `SomaScan.db`.
- `ensembl_gene_id`, `gene_name`, `chromosome`, `gene_start`, `gene_end`,
  `strand`, `gene_biotype`: Ensembl gene annotation fields.
- `genome_build`: coordinate build, currently `GRCh38`.
- `is_primary_chromosome`: whether the Ensembl coordinate is on chr1-22, X, Y,
  or MT rather than an alternate scaffold or patch.
- `mhc`: whether the mapped gene overlaps chr6:25-34 Mb.
- `somascan_is_multiple`: `SomaScan.db` multi-gene target flag.
- `menu_v4_0`, `menu_v4_1`, `menu_v5_0`: SomaScan menu membership.
- `mapping_status`: `mapped_to_ensembl`, `no_entrez_id`, or
  `no_ensembl_match`.
- `mapping_source`, `somascan_db_version`, `coordinate_source`,
  `coordinate_source_url`: provenance.
