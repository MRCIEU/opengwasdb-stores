#!/usr/bin/env python3
"""One-off migration converting already-built gwas-ssf-ragged bundles'
`trait_ontology_id` values from full OBO Library PURLs (e.g.
http://www.ebi.ac.uk/efo/EFO_0008012, http://purl.obolibrary.org/obo/OBA_2050236)
to CURIE format (EFO:0008012, OBA:2050236), per docs/release-metadata-schema.md
and the same conversion resources/generators/gwas-ssf-ragged/generate.R's
obo_uri_to_curie() applies to newly generated manifests.

Only `gwas-ssf-ragged` bundles need this: `opengwas-gwas-vcf-dense` (ukb-b)
bundles have no trait_ontology_id values at all yet (blank for every row).

Touches only `trait_ontology_id` -- no other column.

Usage (already applied once; kept for reproducibility/audit, not part of the
regular build):

    python3 scripts/migrate-trait-ontology-curie.py
"""
from __future__ import annotations

import csv
import glob
import re

RAGGED_BUNDLES = [
    "families/pqtl-interval-2018/releases/2018-sun-pilot-100/analyses.tsv",
    *sorted(glob.glob("families/metabolome-plasma-2023/releases/*/analyses.tsv")),
]


def obo_uri_to_curie(value: str) -> str:
    if not value or "/" not in value:
        return value
    segment = value.rsplit("/", 1)[-1]
    prefix, _, local_id = segment.rpartition("_")
    if not prefix:
        return value
    return f"{prefix.upper()}:{local_id}"


def migrate_bundle(path: str) -> None:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fieldnames = list(reader.fieldnames or ())
        rows = list(reader)

    for row in rows:
        row["trait_ontology_id"] = obo_uri_to_curie(row["trait_ontology_id"])

    non_curie = [
        row["trait_ontology_id"]
        for row in rows
        if row["trait_ontology_id"] and not re.match(r"^[A-Za-z]+:\w+$", row["trait_ontology_id"])
    ]
    if non_curie:
        raise SystemExit(f"{path}: values that still aren't CURIE-shaped: {non_curie}")

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"migrated {path} ({len(rows)} rows)")


def main() -> None:
    for path in RAGGED_BUNDLES:
        migrate_bundle(path)


if __name__ == "__main__":
    main()
