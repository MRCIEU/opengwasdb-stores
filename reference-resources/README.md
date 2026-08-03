# Reference Resources

Reference Resources describe auxiliary build-time resources such as LD reference panels and genome references. They can be used by Build Recipes but are not the summary-statistics Source Collections that define Store Families.

Each subdirectory records one Reference Resource declaration (`resource.yaml`): a stable `resource_id`, ancestry/population label, genome build, variant identifier/allele conventions, and an external `location` outside this repository. Build Recipes reference a declared `resource_id` (see `docs/release-metadata-schema.md`, "Reference Resource declaration") so reviewers know exactly which panel a release used; the panel data itself always lives under the configured artifact/reference root, never in this repository.

- `ukb-hg38-eur-af/` - UKB hg38 EUR reference allele frequencies, used as the reference-AF fallback for effect-scale validation (issue #16) when a Source Collection provides no usable source allele frequencies.
