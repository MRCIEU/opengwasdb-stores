#!/usr/bin/env python3
"""One-off migration for already-accepted release bundles onto the
analyses.tsv shape opengwasdb's ADR 0034 promotes to shared core
(explodecomputer/opengwasdb#64, opengwasdb-stores#63): renames
`trait_ontology_name` to `trait_ontology_label`, and for `gwas-ssf-ragged`
bundles adds `analysis_label` (copied from the already-present `source_label`)
and `first_author` (joined by `analysis_id` against
resources/data/derived/store-candidates-analyses.tsv's `FIRST.AUTHOR`,
matching resources/generators/gwas-ssf-ragged/generate.R's manifest_rows()
column order).

Deliberately does not touch `checksum`/`size_bytes` or any other column --
re-running the generator's own `--mode=emit` would reset those to blank
pending a fresh `--mode=filter`, destroying already-recorded filter
provenance for these accepted bundles, so this script edits the checked-in
TSV directly instead of regenerating through generate.R.

Usage (already applied once; kept for reproducibility/audit, not part of the
regular build):

    python3 scripts/migrate-analyses-tsv-adr-0034.py
"""
from __future__ import annotations

import csv
import glob

CANDIDATES_PATH = "resources/data/derived/store-candidates-analyses.tsv"

RAGGED_BUNDLES = [
    "families/pqtl-interval-2018/releases/2018-sun-pilot-100/analyses.tsv",
    *sorted(glob.glob("families/metabolome-plasma-2023/releases/*/analyses.tsv")),
]

DENSE_BUNDLES = [
    "families/ukb-b/releases/dense-observed-vcf-c128/analyses.tsv",
    "families/ukb-b/releases/dense-observed-vcf-c128-resolved/analyses.tsv",
]


def load_first_author_by_id(path: str) -> dict[str, str]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return {row["STUDY.ACCESSION"]: row["FIRST.AUTHOR"] for row in reader}


def migrate_ragged_bundle(path: str, first_author_by_id: dict[str, str]) -> None:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fieldnames = list(reader.fieldnames or ())
        rows = list(reader)

    fieldnames[fieldnames.index("trait_ontology_name")] = "trait_ontology_label"
    for row in rows:
        row["trait_ontology_label"] = row.pop("trait_ontology_name")

    fieldnames.insert(fieldnames.index("source_label") + 1, "analysis_label")
    fieldnames.insert(fieldnames.index("consortium") + 1, "first_author")
    for row in rows:
        row["analysis_label"] = row["source_label"]
        row["first_author"] = first_author_by_id.get(row["analysis_id"], "")

    missing = [row["analysis_id"] for row in rows if not row["first_author"]]
    if missing:
        raise SystemExit(f"{path}: no FIRST.AUTHOR match for {missing}")

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"migrated {path} ({len(rows)} rows)")


def migrate_dense_bundle_header_only(path: str) -> None:
    with open(path, "rb") as fh:
        original_line_ending = "\r\n" if b"\r\n" in fh.readline() else "\n"

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fieldnames = list(reader.fieldnames or ())
        rows = list(reader)

    fieldnames[fieldnames.index("trait_ontology_name")] = "trait_ontology_label"
    for row in rows:
        row["trait_ontology_label"] = row.pop("trait_ontology_name")

    # Preserve the file's existing line-ending convention (issue #63 review
    # caught dense-observed-vcf-c128/analyses.tsv is CRLF, unlike every other
    # release bundle) rather than csv's LF default silently normalising it.
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, delimiter="\t", fieldnames=fieldnames, lineterminator=original_line_ending
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"migrated (header-only) {path} ({len(rows)} rows)")


def main() -> None:
    first_author_by_id = load_first_author_by_id(CANDIDATES_PATH)
    for path in RAGGED_BUNDLES:
        migrate_ragged_bundle(path, first_author_by_id)
    for path in DENSE_BUNDLES:
        migrate_dense_bundle_header_only(path)


if __name__ == "__main__":
    main()
