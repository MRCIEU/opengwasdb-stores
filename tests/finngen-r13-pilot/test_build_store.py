#!/usr/bin/env python3
"""Frozen FinnGen bundle through OpenGWASDB's Store envelope and query API."""
from __future__ import annotations

import csv
import gzip
import importlib.util
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from opengwasdb.query import query_store
from opengwasdb.validation import validate_store

ROOT = Path(__file__).resolve().parents[2]


def load_build_module() -> object:
    path = ROOT / "resources/generators/opengwas-gwas-vcf-dense/build-store.py"
    spec = importlib.util.spec_from_file_location("dense_build_store", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_finngen(path: Path, *, beta: float, se: float) -> None:
    with gzip.open(path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["#chrom", "pos", "ref", "alt", "beta", "sebeta", "af_alt"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows([
            {"#chrom": "1", "pos": 1000, "ref": "G", "alt": "A", "beta": beta, "sebeta": se, "af_alt": 0.4},
            {"#chrom": "2", "pos": 2000, "ref": "T", "alt": "C", "beta": -beta, "sebeta": se, "af_alt": 0.3},
        ])


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp_raw:
        tmp = Path(tmp_raw)
        release = tmp / "release"
        release.mkdir()
        binary_source = tmp / "finngen_R13_BINARY.gz"
        quant_source = tmp / "finngen_R13_QUANT.gz"
        write_finngen(binary_source, beta=0.6, se=0.3)
        write_finngen(quant_source, beta=0.8, se=0.4)
        store = tmp / "store.opengwasdb"

        columns = [
            "analysis_id", "source_analysis_id", "source_label", "analysis_label",
            "trait_ontology_id", "trait_ontology_label", "trait_ontology_mapping_method",
            "source_file", "source_reader_capability", "source_genome_build", "license",
            "publication_doi", "publication_pmid", "consortium", "first_author",
            "source_ancestry_label", "assigned_ancestry", "ancestry_assignment_method",
            "ancestry_prop_EUR", "original_effect_scale", "original_sd", "original_sd_method",
            "stored_effect_scale", "sample_size_kind", "sample_size_scope", "sample_size",
            "n_cases", "n_controls", "exclude_from_build",
        ]
        common = {
            "trait_ontology_id": "",
            "trait_ontology_label": "",
            "trait_ontology_mapping_method": "unmapped",
            "source_reader_capability": "opengwasdb.finngen-r13",
            "source_genome_build": "GRCh38",
            "license": "FinnGen public data",
            "publication_doi": "",
            "publication_pmid": "",
            "consortium": "FinnGen",
            "first_author": "",
            "source_ancestry_label": "Finnish",
            "assigned_ancestry": "EUR",
            "ancestry_assignment_method": "af_assigned",
            "ancestry_prop_EUR": "0.99",
            "sample_size_scope": "analysis_level",
            "exclude_from_build": "",
        }
        rows = [
            {
                **common,
                "analysis_id": "finngen-r13-BINARY",
                "source_analysis_id": "BINARY",
                "source_label": "Binary fixture",
                "analysis_label": "Binary fixture",
                "source_file": str(binary_source),
                "original_effect_scale": "log_or",
                "original_sd": "",
                "original_sd_method": "binary_trait",
                "stored_effect_scale": "log_or",
                "sample_size_kind": "case_control",
                "sample_size": "10000",
                "n_cases": "1000",
                "n_controls": "9000",
            },
            {
                **common,
                "analysis_id": "finngen-r13-QUANT",
                "source_analysis_id": "QUANT",
                "source_label": "Quantitative fixture",
                "analysis_label": "Quantitative fixture",
                "source_file": str(quant_source),
                "original_effect_scale": "sd",
                "original_sd": "2",
                "original_sd_method": "source_provided",
                "stored_effect_scale": "sd",
                "sample_size_kind": "total",
                "sample_size": "10000",
                "n_cases": "",
                "n_controls": "",
            },
        ]
        with (release / "analyses.tsv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        (release / "release.yaml").write_text(
            "store_family_id: finngen-r13-fixture\nfamily_release_id: fixture-2\n",
            encoding="utf-8",
        )
        (release / "build.yaml").write_text(
            f"""store_family_id: finngen-r13-fixture
family_release_id: fixture-2
store_layout: dense-observed
completion_state: observed-only
builder:
  package: opengwasdb
  entrypoint: opengwasdb.layouts.dense.build_vcf:build_dense_from_vcf_manifest
source:
  source_format: finngen-r13-tabular
  source_reader_capability: opengwasdb.finngen-r13
  source_genome_build: GRCh38
normalisation:
  target_reference_assembly: GRCh38
  liftover: none
artifacts:
  store_uri: {store}
""",
            encoding="utf-8",
        )
        (release / "validation.yaml").write_text(
            "checks:\n  schema: passed\n  files: passed\n  reader_smoke_test: not_run\n"
            "reports: {}\nwarnings: []\nerrors: []\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "resources/generators/opengwas-gwas-vcf-dense/build-store.py",
                f"--release-dir={release}",
                "--workers=2",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert (store / "manifest.json").exists()
        assert (store / "analyses.tsv").exists()
        assert (store / "data.zarr").exists()
        validation = validate_store(store)
        assert validation.ok, validation.errors

        query = query_store(store)
        try:
            binary = query.lookup(["1:1000:A:G"], ["finngen-r13-BINARY"])
            quantitative = query.lookup(["1:1000:A:G"], ["finngen-r13-QUANT"])
            built = {row["analysis_id"]: row for row in query.analyses_table().values()}
        finally:
            query.close()
        assert math.isclose(float(binary["z"][0]), 2.0, rel_tol=1e-3)
        assert math.isclose(float(binary["se"][0]), 0.3, rel_tol=1e-3)
        assert math.isclose(float(quantitative["z"][0]), 2.0, rel_tol=1e-3)
        assert math.isclose(float(quantitative["se"][0]), 0.2, rel_tol=1e-3)

        for analysis_id, source in ((row["analysis_id"], row) for row in rows):
            observed = built[analysis_id]
            for column in (
                "sample_size_kind", "sample_size_scope", "sample_size", "n_cases", "n_controls",
                "assigned_ancestry", "ancestry_assignment_method", "original_effect_scale",
                "original_sd", "original_sd_method", "stored_effect_scale",
            ):
                assert observed[column] == source[column], (
                    f"{analysis_id}: built {column}={observed[column]!r}, expected {source[column]!r}"
                )
            assert math.isclose(float(observed["ancestry_prop_EUR"]), 0.99, rel_tol=1e-9)

        report = read_rows(release / "sidecars" / "build_report.tsv")[0]
        assert report["binary_probe_analysis_id"] == "finngen-r13-BINARY"
        assert report["quantitative_probe_analysis_id"] == "finngen-r13-QUANT"
        assert report["store_validation_status"] == "passed"
        validation_text = (release / "validation.yaml").read_text(encoding="utf-8")
        assert "reader_smoke_test: passed" in validation_text
        assert "store: passed" in validation_text

    build_module = load_build_module()
    mismatch_errors = build_module.metadata_mismatch_errors(  # type: ignore[attr-defined]
        [{"analysis_id": "fixture", "stored_effect_scale": "log_or", "n_cases": "100"}],
        {"fixture": {"stored_effect_scale": "log_or", "n_cases": ""}},
    )
    assert mismatch_errors
    assert "n_cases" in mismatch_errors[0]
    print("ALL 30 CHECKS PASSED")


if __name__ == "__main__":
    main()
