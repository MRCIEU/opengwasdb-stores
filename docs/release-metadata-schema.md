# Release metadata schema

This document drafts the metadata files emitted by a Store Family Manifest
Generator for an accepted Store Release bundle.

The schema is intentionally simple:

- `release.yaml` records store-level identity, source snapshot, release defaults,
  and pointers to sidecars.
- `analyses.tsv` records one resolved row per Analysis. Store-level defaults may
  be repeated here after expansion, because builders and reviewers should be able
  to reason about each row without chasing YAML inheritance.
- `build.yaml` records the concrete OpenGWASDB build shape.
- `validation.yaml` records acceptance checks and pointers to logs or reports.
- sidecars record detailed evidence used to derive compact manifest fields.

Release bundles live at:

```text
families/<store-family-id>/releases/<family-release-id>/
```

## Pipeline stages

| Stage | Purpose | Typical inputs | Outputs |
|---|---|---|---|
| `discover` | Snapshot available upstream analyses and files. | Source inventory, GWAS Catalog studies table, source `meta.yaml`, provider APIs. | Raw candidate records and source-file locations. |
| `select` | Apply Store Family inclusion rules. | Candidate records, family config, priority lists, publication/analyte filters. | Selected Analysis set for a proposed Store Release. |
| `derive` | Add generated analytical metadata. | Selected rows, source files, OpenGWASDB readers, reference resources, Ensembl, checksums. | Resolved `analyses.tsv` columns and sidecar evidence. |
| `emit` | Write a reproducible release bundle. | Resolved rows, sidecars, build choices, generator provenance. | `release.yaml`, `analyses.tsv`, `build.yaml`, `validation.yaml`, sidecars. |
| `accept` | Check that the bundle is complete enough to build. | Release bundle, schema checks, lightweight source/readability checks. | Updated `validation.yaml` and release status. |

## `release.yaml`

Store-level release metadata. Required fields are required for an accepted
release bundle; candidate bundles may leave lifecycle timestamps null.

| Field | Required | Description |
|---|---:|---|
| `metadata_schema_version` | Yes | Schema version for this release bundle format. Start with `1`. |
| `store_family_id` | Yes | Stable Store Family ID matching the family directory. |
| `family_release_id` | Yes | Release ID unique within the Store Family, such as `2018-ieu`, `r2026-07-10`, or `phase-1`. |
| `status` | Yes | Registry lifecycle state: `candidate`, `accepted`, `built`, `validated`, `superseded`, or `withdrawn`. |
| `source_collection_id` | Yes | Source Collection used by this Store Family. |
| `source_snapshot_id` | Yes | Dated or provider-native source snapshot used for this release, for example a GWAS Catalog studies-table release date. |
| `release_kind` | Yes | Release cadence kind, such as `source-natural`, `date-snapshot`, `one-off`, or `corrected`. |
| `association_coverage` | Yes | Expected association coverage: `full_gwas`, `cis`, `trans`, `cis_plus_signals`, `top_hits`, or `unknown`. |
| `description` | Yes | Short human-readable release description. |
| `created_at` | Optional | Timestamp when the candidate bundle was generated. |
| `accepted_at` | Optional | Timestamp when the bundle was accepted as the release input record. |
| `generator.name` | Yes | Manifest Generator name or path. |
| `generator.version` | Optional | Generator package version, git commit, or script hash. |
| `generator.command` | Optional | Re-run command used to generate the bundle. |
| `source_defaults.source_genome_build` | Yes | Default genome build for source files if not overridden in `analyses.tsv`. |
| `source_defaults.license` | Yes | Default source licence if not overridden in `analyses.tsv`. |
| `source_defaults.original_effect_scale` | Optional | Default original effect scale if constant across the release. |
| `source_defaults.stored_effect_scale` | Yes | Stored effect scale for OpenGWASDB. This should be `sd`. |
| `source_defaults.sample_size_kind` | Optional | Default sample-size kind if constant across the release. |
| `source_defaults.source_ancestry_label` | Optional | Default source ancestry label if constant across the release. |
| `source_defaults.assigned_ancestry` | Optional | Default assigned ancestry if constant across the release. |
| `lineage.derived_from` | Optional | Parent release ID or URI when this release derives from another release. |
| `sidecars.ancestry` | Optional | Path to ancestry evidence sidecar. |
| `sidecars.sparse_regions` | Optional | Path to sparse-region sidecar. |
| `sidecars.derivations` | Optional | Path to general derivation or curation sidecar. |
| `notes` | Optional | Free-text release notes. |

## `analyses.tsv`

One row per Analysis. Values should be resolved after applying `release.yaml`
defaults, even when that repeats store-level metadata. This makes the table
streamable, diffable, and directly consumable by builders.

Use empty strings for unknown optional values in TSV.

| Field | Required | Description |
|---|---:|---|
| `analysis_id` | Yes | Stable registry Analysis ID. Usually source-derived unless the source lacks stable IDs. |
| `source_analysis_id` | Optional | Upstream analysis identifier, such as a GCST accession or OpenGWAS ID, when the Source Collection provides one. |
| `source_label` | Yes | Upstream trait or phenotype label preserved as source provenance. |
| `trait_ontology_name` | Optional | Ontology or controlled vocabulary that defines `trait_ontology_id`, such as EFO, MONDO, OBA, or a source-local analyte vocabulary. |
| `trait_ontology_id` | Optional | Ontology or controlled-vocabulary identifier for the analysed trait, when available. |
| `source_file` | Yes | Source file or filtered source file consumed by the builder. |
| `source_bundle_id` | Optional | Identifier for a multi-file Source Bundle when one file is insufficient. |
| `checksum` | Yes | Checksum for `source_file` or source bundle manifest. |
| `checksum_algorithm` | Yes | Algorithm used for `checksum`, for example `sha256`. |
| `size_bytes` | Optional | File size in bytes. |
| `source_genome_build` | Yes | Genome build of source coordinates for this Analysis. |
| `license` | Yes | Licence or usage terms after applying source defaults and row overrides. |
| `publication_doi` | Optional | DOI for compact bibliographic provenance. |
| `publication_pmid` | Optional | PMID for compact bibliographic provenance. |
| `consortium` | Optional | Consortium or provider label when DOI/PMID is not enough for provenance. |
| `source_ancestry_label` | Optional | Upstream ancestry/population label. |
| `assigned_ancestry` | Optional | Registry-normalised ancestry used for store inclusion and routing. Empty means unassigned. |
| `ancestry_assignment_method` | Yes | Controlled value: `af_assigned`, `source_fallback`, `source_trusted_no_af`, or `unassigned`. |
| `original_effect_scale` | Yes | Controlled value for upstream effect units, such as `sd`, `cm`, `logOR`, or another approved vocabulary item. |
| `original_sd` | Optional | Source-provided or estimated phenotype SD on the original scale. Empty for binary traits or unavailable values. |
| `original_sd_method` | Yes | Controlled value describing `original_sd`: `source_provided`, `estimated_from_source_maf`, `estimated_from_reference_maf`, `binary_trait`, or `unavailable`. |
| `stored_effect_scale` | Yes | Effect scale stored by OpenGWASDB. This should be `sd`. |
| `sample_size_kind` | Yes | `total`, `case_control`, `effective`, `variant_level`, or `unknown`. |
| `sample_size_scope` | Yes | `analysis_level`, `variant_level`, or `unknown`. |
| `sample_size` | Optional | Total or effective sample size when a scalar value is valid. |
| `n_cases` | Optional | Case count for binary traits. |
| `n_controls` | Optional | Control count for binary traits. |
| `analysis_group_id` | Optional | Grouping key for analyses sharing a publication, analyte panel, phenotype batch, or source bundle. |
| `inclusion_reason` | Optional | Short family-specific reason this Analysis was selected. |
| `exclude_from_build` | Optional | `true` only for rows retained for audit but intentionally skipped by the build. Accepted build inputs normally omit excluded rows. |

## `build.yaml`

Build-level metadata and execution configuration. This file describes how the
accepted manifest should become an OpenGWASDB store, not which analyses belong
to the release.

| Field | Required | Description |
|---|---:|---|
| `store_family_id` | Yes | Store Family ID. |
| `family_release_id` | Yes | Release ID. |
| `store_layout` | Yes | `dense-observed`, `dense-reference-completed`, `ragged-observed`, or `ragged-reference-completed`. |
| `completion_state` | Yes | `observed-only` or `reference-completed`. |
| `builder.package` | Yes | Package that owns the builder. Usually `opengwasdb`. |
| `builder.entrypoint` | Yes | Importable builder entry point. |
| `source.source_format` | Yes | Source Format read by the builder, such as `gwas-vcf`, `gwas-ssf`, or `besd`. |
| `source.source_reader_capability` | Yes | OpenGWASDB reader capability for the Source Collection. |
| `normalisation.target_reference_assembly` | Yes | Target reference assembly for stored coordinates. |
| `normalisation.liftover` | Optional | Liftover policy or chain when source and target assemblies differ. |
| `effects.stored_effect_scale` | Yes | Stored effect scale. This should be `sd`. |
| `shape.association_coverage` | Yes | Repeats the release association coverage for builder convenience. |
| `shape.ragged_region_policy` | Optional | Named sparse-region policy for ragged releases. |
| `reference_resources` | Optional | List of reference resources used for completion, ancestry assignment, MAF lookup, or validation. |
| `validation.required` | Yes | Whether validation is required before publishing the built store. |
| `artifacts.store_uri` | Optional | URI for the built store artifact. |
| `artifacts.build_log_uri` | Optional | URI for detailed build logs. |

## `validation.yaml`

Release-level acceptance and build validation summary.

| Field | Required | Description |
|---|---:|---|
| `status` | Yes | `not_run`, `passed`, `failed`, or `passed_with_warnings`. |
| `validated_at` | Optional | Timestamp of the latest validation run. |
| `validator.name` | Optional | Validator script, package, or workflow name. |
| `validator.version` | Optional | Validator version, git commit, or script hash. |
| `checks.schema` | Yes | Whether required files and fields are present with valid controlled values. |
| `checks.files` | Yes | Whether referenced source or filtered files exist and match checksums. |
| `checks.reader_smoke_test` | Optional | Whether OpenGWASDB can read a small sample from each source file or bundle. |
| `checks.ancestry` | Optional | Whether ancestry fields are valid and sidecar evidence is internally consistent. |
| `checks.effect_scale` | Optional | Whether original/stored effect-scale fields are valid and conversion inputs are present. |
| `checks.sparse_regions` | Optional | Whether ragged region sidecars match filtered files. |
| `reports` | Optional | URIs or paths to detailed reports. |
| `warnings` | Optional | List of non-blocking warnings. |
| `errors` | Optional | List of blocking errors. |

## Ancestry sidecar

Suggested path: `sidecars/ancestry.tsv`.

One row per Analysis when ancestry assignment was attempted or source ancestry
required mapping.

| Field | Required | Description |
|---|---:|---|
| `analysis_id` | Yes | Registry Analysis ID matching `analyses.tsv`. |
| `source_analysis_id` | Yes | Upstream analysis identifier. |
| `source_ancestry_label` | Optional | Upstream ancestry label. |
| `assigned_ancestry` | Optional | Final assigned ancestry used for routing. |
| `ancestry_assignment_method` | Yes | Same controlled value as `analyses.tsv`. |
| `ancestry_reference_id` | Optional | Reference panel/catalogue used for AF-based assignment or MAF fallback. |
| `af_overlap` | Optional | Number or proportion of variants overlapping the reference panel. |
| `dominant_superpop` | Optional | Dominant reference super-population. |
| `dominant_proportion` | Optional | Estimated dominant ancestry proportion. |
| `runner_up_margin` | Optional | Difference between dominant and runner-up proportions. |
| `nnls_residual` | Optional | Residual from mixture fitting, when used. |
| `gate_reason` | Optional | Pass/fail or exclusion reason from the ancestry assignment gate. |
| `ancestry_prop_*` | Optional | Optional family of columns for estimated reference ancestry proportions. |
| `source_assigned_mismatch` | Optional | `true` when source label and AF-based assignment disagree. |
| `ancestry_notes` | Optional | Free-text notes for review dashboards. |

## Sparse-region sidecar

Suggested path: `sidecars/sparse_regions.tsv`.

One row per retained region for ragged stores.

| Field | Required | Description |
|---|---:|---|
| `analysis_id` | Yes | Registry Analysis ID matching `analyses.tsv`. |
| `region_id` | Yes | Stable region identifier within the Analysis. |
| `region_kind` | Yes | Controlled value such as `cis`, `significant_trans`, `suggestive_trans`, or `manual`. |
| `chromosome` | Yes | Chromosome name in source coordinates. |
| `start` | Yes | 1-based inclusive region start. |
| `end` | Yes | 1-based inclusive region end. |
| `source_genome_build` | Yes | Genome build of the region coordinates. |
| `target_id` | Optional | Gene, analyte, or other target defining the region. |
| `target_label` | Optional | Human-readable target label. |
| `lead_variant_id` | Optional | Lead variant for signal-defined regions. |
| `pvalue_threshold` | Optional | Threshold used to define signal-derived regions. |
| `n_variants_retained` | Optional | Number of variants retained in the filtered source file for this region. |
| `region_policy_id` | Yes | Named sparse-region policy from `build.yaml`. |

## General derivation sidecar

Suggested path: `sidecars/derivations.tsv`.

Use only when compact `analyses.tsv` fields need additional evidence that does
not belong in a specialised sidecar.

| Field | Required | Description |
|---|---:|---|
| `analysis_id` | Yes | Registry Analysis ID matching `analyses.tsv`. |
| `field` | Yes | Manifest field being explained. |
| `value` | Optional | Resolved value written to the manifest. |
| `method` | Yes | Controlled or script-local method name. |
| `evidence` | Optional | Compact evidence string or URI. |
| `notes` | Optional | Free-text notes for audit. |

## Acceptance rule of thumb

A release bundle is acceptable when `analyses.tsv` is enough for OpenGWASDB to
build the intended store, `release.yaml` and `build.yaml` are enough to explain
what the store is and how to rebuild it, and sidecars are enough to audit any
non-obvious derived metadata without blocking low-effort source ingestion.
