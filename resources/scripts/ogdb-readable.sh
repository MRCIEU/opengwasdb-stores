#!/usr/bin/env bash
#
# Turn `opengwasdb query-*` JSON into a readable table.
#
# The query CLI returns association rows keyed by integer `analysis_index` and
# `variant_index` — compact, but not something you can read. This resolves both
# against the store's own `analyses.tsv` and `variants.tsv.gz`, which every
# layout (Dense, Ragged, Hybrid) ships.
#
# Usage:
#   opengwasdb query-top-hits <store> --limit 5 | ogdb-readable.sh <store>
#
# Output columns: analysis_id, label, rsid, chr, pos, alid, z, se, p
set -euo pipefail

STORE="${1:?usage: ogdb-readable.sh <store_path>  (query JSON on stdin)}"
ANALYSES="$STORE/analyses.tsv"
VARIANTS="$STORE/variants.tsv.gz"

for f in "$ANALYSES" "$VARIANTS"; do
  [ -r "$f" ] || { echo "not readable: $f" >&2; exit 1; }
done

jq -r '.[] | [.analysis_index, .variant_index, .z, .se] | @tsv' \
| awk -F'\t' -v OFS='\t' -v analyses="$ANALYSES" -v variants="$VARIANTS" '
  BEGIN {
    # analyses.tsv: analysis_index col 1, analysis_id col 2, analysis_label col 3.
    while ((getline line < analyses) > 0) {
      split(line, f, "\t")
      if (f[1] == "analysis_index") continue          # header
      aid[f[1]] = f[2]
      alab[f[1]] = (f[3] == "") ? "-" : f[3]
    }
    close(analyses)
  }
  # Buffer the query rows, noting which variant indices we actually need, so
  # the (potentially very large) variant table is scanned exactly once.
  {
    n++; ai[n] = $1; vi[n] = $2; z[n] = $3; se[n] = $4
    want[$2] = 1
  }
  END {
    if (n == 0) { print "(no associations returned)"; exit }
    cmd = "zcat " variants
    while ((cmd | getline line) > 0) {
      split(line, f, "\t")
      if (f[3] in want) {                              # col 3 = variant_index
        chrom[f[3]] = f[1]; pos[f[3]] = f[2]
        alid[f[3]] = f[6];  rsid[f[3]] = f[7]
      }
    }
    close(cmd)

    print "analysis_id", "label", "rsid", "chr", "pos", "alid", "z", "se", "p"
    for (i = 1; i <= n; i++) {
      v = vi[i]
      r = (rsid[v] == "" || rsid[v] == ".") ? "-" : rsid[v]
      # Two-sided normal p from z, via the complementary error function.
      p = erfc(abs(z[i]) / sqrt(2))
      pstr = (p > 0) ? sprintf("%.2e", p) : "<1e-300"    # underflows past |z|~37
      printf "%s\t%s\t%s\t%s\t%s\t%s\t%.3f\t%.4f\t%s\n",
             aid[ai[i]], alab[ai[i]], r, chrom[v], pos[v], alid[v], z[i], se[i], pstr
    }
  }
  function abs(x) { return x < 0 ? -x : x }
  # Abramowitz & Stegun 7.1.26 — plenty for displaying a p-value.
  function erfc(x,   t, y) {
    if (x * x > 700) return 0                          # exp() would underflow
    t = 1 / (1 + 0.3275911 * x)
    y = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 \
        + t * (-1.453152027 + t * 1.061405429))))
    return y * exp(-x * x)
  }
'
