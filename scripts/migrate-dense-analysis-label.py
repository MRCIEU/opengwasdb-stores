#!/usr/bin/env python3
"""One-off migration adding `analysis_label` (ADR 0034, shared core) to the
already-built opengwas-gwas-vcf-dense (ukb-b) release bundles, which never
emitted it (PR #64 review finding). Mirrors `source_label` directly, matching
resources/generators/opengwas-gwas-vcf-dense/generate.R's emit_bundle() and
gwas-ssf-ragged's existing convention for Source Collections with no
separate curated display name.

Touches only the new column -- no other value changes.

Usage (already applied once; kept for reproducibility/audit, not part of the
regular build):

    python3 scripts/migrate-dense-analysis-label.py
"""
from __future__ import annotations

import csv

DENSE_BUNDLES = [
    "families/ukb-b/releases/dense-observed-vcf-c128/analyses.tsv",
    "families/ukb-b/releases/dense-observed-vcf-c128-resolved/analyses.tsv",
]


def migrate_bundle(path: str) -> None:
    with open(path, "rb") as fh:
        original_line_ending = "\r\n" if b"\r\n" in fh.readline() else "\n"

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fieldnames = list(reader.fieldnames or ())
        rows = list(reader)

    fieldnames.insert(fieldnames.index("source_label") + 1, "analysis_label")
    for row in rows:
        row["analysis_label"] = row["source_label"]

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, delimiter="\t", fieldnames=fieldnames, lineterminator=original_line_ending
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"migrated {path} ({len(rows)} rows)")


def main() -> None:
    for path in DENSE_BUNDLES:
        migrate_bundle(path)


if __name__ == "__main__":
    main()
