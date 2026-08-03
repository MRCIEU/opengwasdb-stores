#!/usr/bin/env python3
"""Unit test for build-store.py's validation.yaml preservation logic.

build-store.py used to unconditionally overwrite `checks.ancestry`,
`checks.effect_scale`, and `checks.sd_estimation` with hardcoded values every
time it ran, silently discarding whatever the generator's `--mode=effect-scale`
stage had just computed (issue #21). This proves the fix: those three checks
and prior warnings must survive a build-store.py validation.yaml rewrite.

Run from the repository root:
    python3 tests/effect-scale-validation/test_build_store_validation_merge.py
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "resources" / "generators" / "gwas-ssf-ragged" / "build-store.py"


def _stub(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def load_build_store_module():
    # build-store.py imports the opengwasdb package, which is a separate repo
    # not guaranteed to be installed here. Stub it out so we can unit test the
    # pure validation.yaml merge logic in isolation.
    opengwasdb = _stub("opengwasdb")
    _stub("opengwasdb.layouts")
    _stub("opengwasdb.layouts.ragged")
    build_ssf = _stub("opengwasdb.layouts.ragged.build_ssf")
    build_ssf.build_ragged_from_ssf = lambda *a, **k: None
    zarr_csr = _stub("opengwasdb.layouts.ragged.zarr_csr")
    zarr_csr.RaggedCSRReader = object
    model = _stub("opengwasdb.model")
    manifest = _stub("opengwasdb.model.manifest")
    manifest.StoreManifest = object
    traits = _stub("opengwasdb.traits")
    axis = _stub("opengwasdb.traits.axis")
    axis.TraitsAxisReader = object
    opengwasdb.layouts = sys.modules["opengwasdb.layouts"]

    spec = importlib.util.spec_from_file_location("build_store_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_build_store_module()
    n_checks = 0

    def check(cond: bool, message: str) -> None:
        nonlocal n_checks
        n_checks += 1
        if not cond:
            raise AssertionError(message)

    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "validation.yaml"
        path.write_text(
            "\n".join([
                "status: failed",
                "validated_at: 2026-08-03T00:00:00Z",
                "validator:",
                "  name: resources/generators/gwas-ssf-ragged/generate.R",
                "  version: null",
                "checks:",
                "  schema: not_run",
                "  files: not_run",
                "  reader_smoke_test: not_run",
                "  ancestry: not_run",
                "  effect_scale: failed",
                "  sd_estimation: failed",
                "  sparse_regions: not_run",
                "reports: {}",
                "warnings:",
                "  - GCST123: scale_inconsistent (effect_scale_failed)",
                "errors: []",
                "",
            ]),
            encoding="utf-8",
        )

        module.write_validation_yaml(path, path, "passed", ["build warning: nothing serious"])
        rewritten = path.read_text(encoding="utf-8")

        check("effect_scale: failed" in rewritten,
              "checks.effect_scale from the generator stage must survive the build-store rewrite")
        check("sd_estimation: failed" in rewritten,
              "checks.sd_estimation from the generator stage must survive the build-store rewrite")
        check("- GCST123: scale_inconsistent (effect_scale_failed)" in rewritten,
              "prior effect-scale warnings must be preserved")
        check("- build warning: nothing serious" in rewritten,
              "new build-time warnings must also be included")
        check("schema: passed" in rewritten, "build-store.py should still record its own passed checks")
        check("status: failed" in rewritten,
              "overall status must reflect the worse of build checks and preserved effect-scale checks")

    print(f"ALL {n_checks} CHECKS PASSED")


if __name__ == "__main__":
    main()
