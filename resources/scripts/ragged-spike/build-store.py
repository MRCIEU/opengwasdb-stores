#!/usr/bin/env python
"""Build the Sun-plasma-proteome ragged store from the filtered spike data and
validate it by reading associations back — the #7 end-to-end check.

Run with the opengwasdb venv + repo on the path:
  PYTHONPATH=../opengwasdb ../opengwasdb/.venv/bin/python \
      resources/scripts/ragged-spike/build-store.py
"""
from __future__ import annotations

import gzip
import subprocess
from pathlib import Path

from opengwasdb.layouts.ragged.build_ssf import build_ragged_from_ssf
from opengwasdb.layouts.ragged.zarr_csr import RaggedCSRReader
from opengwasdb.model.manifest import StoreManifest
from opengwasdb.traits.axis import TraitsAxisReader

SPIKE = Path("resources/data/ragged-spike")
FILTERED = SPIKE / "filtered"
MANIFEST = SPIKE / "analyses-manifest.tsv"
STORE = SPIKE / "store" / "ragged__pmid-29875488__European"


def variant_lookup(store: Path) -> dict[int, tuple[str, int]]:
    """variant_index -> (chromosome, position) from variants.tsv.gz."""
    out: dict[int, tuple[str, int]] = {}
    with gzip.open(store / "variants.tsv.gz", "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            out[int(f[2])] = (f[0], int(f[1]))
    return out


def main() -> None:
    print("=== BUILD ===")
    result = build_ragged_from_ssf(
        MANIFEST, FILTERED, STORE,
        store_id="ragged__pmid-29875488__European",
        release_id="2018-sun-plasma-proteome-spike",
        stored_effect_scale="sd_units",
        overwrite=True,
    )

    print("\n=== STORE ON DISK ===")
    for p in sorted(STORE.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(STORE)}  ({p.stat().st_size:,} B)")
    du = subprocess.run(["du", "-sh", str(STORE)], capture_output=True, text=True)
    print(f"  total: {du.stdout.split()[0]}")

    print("\n=== MANIFEST ===")
    m = StoreManifest.load(STORE)
    print(f"  layout={m.primary_layout.value} coverage={m.association_coverage.value} "
          f"completion={m.completion_state.value} assembly={m.reference_assembly}")
    print(f"  effect_scale={m.provenance['stored_effect_scale']} "
          f"mhc_analyses={m.provenance['mhc_analyses']}")

    print("\n=== READ-BACK (query the store) ===")
    reader = RaggedCSRReader(STORE)
    vlook = variant_lookup(STORE)
    print(f"  n_analyses={reader.n_analyses} n_associations={reader.n_associations:,}")

    with TraitsAxisReader(STORE) as traits:
        analyses = list(traits.all())
    analyses.sort(key=lambda t: t.analysis_index)

    print("\n  per-analysis association counts + chromosome spread of stored variants:")
    for t in analyses:
        assoc = reader.get_analysis(t.analysis_index)
        chrs = sorted({vlook[int(vi)][0] for vi in assoc.variant_index},
                      key=lambda c: (len(c), c))
        cis_chr = t.trait_chr
        n_cis = sum(1 for vi in assoc.variant_index if vlook[int(vi)][0] == cis_chr)
        print(f"    [{t.analysis_index}] {t.gene_name or t.analysis_id:<10} "
              f"{t.trait_id:<20} n_assoc={len(assoc.variant_index):>6}  "
              f"cis(chr{cis_chr})={n_cis:>6}  chrs={','.join(chrs)}")

    print("\n=== POINT QUERY: cis-pQTL for USP25 ===")
    usp25 = next(t for t in analyses if t.gene_name == "USP25")
    a = reader.get_analysis(usp25.analysis_index)
    # strongest |z| among its cis (chr21) variants
    cis = [(int(vi), float(z), float(se)) for vi, z, se in
           zip(a.variant_index, a.z, a.se) if vlook[int(vi)][0] == usp25.trait_chr]
    top = max(cis, key=lambda r: abs(r[1]))
    chrom, pos = vlook[top[0]]
    print(f"  USP25 strongest cis assoc: chr{chrom}:{pos}  z={top[1]:.2f} se={top[2]:.3f} "
          f"(from {len(cis)} cis variants; total {len(a.variant_index)} incl. trans)")

    print("\n=== trans check: USP25 associations on chr6 (MHC) ===")
    trans6 = sum(1 for vi in a.variant_index if vlook[int(vi)][0] == "6")
    print(f"  USP25 has {trans6} stored associations on chr6 (the HLA trans signal)")

    print("\nOK — store built and queried.")


if __name__ == "__main__":
    main()
