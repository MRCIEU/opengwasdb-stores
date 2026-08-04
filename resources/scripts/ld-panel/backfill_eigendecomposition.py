#!/usr/bin/env python3
"""Backfill missing ``.ldeig.npz`` eigendecompositions for an LD Reference Panel.

OpenGWASDB's reference completion consumes only the eigendecomposition of each LD
block (``load_ld_eigenvectors`` reads ``{block}.ldeig.npz``); the full
``{block}.unphased.vcor1.gz`` matrix is a fallback that is never read when the npz
is present. Panels are therefore stored as eigendecompositions only. Blocks that
predate that decision and still lack an npz must be backfilled before the matrix
fallback is removed, or they would be silently dropped from completion.

Components stored are variance-driven rather than a fixed count: enough to reach
``--cumvar`` of the total spectrum, with a floor of ``--min-k`` so the panel is
never *worse* resolved than the historical fixed-250 convention. This matters
because consumers truncate again at load time (default 0.9); if the stored count
bound first, imputation would silently use less variance than requested.

Usage:
  uv run python backfill_eigendecomposition.py \
      --panel /path/to/ld_reference_panel_hg38 --ancestry EUR
"""

from __future__ import annotations

import argparse
import gzip
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy.linalg


def _read_ld_matrix(path: Path) -> np.ndarray:
    """Read a plink2 ``--r-unphased square`` matrix (tab-delimited, gzipped)."""
    with gzip.open(path, "rt") as fh:
        rows = [np.fromstring(line, sep="\t") for line in fh]  # noqa: NPY201
    return np.asarray(rows, dtype=np.float64)


def _eigendecompose(ld: np.ndarray, cumvar: float, min_k: int) -> tuple[np.ndarray, int]:
    """Return (all eigenvalues descending, number of eigenvectors to keep)."""
    vals, vecs = scipy.linalg.eigh(ld)
    vals = vals[::-1]
    vecs = vecs[:, ::-1]
    # plink2 computes pairwise correlations, so the matrix is not guaranteed PSD;
    # clamp negatives exactly as opengwasdb.completion.impute.ld_pca does.
    clamped = np.maximum(vals, 0.0)
    total = float(clamped.sum()) or 1.0
    k = int(np.searchsorted(np.cumsum(clamped) / total, cumvar)) + 1
    k = max(k, min_k)
    k = min(k, vecs.shape[1])
    return vals, vecs, k


def _write_npz(npz_path: Path, vals: np.ndarray, vecs: np.ndarray, k: int) -> None:
    """Atomic write: temp then rename, so a crash never leaves a half-written cache."""
    fd, tmp_base = tempfile.mkstemp(suffix=".tmp", dir=npz_path.parent)
    Path(tmp_base).unlink(missing_ok=True)
    import os

    os.close(fd)
    tmp_npz = Path(tmp_base + ".npz")
    try:
        np.savez_compressed(tmp_base, values=vals, vectors=vecs[:, :k])
        tmp_npz.replace(npz_path)
    except Exception:
        tmp_npz.unlink(missing_ok=True)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel", type=Path, required=True, help="Panel root (contains {ancestry}/)")
    ap.add_argument("--ancestry", required=True)
    ap.add_argument("--cumvar", type=float, default=0.99)
    ap.add_argument("--min-k", type=int, default=250)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = args.panel / args.ancestry
    if not root.is_dir():
        print(f"No such panel ancestry directory: {root}", file=sys.stderr)
        return 1

    missing = [
        tsv.with_suffix("")
        for chrom_dir in sorted(root.iterdir())
        if chrom_dir.is_dir()
        for tsv in sorted(chrom_dir.glob("*.tsv"))
        if not tsv.with_suffix(".ldeig.npz").exists()
        and tsv.with_suffix(".unphased.vcor1.gz").exists()
    ]
    print(f"{len(missing)} block(s) missing an eigendecomposition")
    if args.dry_run:
        for b in missing:
            print(f"  {b}")
        return 0

    for i, base in enumerate(missing, 1):
        ld_path = base.with_suffix(".unphased.vcor1.gz")
        npz_path = base.with_suffix(".ldeig.npz")
        print(f"[{i}/{len(missing)}] {base}", flush=True)
        ld = _read_ld_matrix(ld_path)
        if ld.ndim != 2 or ld.shape[0] != ld.shape[1]:
            print(f"  !! not square {ld.shape} — skipping", flush=True)
            continue
        vals, vecs, k = _eigendecompose(ld, args.cumvar, args.min_k)
        _write_npz(npz_path, vals, vecs, k)
        achieved = float(np.cumsum(np.maximum(vals, 0.0))[k - 1] / (np.maximum(vals, 0.0).sum() or 1.0))
        print(f"  p={ld.shape[0]} k={k} cumvar={achieved:.4f}", flush=True)

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
