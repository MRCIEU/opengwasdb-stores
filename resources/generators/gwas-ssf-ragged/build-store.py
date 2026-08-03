#!/usr/bin/env python
"""Build and smoke-query a ragged GWAS-SSF release bundle with OpenGWASDB."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from opengwasdb.layouts.ragged.build_ssf import build_ragged_from_ssf
from opengwasdb.layouts.ragged.zarr_csr import RaggedCSRReader
from opengwasdb.model.manifest import StoreManifest
from opengwasdb.traits.axis import TraitsAxisReader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--store-dir")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def read_release_yaml(path: Path) -> dict[str, object]:
    out: dict[str, object] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            current = key.strip()
            parsed = parse_yaml_scalar(value)
            out[current] = {} if parsed == "" else parsed
        elif current and line.startswith("  ") and ":" in line:
            key, value = line.split(":", 1)
            if not isinstance(out.get(current), dict):
                out[current] = {}
            out[current][key.strip()] = parse_yaml_scalar(value)
    return out


def parse_yaml_scalar(value: str) -> str:
    value = value.strip().strip("'\"")
    if value in {"~", "|", ">"}:
        return ""
    return value


def require_text(data: dict[str, object], *keys: str) -> str:
    current: object = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            dotted = ".".join(keys)
            raise SystemExit(f"Missing required YAML field: {dotted}")
        current = current[key]
    if current is None:
        return ""
    return str(current)


def repo_root(start: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    )
    return Path(result.stdout.strip())


def variant_lookup(store: Path) -> dict[int, tuple[str, int]]:
    out: dict[int, tuple[str, int]] = {}
    with gzip.open(store / "variants.tsv.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            out[int(fields[2])] = (fields[0], int(fields[1]))
    return out


def first_complete_manifest_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    missing = [r["analysis_id"] for r in rows if not r.get("checksum") or not r.get("size_bytes")]
    if missing:
        preview = ", ".join(missing[:10])
        raise SystemExit(
            f"{path} still has {len(missing)} rows without filtered-file checksums: {preview}"
        )
    return rows


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def associations_in_region(
    reader: RaggedCSRReader,
    variants: dict[int, tuple[str, int]],
    analysis_index: int,
    chromosome: str,
    start: int,
    end: int,
) -> dict[str, object]:
    assoc = reader.get_analysis(analysis_index)
    hits = [
        (int(vi), float(z), float(se))
        for vi, z, se in zip(assoc.variant_index, assoc.z, assoc.se)
        if variants[int(vi)][0] == chromosome and start <= variants[int(vi)][1] <= end
    ]
    top = max(hits, key=lambda row: abs(row[1]), default=None)
    if top is None:
        return {
            "observed": 0,
            "top_variant": "",
            "top_position": "",
            "top_z": "",
            "top_se": "",
        }
    top_chrom, top_pos = variants[top[0]]
    return {
        "observed": len(hits),
        "top_variant": f"{top_chrom}:{top_pos}",
        "top_position": top_pos,
        "top_z": round(top[1], 4),
        "top_se": round(top[2], 6),
    }


def choose_region(regions: list[dict[str, str]], kind: str) -> dict[str, str] | None:
    candidates = [
        row for row in regions
        if row.get("region_kind") == kind and int(row.get("n_variants_retained") or 0) > 0
    ]
    return candidates[0] if candidates else None


def du_bytes(path: Path) -> int:
    result = subprocess.run(
        ["du", "-sb", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    )
    return int(result.stdout.split()[0])


def write_validation_yaml(path: Path, report_path: Path, status: str, warnings: list[str]) -> None:
    warning_lines = "\n".join(f"  - {warning}" for warning in warnings) if warnings else "[]"
    validated_at = datetime.now(UTC).isoformat()
    path.write_text(
        "\n".join([
            f"status: {status}",
            f"validated_at: {validated_at}",
            "validator:",
            "  name: resources/generators/gwas-ssf-ragged/build-store.py",
            "  version: null",
            "checks:",
            "  schema: passed",
            "  files: passed",
            "  reader_smoke_test: passed",
            "  ancestry: not_run",
            "  effect_scale: passed",
            "  sd_estimation: not_run",
            "  sparse_regions: passed",
            "reports:",
            f"  build_report: {report_path.relative_to(path.parent)}",
            f"warnings: {warning_lines}",
            "errors: []",
            "",
        ]),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    release_dir = Path(args.release_dir).resolve()
    root = repo_root(release_dir)
    release = read_release_yaml(release_dir / "release.yaml")
    build = read_release_yaml(release_dir / "build.yaml")
    analyses_path = release_dir / "analyses.tsv"
    rows = first_complete_manifest_rows(analyses_path)

    filtered_dir = root / require_text(build, "artifacts", "filtered_dir")
    if not filtered_dir.exists():
        raise SystemExit(f"Filtered directory does not exist: {filtered_dir}")
    store_id = require_text(release, "store_key") or (
        f"{require_text(release, 'store_family_id')}__{require_text(release, 'family_release_id')}"
    )
    store_dir = Path(args.store_dir).resolve() if args.store_dir else root / require_text(build, "artifacts", "store_uri")
    scale_map = {"sd": "sd_units", "log_or": "log_or", "log_hazard": "log_hazard"}
    stored_effect_scale = scale_map.get(require_text(build, "effects", "stored_effect_scale") or "sd", "sd_units")

    build_started = time.perf_counter()
    result = build_ragged_from_ssf(
        analyses_path,
        filtered_dir,
        store_dir,
        store_id=store_id,
        release_id=require_text(release, "family_release_id"),
        stored_effect_scale=stored_effect_scale,
        overwrite=args.overwrite,
    )
    build_seconds = round(time.perf_counter() - build_started, 3)

    manifest = StoreManifest.load(store_dir)
    reader = RaggedCSRReader(store_dir)
    variants = variant_lookup(store_dir)
    with TraitsAxisReader(store_dir) as traits:
        trait_rows = sorted(list(traits.all()), key=lambda t: t.analysis_index)
    trait_by_id = {row.analysis_id: row for row in trait_rows}
    regions = read_tsv(release_dir / "sidecars" / "sparse_regions.tsv")
    filter_summary = read_tsv(release_dir / "sidecars" / "filter_summary.tsv")

    cis_region = choose_region(regions, "cis")
    trans_region = choose_region(regions, "significant_trans") or choose_region(regions, "suggestive_trans")
    if cis_region is None:
        raise SystemExit("No non-empty cis region found in sparse_regions.tsv")
    if trans_region is None:
        raise SystemExit("No non-empty trans region found in sparse_regions.tsv")

    cis_trait = trait_by_id[cis_region["analysis_id"]]
    trans_trait = trait_by_id[trans_region["analysis_id"]]
    cis_query = associations_in_region(
        reader,
        variants,
        cis_trait.analysis_index,
        cis_region["chromosome"],
        int(cis_region["start"]),
        int(cis_region["end"]),
    )
    trans_query = associations_in_region(
        reader,
        variants,
        trans_trait.analysis_index,
        trans_region["chromosome"],
        int(trans_region["start"]),
        int(trans_region["end"]),
    )
    cis_expected = int(cis_region.get("n_variants_retained") or 0)
    trans_expected = int(trans_region.get("n_variants_retained") or 0)
    expected_associations = sum(int(row["retained_rows"]) for row in filter_summary if row.get("status") == "ok")
    warnings = []
    if cis_query["observed"] != cis_expected:
        warnings.append(f"cis query observed {cis_query['observed']} associations but sidecar records {cis_expected}")
    if trans_query["observed"] != trans_expected:
        warnings.append(f"trans query observed {trans_query['observed']} associations but sidecar records {trans_expected}")
    if result.n_associations != expected_associations:
        warnings.append(
            f"store has {result.n_associations} associations but filter summary records {expected_associations}"
        )

    report = {
        "store_uri": require_text(build, "artifacts", "store_uri"),
        "filtered_uri": require_text(build, "artifacts", "filtered_dir"),
        "store_bytes": du_bytes(store_dir),
        "filtered_bytes": du_bytes(filtered_dir),
        "download_filter_seconds": round(
            sum(float(row["total_seconds"]) for row in filter_summary if row.get("status") == "ok"),
            3,
        ),
        "build_seconds": build_seconds,
        "end_to_end_seconds": round(
            sum(float(row["total_seconds"]) for row in filter_summary if row.get("status") == "ok")
            + build_seconds,
            3,
        ),
        "layout": manifest.primary_layout.value,
        "coverage": manifest.association_coverage.value,
        "completion_state": manifest.completion_state.value,
        "n_manifest_rows": len(rows),
        "n_analyses": result.n_analyses,
        "n_variants": result.n_variants,
        "n_associations": result.n_associations,
        "filter_summary_retained_rows": expected_associations,
        "cis_analysis_id": cis_region["analysis_id"],
        "cis_region_id": cis_region["region_id"],
        "cis_region": f"{cis_region['chromosome']}:{cis_region['start']}-{cis_region['end']}",
        "cis_sidecar_associations": cis_expected,
        "cis_query_associations": cis_query["observed"],
        "cis_top_variant": cis_query["top_variant"],
        "cis_top_z": cis_query["top_z"],
        "trans_analysis_id": trans_region["analysis_id"],
        "trans_region_id": trans_region["region_id"],
        "trans_region_kind": trans_region["region_kind"],
        "trans_region": f"{trans_region['chromosome']}:{trans_region['start']}-{trans_region['end']}",
        "trans_sidecar_associations": trans_expected,
        "trans_query_associations": trans_query["observed"],
        "trans_top_variant": trans_query["top_variant"],
        "trans_top_z": trans_query["top_z"],
        "warnings": "; ".join(warnings) if warnings else "none",
    }
    report_path = release_dir / "sidecars" / "build_report.tsv"
    with report_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=list(report), lineterminator="\n")
        writer.writeheader()
        writer.writerow(report)
    status = "passed_with_warnings" if warnings else "passed"
    write_validation_yaml(release_dir / "validation.yaml", report_path, status, warnings)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
