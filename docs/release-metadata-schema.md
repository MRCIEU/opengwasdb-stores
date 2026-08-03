# Release metadata schema

This document drafts the metadata files emitted by a Store Family Manifest
Generator for an accepted Store Release bundle.

OpenGWASDB owns the shared interpretation-bearing `analyses.tsv` core schema as
part of its store-format contract. This registry emits manifests that conform to
that core schema, while adding registry-only columns needed to locate source
inputs, audit release selection, and rebuild a Store Release.

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

Large release artifacts live outside this repository and should mirror the
Store Family and Release Bundle identity under the configured artifact root:

```text
<artifact-root>/<store-family-id>/releases/<family-release-id>/
```

## Pipeline stages

| Stage | Purpose | Typical inputs | Outputs |
|---|---|---|---|
| `discover` | Snapshot available upstream analyses and files. | Source inventory, GWAS Catalog studies table, source `meta.yaml`, provider APIs. | Raw candidate records and source-file locations. |
| `select` | Apply Store Family inclusion rules. | Candidate records, family config, priority lists, publication/analyte filters. | Selected Analysis set for a proposed Store Release. |
| `derive` | Add authoritative analytical metadata and generated evidence. | Selected rows, provider metadata resolvers, source files, OpenGWASDB readers, reference resources, Ensembl, checksums. | Resolved `analyses.tsv` columns and sidecar evidence. |
| `emit` | Write a reproducible release bundle. | Resolved rows, sidecars, build choices, generator provenance. | `release.yaml`, `analyses.tsv`, `build.yaml`, `validation.yaml`, sidecars. |
| `accept` | Check that the bundle is complete enough to build. | Release bundle, schema checks, lightweight source/readability checks. | Updated `validation.yaml` and release status. |

Metadata resolution and summary-statistics reading are orthogonal concerns. A
Source Collection chooses a provider-specific metadata resolver for study tables,
APIs, or endpoint manifests, and separately declares an OpenGWASDB Source Reader
Capability for source data. The resolved metadata shape is common even when the
provider and source format differ.

## Column classes

`analyses.tsv` spans three column classes:

| Class | Owner | Where used | Examples |
|---|---|---|---|
| Shared core | OpenGWASDB | Release manifests and built stores. These columns carry interpretation-bearing Analysis metadata. | `analysis_id`, `source_label`, ontology fields, ancestry fields, effect-scale fields, sample-size fields. |
| Registry-only | Store registry | Release manifests only. These columns locate source inputs, record provenance, or explain inclusion. | `source_analysis_id`, `source_file`, `source_bundle_id`, `checksum`, `checksum_algorithm`, `size_bytes`, `license`, publication metadata, `analysis_group_id`, `inclusion_reason`, `exclude_from_build`. |
| Store-only | OpenGWASDB | Built stores only. These columns are produced during or after the build and therefore do not appear in accepted release manifests. | `completed_against`, reference-completion quality rollups, store artifact diagnostics. |

Builders may ignore registry-only columns after using them to locate inputs.
Store-only columns must not be required before the build has run.

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
| `source_defaults.stored_effect_scale` | Yes | Default stored effect scale for OpenGWASDB when constant across the release: `sd`, `log_or`, or `log_hazard`. |
| `source_defaults.sample_size_kind` | Optional | Default sample-size kind if constant across the release. |
| `source_defaults.source_ancestry_label` | Optional | Default source ancestry label if constant across the release. |
| `source_defaults.assigned_ancestry` | Optional | Default assigned ancestry if constant across the release. |
| `lineage.derived_from` | Optional | Parent release ID or URI when this release derives from another release. |
| `sidecars.ancestry` | Optional | Path to ancestry evidence sidecar. |
| `sidecars.sd_estimation` | Optional | Path to phenotype-SD estimation evidence sidecar. |
| `sidecars.sparse_regions` | Optional | Path to sparse-region sidecar. |
| `sidecars.derivations` | Optional | Path to general derivation or curation sidecar. |
| `notes` | Optional | Free-text release notes. |

## `analyses.tsv`

One row per Analysis. Values should be resolved after applying `release.yaml`
defaults, even when that repeats store-level metadata. This includes fields that
are often constant across a store, such as stored effect scale and sample-size
semantics. The table should be streamable, diffable, and directly consumable by
builders.

Use empty strings for unknown optional values in TSV.

Accepted build rows must have usable sample-size metadata. Analyses with unknown
sample size may appear in Source Inventories, candidate diagnostics, or review
sidecars, but should not be included as buildable rows in an accepted
`analyses.tsv`.

Case/control-style counts are required when `stored_effect_scale = log_or` or
`stored_effect_scale = log_hazard`. For time-to-event traits, `n_cases` is the
event count and `n_controls` is the non-event or comparison count reported by
the source.

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
| `original_sd_method` | Yes | Controlled value describing `original_sd`: `declared_standardised`, `source_provided`, `estimated_from_source_maf`, `estimated_from_reference_maf`, `estimated_from_beta_distribution`, `binary_trait`, or `unavailable`. |
| `stored_effect_scale` | Yes | Controlled value for the effect scale stored by OpenGWASDB for this Analysis: `sd`, `log_or`, or `log_hazard`. |
| `sample_size_kind` | Yes | `total`, `case_control`, `effective`, or `variant_level`. Accepted build rows must not use `unknown`. |
| `sample_size_scope` | Yes | `analysis_level` or `variant_level`. Use `variant_level` when N differs per SNP in the source file. |
| `sample_size` | Yes | Scalar study N for this Analysis. When source N differs per SNP, use the study's maximum N. |
| `n_cases` | Optional | Case count for binary traits, or event count for time-to-event traits. Required when `stored_effect_scale = log_or` or `log_hazard`. |
| `n_controls` | Optional | Control count for binary traits, or non-event/comparison count for time-to-event traits when reported by the source. Required when `stored_effect_scale = log_or` or `log_hazard`. |
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
| `effects.stored_effect_scale` | Yes | Stored effect scale for the build: `sd`, `log_or`, or `log_hazard`. |
| `shape.association_coverage` | Yes | Repeats the release association coverage for builder convenience. |
| `shape.ragged_region_policy` | Optional | Named sparse-region policy for ragged releases. |
| `reference_resources` | Optional | List of reference resources used for completion, ancestry assignment, MAF lookup, or validation. |
| `validation.required` | Yes | Whether validation is required before publishing the built store. |
| `artifacts.artifact_root` | Optional | Configured root for large release artifacts outside this repository, such as `/data/opengwasdb`. |
| `artifacts.release_subdir` | Optional | Release-specific artifact directory relative to `artifacts.artifact_root`, conventionally `<store-family-id>/releases/<family-release-id>`. |
| `artifacts.filtered_dir` | Optional | Directory containing filtered source files used by the builder. |
| `artifacts.work_dir` | Optional | Directory for transient build/download files. |
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
| `checks.schema` | Yes | Whether required files and fields conform to OpenGWASDB's shared core schema and this registry's release-bundle requirements. |
| `checks.files` | Yes | Whether referenced source or filtered files exist and match checksums. |
| `checks.reader_smoke_test` | Optional | Whether OpenGWASDB can read a small sample from each source file or bundle. |
| `checks.ancestry` | Optional | Whether ancestry fields are valid and sidecar evidence is internally consistent. |
| `checks.effect_scale` | Optional | Whether original/stored effect-scale fields are valid and conversion inputs are present. |
| `checks.sd_estimation` | Optional | Whether SD-estimation fields and sidecar evidence are internally consistent. |
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
| `source_analysis_id` | Optional | Upstream analysis identifier, when the Source Collection provides one. |
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

## SD-estimation sidecar

Suggested path: `sidecars/sd_estimation.tsv`.

One row per Analysis where `original_sd_method` is an estimation method or where
source-provided/declared standardisation evidence should be auditable.

| Field | Required | Description |
|---|---:|---|
| `analysis_id` | Yes | Registry Analysis ID matching `analyses.tsv`. |
| `source_analysis_id` | Optional | Upstream analysis identifier, when the Source Collection provides one. |
| `original_sd` | Optional | Resolved phenotype SD written to `analyses.tsv`. |
| `original_sd_method` | Yes | Same controlled value as `analyses.tsv`. |
| `af_source` | Optional | `source`, `reference`, `assumed`, or empty when AF was not used. |
| `ancestry_reference_id` | Optional | Reference panel used for reference MAF, when applicable. |
| `n_variants_sampled` | Optional | Number of variants used by the estimator. |
| `maf_min` | Optional | Minimum MAF bound used for variant selection. |
| `maf_max` | Optional | Maximum MAF bound used for variant selection. |
| `variant_sampling_policy` | Optional | Description or ID for the random/common-variant sampling policy. |
| `sd_dispersion` | Optional | Dispersion diagnostic returned by the OpenGWASDB estimator. |
| `estimator_version` | Optional | OpenGWASDB estimator version, package version, or git commit. |
| `sd_notes` | Optional | Free-text notes for audit or review dashboards. |

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
