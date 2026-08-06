# Reference Resources

Reference Resources describe auxiliary build-time resources such as LD reference panels and genome references. They can be used by Build Recipes but are not the summary-statistics Source Collections that define Store Families.

Each subdirectory records one Reference Resource declaration (`resource.yaml`): a stable `resource_id`, ancestry/population label, genome build, variant identifier/allele conventions, and an external `location` outside this repository. Build Recipes reference a declared `resource_id` (see `docs/release-metadata-schema.md`, "Reference Resource declaration") so reviewers know exactly which panel a release used; the panel data itself always lives under the configured artifact/reference root, never in this repository.

- `ukb-hg38-eur-af/` - UKB hg38 EUR reference allele frequencies, used as the reference-AF fallback for effect-scale validation (issue #16) when a Source Collection provides no usable source allele frequencies.
- `ukb-ancestry-mixture-hg38/` - UK Biobank ancestry-mixture reference allele frequencies (Privé 2022), used for AF-based ancestry assignment (issue #23) when a Source Collection provides usable source allele frequencies. Distinct from `ukb-hg38-eur-af`: this one is multi-ancestry (7 super-populations) and used for mixture fitting, not single-ancestry MAF lookup.
- `gpm-hg38-eur-ld/` - UKB hg38 EUR LD reference panel, used for reference completion of EUR-assigned Analyses. Declares the same physical directory as `ukb-hg38-eur-af`, but for its LD content rather than its allele frequencies.
- `hgdp1kgp-hg38-ld/` - available HGDP+1kGP LD reference panels for AFR, EAS and SAS. Built from a different, much smaller cohort than the EUR panel; see ADR 0020 for why, and for the resulting permanent difference in completion quality across ancestries.
- `hgdp1kgp-hg38-eur-calibration/` - available matched, non-production EUR calibration control; its quantitative comparison with the UKB EUR panel gates release of the production panels.

Generation and maintenance tooling for LD panels lives in `resources/scripts/ld-panel/`.
