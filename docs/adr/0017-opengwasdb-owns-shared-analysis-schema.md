# OpenGWASDB owns the shared analysis schema

OpenGWASDB owns the shared interpretation-bearing `analyses.tsv` core schema as
part of its store-format contract. The store registry emits Release Manifests
that conform to that core schema, and may add registry-only columns needed to
locate source files, record checksums, carry licence/publication provenance, or
explain inclusion decisions.

This keeps dependency direction one-way: the registry depends on OpenGWASDB's
schema contract, while OpenGWASDB never depends on the registry to interpret a
built store. Built stores carry their own Analysis metadata, and store-only
fields produced during or after the build, such as reference-completion quality,
do not need to exist in accepted Release Manifests.

Manifest Generators therefore resolve authoritative Analytical Metadata before a
build starts, validate the emitted manifest against the OpenGWASDB shared core
schema, and leave reusable source readers, SD estimation, ancestry assignment,
and statistical validation logic in OpenGWASDB.
