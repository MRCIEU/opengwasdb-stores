# Non-EUR LD Reference Panels are built from HGDP+1kGP, at structurally lower power

Reference completion requires an ancestry-specific LD Reference Panel, so an
Analysis can only be completed against a panel of its own Assigned Ancestry. Only
EUR has one. It was generated on the UK Biobank RAP from **49,766 individuals** at
MAF ≥ 0.005 (`MRCIEU/ukb-rap-utils`, `scripts/ld_matrix`), and RAP access is not
currently available — so the remaining ancestries cannot be produced the same way.

No locally available cohort comes close to that sample size. HGDP+1kGP offers
roughly 500–1,000 individuals per super-population against UKB's ~50,000. Because
an LD matrix estimated from *n* individuals has rank at most *n*−1 regardless of
how many variants it spans, and a typical block holds several thousand variants,
non-EUR panels are not merely noisier than EUR — they are rank-deficient where EUR
is full-rank. That gap cannot be closed by tuning: reaching p ≈ n would require
~800-variant blocks that would cut through real LD structure.

## Decision

Build **AFR, EAS and SAS** LD Reference Panels from **HGDP+1kGP** (natively
GRCh38, avoiding a liftover the EUR panel needed), and **retain the existing UKB
EUR panel for production** rather than rebuilding it for cohort consistency.
Discarding a 60×-better-powered panel to make the collection uniform would degrade
the ancestry we have the most data for, to no analytical benefit.

Accept as a consequence that **completion quality is permanently asymmetric across
ancestries** for reasons of panel construction rather than of the underlying GWAS.
This asymmetry is made explicit in each panel's Reference Resource declaration —
source cohort, sample size, and variant-inclusion threshold — so it is legible to
anyone comparing an AFR store against a EUR store.

Additionally build an **HGDP+1kGP EUR panel as a calibration control**, not for
production. Holding ancestry fixed and varying only *n* is the only clean way to
measure what the reduced sample size costs in imputation quality; without it, the
usability of the non-EUR panels is a guess.

Parameters, recorded per panel rather than fixed by this decision:

- **Variant inclusion by minor-allele count (MAC ≥ 50)**, not minor-allele
  frequency. A frequency floor means different estimation precision in each panel
  as *n* varies; a count floor tracks precision directly and adapts across
  ancestries with differing sample sizes. The EUR panel's MAF ≥ 0.005 gave ~500
  copies; the same threshold at n ≈ 800 would give ~8, which is unestimable.
- **Existing ancestry-specific LD block definitions are reused**
  (`ld_regions_hg38.tsv`), not recomputed. Block boundaries describe population
  recombination structure; re-deriving them from n ≈ 800 would produce noisier
  boundaries than those that exist, and would break comparability with the EUR
  panel that the calibration control depends on.
- **Variant identifiers are canonical store ALIDs** (`chr:pos:A1:A2`), unlike the
  EUR panel's `chr:pos_ref_alt`. The consuming code accepts both, but emitting
  ALIDs makes allele orientation unambiguous at rest rather than resolved at load,
  removing a class of failure where mis-parsed identifiers silently reduce
  imputation coverage.
- **Panel membership mirrors the ancestry-assignment super-populations**, via an
  explicit recorded mapping parallel to the assignment's own group map. Admixed
  populations (1kGP ASW, ACB) are **excluded from AFR**: recent admixture creates
  long-range LD absent from continental African populations, so including them
  would build a panel whose LD is wrong for exactly the Analyses routed to it.

## Considered options

- **Wait for UKB RAP access to be restored.** Rejected as a blocker: the RAP
  pipeline already loops over AFR/EAS/SAS and would reuse unchanged, but UKB's
  non-EUR counts (~8k SAS, ~8k AFR, ~2.5k EAS) are themselves far below EUR, so
  waiting buys a smaller improvement than it appears while blocking all non-EUR
  completion indefinitely.
- **Rebuild EUR from HGDP+1kGP for cohort consistency.** Rejected: makes every
  panel equally weak rather than making the weak ones stronger, and sacrifices the
  ancestry with the most Analyses.
- **Extend to all seven assigned super-populations.** Rejected: AMR, MID and NAF
  have no ancestry-specific LD block definitions, and HGDP+1kGP coverage of MID
  and NAF is thin. Analyses assigned to them remain observed-only, which
  Ancestry-Matched Completion already handles as a first-class state.
- **Collapse MID/NAF into adjacent panels.** Rejected: that is precisely the
  admixture the fine-grained ancestry fit exists to detect, and it would impute
  against knowingly wrong LD rather than declining to impute.
- **Shrinkage LD estimation to regularise low-*n* matrices.** Not adopted now: it
  is the standard remedy for small reference panels and would permit a lower MAC
  floor, but it changes the Reference Completion Method and its provenance
  contract. Retained as the escape hatch if calibration shows MAC-thresholding is
  insufficient.

## Consequences

- Analyses assigned AMR, MID or NAF can be annotated and stored but never
  reference-completed, until block definitions and a panel exist for them.
- Panel artifacts live outside this repository under the configured reference root
  and are referenced by `resource_id`, per the Registry-not-artifact-store rule.
- The calibration control's result determines whether the non-EUR panels ship at
  all, and should be recorded as release evidence rather than folklore.
- Because completion quality now varies by panel provenance as well as by data
  quality, per-Analysis completion-quality summaries are the only reliable way to
  compare Analyses across ancestries.
