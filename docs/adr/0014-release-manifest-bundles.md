# Release manifest bundles

A Release Manifest is represented as a small directory bundle rather than one large file. Release-level identity and status live in YAML, the concrete Analysis table lives in TSV, and every release bundle includes its own concrete `analyses.tsv` and `build.yaml` so large Store Releases remain readable, diffable, streamable, self-contained, and reproducible.
