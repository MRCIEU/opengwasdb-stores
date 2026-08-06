# LD panel generation tests

Run `pixi run python tests/ld-panel-generation/run_tests.py`. The tests cover the MAC
boundary, rank-deficient decomposition, cumulative-variance retention,
provenance/artifact agreement, canonical ALIDs, atomic output completion, and
the complete population mapping. They use only synthetic genotypes and do not
download the chromosome-scale callset.
