#!/usr/bin/env Rscript
# Deterministically (re)generates the fixture "full" GWAS-SSF source file and
# candidates table for tests/no-cis-region-policy/run_tests.R (issue #26).
#
# Run from the repository root:
#   Rscript tests/no-cis-region-policy/fixtures/generate_fixtures.R

suppressPackageStartupMessages(library(data.table))

fixtures_dir <- "tests/no-cis-region-policy/fixtures"
source_file <- file.path(
  fixtures_dir, "source", "GCST900001-GCST901000", "GCST900001", "harmonised", "GCST900001.h.tsv.gz"
)
dir.create(dirname(source_file), recursive = TRUE, showWarnings = FALSE)

# 5 significant hits clustered tightly -> one merged significant_trans region.
significant <- data.table(
  chromosome = "1", base_pair_location = seq(5000000, 5000040, by = 10),
  effect_allele = "A", other_allele = "G", beta = 0.3, standard_error = 0.05,
  p_value = 1e-9, effect_allele_frequency = "", variant_id = "", rsid = ""
)
# 3 suggestive hits, far apart -> three distance-pruned suggestive leads.
suggestive <- data.table(
  chromosome = "1", base_pair_location = c(20000000, 40000000, 60000000),
  effect_allele = "A", other_allele = "G", beta = 0.1, standard_error = 0.05,
  p_value = 5e-6, effect_allele_frequency = "", variant_id = "", rsid = ""
)
# 20 null variants, well clear of the significant cluster's +/-1Mb flank
# (4,000,000-6,000,040) and the suggestive leads (which keep only their own
# point, not a window) -> must NOT be retained, since no cis window exists to
# keep them in for a family with no gene target at all.
null_variants <- data.table(
  chromosome = "1", base_pair_location = seq(100000000, 100000000 + 19 * 500000, by = 500000),
  effect_allele = "A", other_allele = "G", beta = 0.01, standard_error = 0.05,
  p_value = 0.5, effect_allele_frequency = "", variant_id = "", rsid = ""
)

full <- rbindlist(list(significant, suggestive, null_variants))
fwrite(full, source_file, sep = "\t")

candidates <- data.table(
  STUDY.ACCESSION = "GCST900001", PUBMED.ID = 99999999L, FIRST.AUTHOR = "Fixture",
  STUDY = "No-cis region policy fixture", DISEASE.TRAIT = "Fixture metabolite level",
  MAPPED_TRAIT = "fixture metabolite measurement", ancestry_group = "European",
  ancestry_fraction = 1, is_molecular = TRUE, molecular_subtype = "metabolomics",
  store_type = "ragged", store_key = "ragged__pmid-99999999__European",
  molecular_type = "metabolomics", study_design = "quantitative",
  n_cases = NA_integer_, n_controls = NA_integer_, sample_size = 5000L,
  n_variants = nrow(full), association_count = nrow(full[p_value <= 5e-8]),
  MAPPED_TRAIT_URI = "http://purl.obolibrary.org/obo/fixture_0000001"
)
fwrite(candidates, file.path(fixtures_dir, "candidates.tsv"), sep = "\t", na = "")

cat(sprintf(
  "Wrote %d source rows (%d significant, %d suggestive, %d null) and 1 candidate\n",
  nrow(full), nrow(significant), nrow(suggestive), nrow(null_variants)
))
