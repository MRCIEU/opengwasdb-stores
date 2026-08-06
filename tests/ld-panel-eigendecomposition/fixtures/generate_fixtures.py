#!/usr/bin/env python3
"""Deterministically (re)generates a tiny synthetic LD Reference Panel used by
tests/ld-panel-eigendecomposition/run_tests.py.

Run from the repository root:
  python3 tests/ld-panel-eigendecomposition/fixtures/generate_fixtures.py

Blocks are AR(1) correlation matrices (R[i,j] = rho**|i-j|), which are cheap to
build, always PSD, and have a spectral decay rate controlled by rho — a high rho
concentrates variance in a few components (few needed at a given cumvar
threshold), a low rho spreads it out (many needed). That lets the fixtures
exercise both "already resolved" and "under-resolved" blocks without needing
real genotype data or panel-scale matrix sizes.
"""
from __future__ import annotations

import gzip
from pathlib import Path

import numpy as np

FIXTURES_DIR = Path("tests/ld-panel-eigendecomposition/fixtures")
PANEL_DIR = FIXTURES_DIR / "panel"
ANCESTRY = "EUR"
CHROM = "1"

# name -> (p, rho). "peaked" blocks concentrate variance in ~1-2 components
# (under-resolved on purpose by generate_fixtures with only 1 stored
# component below); "spread" blocks need most of their components to reach
# high cumvar thresholds.
BLOCKS = {
    "1000-1040": (8, 0.95),   # peaked: stored deliberately under-resolved
    "2000-2030": (6, 0.9),    # peaked: already resolved at the default min-k
    "3000-3060": (10, 0.2),   # spread: needs many components at cumvar=0.99
}


def ar1_matrix(p: int, rho: float) -> np.ndarray:
    idx = np.arange(p)
    return rho ** np.abs(idx[:, None] - idx[None, :])


def write_block_files(chrom_dir: Path, name: str, r: np.ndarray) -> None:
    p = r.shape[0]
    (chrom_dir / f"{name}.tsv").write_text(
        "\n".join(["pos"] + [str(1000 + i) for i in range(p)]) + "\n"
    )
    # mtime=0 keeps the gzip byte stream reproducible across regenerations —
    # gzip embeds the write timestamp by default, which would otherwise make
    # every re-run of this script touch every committed fixture file.
    with gzip.GzipFile(chrom_dir / f"{name}.unphased.vcor1.gz", "wb", mtime=0) as gz:
        body = "".join("\t".join(f"{v:.6g}" for v in row) + "\n" for row in r)
        gz.write(body.encode())


def write_ragged_block(chrom_dir: Path, name: str) -> None:
    """A block whose matrix rows aren't square — exercises the "not square,
    skip" path, and (run alongside valid blocks under --jobs > 1) that one
    bad block doesn't take down the rest of a parallel run."""
    (chrom_dir / f"{name}.tsv").write_text("pos\n9000\n9001\n9002\n")
    with gzip.GzipFile(chrom_dir / f"{name}.unphased.vcor1.gz", "wb", mtime=0) as gz:
        gz.write(b"1\t0.5\t0.2\n0.5\t1\n0.2\t0.5\t1\n")


def write_underresolved_npz(chrom_dir: Path, name: str, r: np.ndarray, stored_k: int) -> None:
    """Write a pre-existing `.ldeig.npz` that stores fewer components than
    `--cumvar` would ask for, mimicking the fixed-250 panel issue #34 fixes."""
    vals, vecs = np.linalg.eigh(r)
    vals = vals[::-1]
    vecs = vecs[:, ::-1]
    np.savez_compressed(
        chrom_dir / f"{name}.ldeig.npz", values=vals, vectors=vecs[:, :stored_k]
    )


def main() -> None:
    chrom_dir = PANEL_DIR / ANCESTRY / CHROM
    chrom_dir.mkdir(parents=True, exist_ok=True)
    for f in chrom_dir.glob("*"):
        f.unlink()

    for name, (p, rho) in BLOCKS.items():
        r = ar1_matrix(p, rho)
        write_block_files(chrom_dir, name, r)

    # 1000-1040 starts under-resolved at the consumer's thresh=0.9 (1 stored
    # component isn't enough for a rho=0.95 spectrum's tail); 2000-2030 starts
    # already resolved (stores all its components) so it's a control that
    # `find_underresolved_blocks.py` must NOT flag and `backfill
    # _eigendecomposition.py` must skip without --force. 3000-3060 has no
    # pre-existing npz at all, exercising the "missing" backfill path.
    write_underresolved_npz(chrom_dir, "1000-1040", ar1_matrix(*BLOCKS["1000-1040"]), stored_k=1)
    write_underresolved_npz(chrom_dir, "2000-2030", ar1_matrix(*BLOCKS["2000-2030"]), stored_k=6)

    write_ragged_block(chrom_dir, "9000-9010")

    print(f"wrote {len(BLOCKS) + 1} synthetic block(s) under {chrom_dir}")


if __name__ == "__main__":
    main()
