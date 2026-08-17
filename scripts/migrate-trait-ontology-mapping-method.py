#!/usr/bin/env python3
"""One-off migration adding the new registry-only `trait_ontology_mapping_method`
column (see docs/release-metadata-schema.md, "Trait ontology mapping resolver",
and docs/adr/0021-trait-ontology-mapping-lookup-lives-in-registry.md) to every
already-built release bundle, mirroring what
resources/generators/gwas-ssf-ragged/generate.R and
resources/generators/opengwas-gwas-vcf-dense/generate.R now emit for newly
generated manifests.

`gwas-ssf-ragged` bundles: every row already has a non-blank trait_ontology_id
(GWAS Catalog's own MAPPED_TRAIT_URI), so every row gets `source_provided`.

`opengwas-gwas-vcf-dense` (ukb-b) bundles: trait_ontology_id is blank for
every row (no Canonical Trait Mapping Table entry exists for any ukb-b trait
label yet), so every row gets `unmapped` -- an explicit, auditable statement
rather than a silently absent column.

Touches only the new column -- no other value changes.

Usage (already applied once; kept for reproducibility/audit, not part of the
regular build):

    python3 scripts/migrate-trait-ontology-mapping-method.py
"""
from __future__ import annotations

import csv
import glob

RAGGED_BUNDLES = [
    "families/pqtl-interval-2018/releases/2018-sun-pilot-100/analyses.tsv",
    *sorted(glob.glob("families/metabolome-plasma-2023/releases/*/analyses.tsv")),
]

DENSE_BUNDLES = [
    "families/ukb-b/releases/dense-observed-vcf-c128/analyses.tsv",
    "families/ukb-b/releases/dense-observed-vcf-c128-resolved/analyses.tsv",
]


def migrate_bundle(path: str, method_for_row) -> None:
    with open(path, "rb") as fh:
        original_line_ending = "\r\n" if b"\r\n" in fh.readline() else "\n"

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fieldnames = list(reader.fieldnames or ())
        rows = list(reader)

    fieldnames.insert(fieldnames.index("trait_ontology_id") + 1, "trait_ontology_mapping_method")
    for row in rows:
        row["trait_ontology_mapping_method"] = method_for_row(row)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, delimiter="\t", fieldnames=fieldnames, lineterminator=original_line_ending
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"migrated {path} ({len(rows)} rows)")


def main() -> None:
    for path in RAGGED_BUNDLES:
        migrate_bundle(path, lambda row: "source_provided" if row["trait_ontology_id"] else "unmapped")
    for path in DENSE_BUNDLES:
        migrate_bundle(path, lambda row: "source_provided" if row["trait_ontology_id"] else "unmapped")


if __name__ == "__main__":
    main()
