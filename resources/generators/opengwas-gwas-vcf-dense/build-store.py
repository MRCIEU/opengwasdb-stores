#!/usr/bin/env python3
"""Build and smoke-query a dense opengwas-gwas-vcf release bundle with
OpenGWASDB. Structured like resources/generators/gwas-ssf-ragged/build-store.py,
but simpler: dense has no sparse-region sidecar to cross-check against, so
the read-back just queries one known Analysis and confirms finite
association statistics plus correct passthrough Analytical Metadata.

opengwasdb.layouts.dense.build_vcf.build_dense_from_vcf_manifest() requires
its own manifest column names (trait_id/file_path/trait_name/n --
OpenGWASDB's older internal convention), distinct from this registry's
analyses.tsv (analysis_id/source_file/analysis_label/sample_size). This
script's whole job is that translation -- see the field-by-field mapping in
main() below.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from resources.lib.release_yaml import (  # noqa: E402
    merge_validation_yaml,
    read_release_yaml,
    read_tsv,
    repo_root,
    require_text,
    resolve_path,
)

from opengwasdb.layouts.dense.build_vcf import build_dense_from_vcf_manifest
from opengwasdb.query import query_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--store-dir")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def write_builder_manifest(rows: list[dict[str, str]], out_path: Path) -> None:
    """Translate this registry's analyses.tsv column names into the shape
    opengwasdb.layouts.dense.build_vcf._read_manifest() actually requires."""
    fieldnames = [
        "trait_id", "file_path", "trait_name", "n", "stored_effect_scale",
        "original_sd_method", "original_sd", "assigned_ancestry",
        "trait_ontology_id", "trait_ontology_label",
        "license", "publication_doi", "publication_pmid", "consortium", "first_author",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "trait_id": row["analysis_id"],
                "file_path": row["source_file"],
                "trait_name": row["analysis_label"],
                "n": row["sample_size"],
                "stored_effect_scale": row["stored_effect_scale"],
                "original_sd_method": row["original_sd_method"],
                "original_sd": row.get("original_sd", ""),
                "assigned_ancestry": row.get("assigned_ancestry", ""),
                "trait_ontology_id": row.get("trait_ontology_id", ""),
                "trait_ontology_label": row.get("trait_ontology_label", ""),
                "license": row.get("license", ""),
                "publication_doi": row.get("publication_doi", ""),
                "publication_pmid": row.get("publication_pmid", ""),
                "consortium": row.get("consortium", ""),
                "first_author": row.get("first_author", ""),
            })


def main() -> None:
    args = parse_args()
    release_dir = Path(args.release_dir).resolve()
    root = repo_root(release_dir)
    release = read_release_yaml(release_dir / "release.yaml")
    build = read_release_yaml(release_dir / "build.yaml")
    rows = read_tsv(release_dir / "analyses.tsv")

    store_dir = (
        Path(args.store_dir).resolve()
        if args.store_dir
        else resolve_path(root, require_text(build, "artifacts", "store_uri"))
    )

    with tempfile.TemporaryDirectory() as tmp:
        builder_manifest_path = Path(tmp) / "manifest.tsv"
        write_builder_manifest(rows, builder_manifest_path)
        result = build_dense_from_vcf_manifest(
            builder_manifest_path,
            store_dir,
            store_id=require_text(release, "store_family_id"),
            release_id=require_text(release, "family_release_id"),
            overwrite=args.overwrite,
        )

    # Read-back: query one known Analysis and confirm finite association
    # statistics, plus that the *resolved* stored_effect_scale (not a
    # VCF-header re-derivation -- opengwasdb#14) and passthrough
    # Analytical Metadata (analysis_label, ADR 0034) actually made it in.
    probe_id = rows[0]["analysis_id"]
    query = query_store(store_dir)
    try:
        assoc = query.analysis(probe_id, observed_only=True)
        analyses_table = query.analyses_table()
    finally:
        query.close()

    n_finite = int(sum(1 for z in assoc["z"] if z == z and abs(z) < float("inf")))
    store_by_id = {r["analysis_id"]: r for r in analyses_table.values()}
    probe_row = store_by_id[probe_id]

    report = {
        "store_uri": str(store_dir),
        "n_analyses": result.n_analyses,
        "n_variants": result.n_variants,
        "probe_analysis_id": probe_id,
        "probe_n_associations": len(assoc["z"]),
        "probe_n_finite_z": n_finite,
        "probe_stored_effect_scale": probe_row.get("stored_effect_scale"),
        "probe_analysis_label": probe_row.get("analysis_label"),
        "probe_trait_ontology_mapping_method": next(
            r["trait_ontology_mapping_method"] for r in rows if r["analysis_id"] == probe_id
        ),
    }
    warnings = []
    if n_finite == 0:
        warnings.append(f"{probe_id}: zero finite association statistics in built store")

    # Confirm shared-core columns the manifest actually populated (resolved
    # stored_effect_scale -- opengwasdb#14 -- plus analysis_label/
    # trait_ontology_id/label, ADR 0034) made it into the built store's own
    # analyses.tsv for every Analysis, not just the probe. Dense's builder is
    # documented to carry these through (unlike Ragged's -- opengwasdb#83),
    # but confirm it rather than assume it.
    for row in rows:
        store_row = store_by_id.get(row["analysis_id"], {})
        if store_row.get("stored_effect_scale") != row["stored_effect_scale"]:
            warnings.append(
                f"{row['analysis_id']}: built store stored_effect_scale="
                f"{store_row.get('stored_effect_scale')!r} != manifest-resolved "
                f"{row['stored_effect_scale']!r}"
            )
        for column in ("analysis_label", "trait_ontology_id", "trait_ontology_label"):
            if row.get(column) and not store_row.get(column):
                warnings.append(
                    f"{row['analysis_id']}: {column} present in the manifest but missing from "
                    "the built store's analyses.tsv"
                )

    report_path = release_dir / "sidecars" / "build_report.tsv"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=list(report), lineterminator="\n")
        writer.writeheader()
        writer.writerow(report)

    build_status = "passed_with_warnings" if warnings else "passed"
    merge_validation_yaml(
        release_dir / "validation.yaml",
        validator_name="resources/generators/opengwas-gwas-vcf-dense/build-store.py",
        updated_checks={"schema": "passed", "files": build_status, "reader_smoke_test": build_status},
        updated_reports={"build_report": str(report_path.relative_to(release_dir))},
        new_warnings=warnings,
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
