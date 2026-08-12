#!/usr/bin/env python3
"""One-pass AF-based ancestry and phenotype-SD annotation for dense GWAS-VCF releases."""
from __future__ import annotations

import argparse
import csv
import gzip
import math
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from opengwasdb.ancestry import Gates, assign_ancestry, load_reference
from opengwasdb.build.phenotype_sd import estimate_phenotype_sd
from opengwasdb.model.enums import OriginalSdMethod
from opengwasdb.readers import GwasVcfReader, load_liftover, write_regions_file

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from resources.lib.release_yaml import get, merge_validation_yaml, read_release_yaml, resolve_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--only-analysis-id", default="")
    parser.add_argument("--source-dir", default="", help="Override source_file by analysis_id.vcf.gz")
    return parser.parse_args()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def find_resource(build: dict, resource_id: str) -> dict:
    for resource in build.get("reference_resources") or []:
        if resource.get("resource_id") == resource_id:
            return resource
    raise SystemExit(f"No reference resource {resource_id!r} in build.yaml")


def _snp_from_alid(alid: str) -> tuple[str, str, str] | None:
    fields = alid.split(":")
    if len(fields) != 4 or len(fields[2]) != 1 or len(fields[3]) != 1:
        return None
    return fields[0], fields[2].upper(), fields[3].upper()


def make_reference_subset(source: Path, destination: Path, chromosome: str, max_sites: int) -> None:
    """Stream a deterministic SNP subset; OpenGWASDB remains the reference parser."""
    opener = gzip.open if str(source).endswith(".gz") else open
    with opener(source, "rt", newline="", encoding="utf-8") as src, destination.open(
        "w", newline="", encoding="utf-8"
    ) as dst:
        reader = csv.reader(src, delimiter="\t")
        writer = csv.writer(dst, delimiter="\t", lineterminator="\n")
        header = next(reader)
        writer.writerow(header)
        alid_index = header.index("alid")
        kept = 0
        for row in reader:
            parsed = _snp_from_alid(row[alid_index])
            if parsed is None:
                continue
            chrom, a1, a2 = parsed
            if chrom != chromosome or {a1, a2} in ({"A", "T"}, {"C", "G"}):
                continue
            writer.writerow(row)
            kept += 1
            if kept >= max_sites:
                break
    if kept < 2:
        raise SystemExit(f"Reference subset contains only {kept} usable sites")


def finite_float(value: str) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def overall_check(statuses: list[str]) -> str:
    if not statuses:
        return "not_run"
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses or "skipped" in statuses:
        return "passed_with_warnings"
    return "passed"


def main() -> None:
    args = parse_args()
    release_dir = Path(args.release_dir).resolve()
    build = read_release_yaml(release_dir / "build.yaml")
    ancestry_cfg = get(build, "ancestry_assignment", default={})
    effect_cfg = get(build, "effect_scale_validation", default={})
    if not isinstance(ancestry_cfg, dict) or not ancestry_cfg.get("enabled"):
        raise SystemExit("build.yaml has no enabled ancestry_assignment config")
    if not isinstance(effect_cfg, dict) or not effect_cfg.get("enabled"):
        raise SystemExit("build.yaml has no enabled effect_scale_validation config")

    resource_id = str(ancestry_cfg["reference_resource_id"])
    resource = find_resource(build, resource_id)
    chromosome = str(ancestry_cfg.get("sampling_chromosome", "1"))
    max_sites = int(ancestry_cfg.get("max_reference_sites", 20000))
    maf_floor = float(ancestry_cfg.get("maf_floor", 0.01))
    root = Path(__file__).resolve().parents[3]
    reference_path = resolve_path(root, str(resource["location"]))
    groups_path = resolve_path(root, str(resource["fine_group_map"]))

    gates_cfg = ancestry_cfg.get("gates") if isinstance(ancestry_cfg.get("gates"), dict) else {}
    gates = Gates(
        tau=float(gates_cfg.get("tau", 0.50)), delta=float(gates_cfg.get("delta", 0.20)),
        n_min=int(gates_cfg.get("n_min", 5000)), residual_max=float(gates_cfg.get("residual_max", 0.06)),
    )
    chain = get(build, "normalisation", "liftover_chain", default=None)
    liftover = load_liftover(chain_file=str(resolve_path(root, str(chain)))) if chain else None

    analyses_path = release_dir / "analyses.tsv"
    analyses = read_tsv(analyses_path)
    requested = {x for x in args.only_analysis_id.split(",") if x}
    selected = [row for row in analyses if not requested or row["analysis_id"] in requested]
    if not selected:
        raise SystemExit("No analyses selected")

    try:
        estimator_version = f"opengwasdb:{version('opengwasdb')}"
    except PackageNotFoundError:
        estimator_version = "opengwasdb:unknown"

    ancestry_rows: list[dict[str, object]] = []
    sd_rows: list[dict[str, object]] = []
    ancestry_statuses: list[str] = []
    sd_statuses: list[str] = []
    warnings: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        subset_path = Path(tmp) / "ancestry-reference-subset.tsv"
        make_reference_subset(reference_path, subset_path, chromosome, max_sites)
        reference = load_reference(subset_path, groups_path, maf_floor=maf_floor)
        regions_file = None
        if liftover is None:
            regions_file = write_regions_file(reference.index.keys(), Path(tmp) / "regions.tsv")

        for row in selected:
            source_path = (
                Path(args.source_dir).resolve() / f"{row['analysis_id']}.vcf.gz"
                if args.source_dir else Path(row["source_file"])
            )
            if not source_path.exists():
                raise SystemExit(f"Source VCF does not exist: {source_path}")
            reader = GwasVcfReader(
                source_path, liftover=liftover, regions_file=regions_file,
                region=chromosome if liftover is not None else None,
            )
            metrics = reader.extract_at_sites(reference.index.keys())
            study_af = {alid: metric.af for alid, metric in metrics.items()}
            assignment = assign_ancestry(study_af, reference, gates)
            ancestry_status = "passed" if assignment.gate_reason == "ok" else "warning"
            ancestry_statuses.append(ancestry_status)
            assigned = assignment.assigned_ancestry or ""
            row["assigned_ancestry"] = assigned
            row["ancestry_assignment_method"] = "af_assigned" if assigned else "unassigned"
            if not assigned:
                warnings.append(f"{row['analysis_id']}: ancestry gate failed ({assignment.gate_reason})")
            ancestry_row: dict[str, object] = {
                "analysis_id": row["analysis_id"], "source_analysis_id": row.get("source_analysis_id", row["analysis_id"]),
                "source_ancestry_label": row.get("source_ancestry_label", ""), "assigned_ancestry": assigned,
                "ancestry_assignment_method": row["ancestry_assignment_method"], "ancestry_reference_id": resource_id,
                "af_overlap": assignment.af_overlap, "dominant_superpop": assignment.dominant_superpop or "",
                "dominant_proportion": assignment.dominant_proportion, "runner_up_margin": assignment.runner_up_margin,
                "nnls_residual": assignment.residual, "gate_reason": assignment.gate_reason,
                "source_assigned_mismatch": "", "ancestry_notes": "one-pass GWAS-VCF AF/SE extraction",
            }
            for superpop in reference.superpops:
                ancestry_row[f"ancestry_prop_{superpop}"] = assignment.superpop_composition.get(superpop, 0.0)
            ancestry_rows.append(ancestry_row)

            scale = row.get("stored_effect_scale", "")
            sample_size = finite_float(row.get("sample_size", ""))
            if scale in {"log_or", "log_hazard"}:
                sd_status, skip_reason, estimate = "skipped", "non_quantitative_effect_scale", None
            elif sample_size is None or not metrics:
                sd_status, skip_reason, estimate = "skipped", "no_usable_site_metrics", None
            else:
                af = np.asarray([metric.af for metric in metrics.values()], dtype=float)
                se = np.asarray([metric.se for metric in metrics.values()], dtype=float)
                estimate = estimate_phenotype_sd(
                    OriginalSdMethod.ESTIMATED_FROM_SOURCE_MAF, sample_size, se=se, af=af
                )
                min_sites = int(effect_cfg.get("min_overlap_variants", 20))
                if estimate.method is OriginalSdMethod.UNAVAILABLE or len(metrics) < min_sites:
                    sd_status, skip_reason = "skipped", "low_overlap"
                elif row.get("original_sd_method") == "declared_standardised":
                    tolerance = float(effect_cfg.get("sd_tolerance", 0.15))
                    delta = abs(estimate.sd - 1.0)
                    sd_status = "passed" if delta <= tolerance else "warning" if delta <= tolerance * 2 else "failed"
                    skip_reason = ""
                else:
                    sd_status, skip_reason = "passed", ""
                    row["original_sd"] = str(estimate.sd)
                    row["original_sd_method"] = estimate.method.value
            sd_statuses.append(sd_status)
            if sd_status in {"warning", "failed"}:
                warnings.append(f"{row['analysis_id']}: empirical effect-scale status={sd_status}")
            sd_rows.append({
                "analysis_id": row["analysis_id"], "source_analysis_id": row.get("source_analysis_id", row["analysis_id"]),
                "status": sd_status, "skip_reason": skip_reason, "af_source": "source" if estimate else "",
                "ancestry_reference_id": "", "original_sd": row.get("original_sd", ""),
                "original_sd_method": row.get("original_sd_method", ""), "n_variants_considered": reference.n_variants,
                "n_variants_overlapping": len(metrics), "n_variants_excluded_ambiguous": "",
                "n_variants_excluded_mismatch": "", "n_variants_excluded_missing_af": reference.n_variants - len(metrics),
                "n_variants_excluded_maf": 0, "n_variants_retained": len(metrics),
                "maf_min": maf_floor, "maf_max": 0.5,
                "implied_sd_median": estimate.sd if estimate else "",
                "sd_dispersion": estimate.dispersion if estimate else "",
                "sd_notes": estimate.notes or "one-pass source-AF estimate" if estimate else skip_reason,
                "estimator_version": estimator_version,
            })

    write_tsv(analyses_path, analyses, list(analyses[0].keys()))
    ancestry_columns = list(ancestry_rows[0].keys())
    write_tsv(release_dir / "sidecars" / "ancestry.tsv", ancestry_rows, ancestry_columns)
    sd_columns = list(sd_rows[0].keys())
    write_tsv(release_dir / "sidecars" / "sd_estimation.tsv", sd_rows, sd_columns)
    merge_validation_yaml(
        release_dir / "validation.yaml",
        validator_name="resources/generators/opengwas-gwas-vcf-dense/annotate.py",
        updated_checks={
            "ancestry": overall_check(ancestry_statuses),
            "effect_scale": overall_check(sd_statuses),
            "sd_estimation": overall_check(sd_statuses),
        },
        new_warnings=warnings,
        updated_reports={"ancestry": "sidecars/ancestry.tsv", "sd_estimation": "sidecars/sd_estimation.tsv"},
    )
    print(
        f"Annotated {len(selected)} analyses in one AF/SE extraction pass each; "
        f"ancestry={overall_check(ancestry_statuses)} effect_scale={overall_check(sd_statuses)}"
    )


if __name__ == "__main__":
    main()
