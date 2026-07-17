# opengwasdb-stores

Registry and orchestration metadata for building many OpenGWASDB store releases.

This repository records what stores should exist, what source inputs define them,
how releases were produced, and what should be built next. It does not implement
OpenGWASDB source readers, normalisation, storage layouts, or query engines.

## Model

The core flow is:

```text
Source Collection
  -> Store Family
  -> Manifest Generator
  -> Release Manifest bundle
  -> Build Recipe
  -> Store Release
```

- A Source Collection is a homogeneous upstream summary-statistics inventory
  with one source format and one OpenGWASDB reader capability.
- A Store Family is a stable product identity built from one Source Collection.
  One Source Collection may feed many Store Families, but a Store Family does
  not combine multiple Source Collections.
- A Manifest Generator is Store Family-specific orchestration code that selects
  inputs from the family's Source Collection and emits a candidate release.
- A Release Manifest bundle is a self-contained directory containing release
  metadata, a concrete analysis table, a build recipe, and validation summary.
- A Build Recipe records the release shape, such as dense versus ragged and
  observed-only versus reference-completed.
- A Store Release is the immutable, validated OpenGWASDB analytical asset
  produced from the accepted release bundle.

## Repository Layout

```text
CONTEXT.md
docs/adr/
source-collections/
reference-resources/
families/
annotations/
```

- `CONTEXT.md` defines the project language.
- `docs/adr/` records design decisions that should not be rediscovered.
- `source-collections/` records upstream summary-statistics inventories.
- `reference-resources/` records auxiliary build-time resources such as LD
  panels and genome references.
- `families/` records Store Families, release bundles, generators, priorities,
  validation summaries, and errata.
- `annotations/` records curated metadata that can evolve independently from
  immutable store releases, such as Trait Annotations.

## Release Bundles

Each release lives under:

```text
families/<store-family-id>/releases/<family-release-id>/
```

Each release bundle should contain:

```text
release.yaml
analyses.tsv
build.yaml
validation.yaml
```

`release.yaml` records release identity, status, source collection, association
coverage, and lineage. `analyses.tsv` lists the concrete Analyses, Traits,
source files, checksums, license, compact publication metadata, ancestry, effect
scale, and sample-size metadata. `build.yaml` records the concrete build shape
and OpenGWASDB builder entry point. `validation.yaml` summarises validation
status and points to any detailed reports.

The draft field-level schema for these files, including sidecars for ancestry
assignment and ragged sparse-region evidence, is recorded in
`docs/release-metadata-schema.md`.

The repository stores metadata and small reports only. Store artifacts, source
data, large logs, and large benchmark outputs belong outside this repository and
should be referenced by URI when needed.

## Example

The initial worked example is:

```text
source-collections/opengwas-gwas-vcf/
families/ukb-b/
families/ukb-b/releases/2018-ieu/
```

It models the IEU OpenGWAS `ukb-b` batch as a dense observed-only candidate
release built from the `opengwas-gwas-vcf` Source Collection.
