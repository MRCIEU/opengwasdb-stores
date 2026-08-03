#!/usr/bin/env Rscript
# Deterministically (re)generates the tiny reference-AF + release fixtures
# used by tests/effect-scale-validation/*.R. Re-run this script whenever the
# fixture design changes; its output is committed so tests do not depend on
# regenerating it.

suppressPackageStartupMessages(library(data.table))

# Run from the repository root: Rscript tests/effect-scale-validation/fixtures/generate_fixtures.R
fixtures_dir <- "tests/effect-scale-validation/fixtures"

ref_dir <- file.path(fixtures_dir, "reference-af", "EUR", "1")
ref_dir_chr2 <- file.path(fixtures_dir, "reference-af", "EUR", "2")
filtered_dir <- file.path(fixtures_dir, "release", "filtered")
release_dir <- file.path(fixtures_dir, "release")
dir.create(ref_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(ref_dir_chr2, recursive = TRUE, showWarnings = FALSE)
dir.create(filtered_dir, recursive = TRUE, showWarnings = FALSE)

N <- 10000

implied_se <- function(target_sd, maf) target_sd / sqrt(2 * N * maf * (1 - maf))

# --- Reference AF block: chr1, one block file spans 1-100000 -----------
ref_rows <- list()
add_ref <- function(bp, oa, ea, eaf) {
  ref_rows[[length(ref_rows) + 1]] <<- data.table(CHR = "1", SNP = sprintf("1:%d_%s_%s", bp, oa, ea),
                                                   OA = oa, EA = ea, EAF = eaf, BP = bp)
}

ref_rows_chr2 <- list()
add_ref_chr2 <- function(bp, oa, ea, eaf) {
  ref_rows_chr2[[length(ref_rows_chr2) + 1]] <<- data.table(CHR = "2", SNP = sprintf("2:%d_%s_%s", bp, oa, ea),
                                                             OA = oa, EA = ea, EAF = eaf, BP = bp)
}
# FIXT013: same bp values as chr1's 1000-1004 block but different alleles/MAF,
# to prove chromosome-scoped lookup (not just the first row's chromosome).
for (bp in 1000:1004) add_ref_chr2(bp, "C", "T", 0.10)

# FIXT001: 10 forward-match SNPs, maf=0.30
for (bp in 1000:1009) add_ref(bp, "A", "G", 0.30)
# FIXT002: 10 forward-match SNPs, maf=0.30 (se scaled up in ssf, not here)
for (bp in 1010:1019) add_ref(bp, "A", "G", 0.30)
# FIXT003: alignment mix at 2000-2015 (2012/2013 deliberately absent -> no_overlap)
add_ref(2000, "A", "G", 0.30) # forward-good x5: 2000-2004
add_ref(2001, "A", "G", 0.30)
add_ref(2002, "A", "G", 0.30)
add_ref(2003, "A", "G", 0.30)
add_ref(2004, "A", "G", 0.30)
add_ref(2005, "A", "G", 0.30) # swapped-good x3: source will use G/A -> 2005-2007
add_ref(2006, "A", "G", 0.30)
add_ref(2007, "A", "G", 0.30)
add_ref(2008, "C", "G", 0.30) # palindromic source (A/T) x2: 2008-2009 (ref alleles irrelevant)
add_ref(2009, "C", "G", 0.30)
add_ref(2010, "A", "C", 0.30) # mismatch x2: source G/T vs ref A/C: 2010-2011
add_ref(2011, "A", "C", 0.30)
# 2012, 2013 intentionally absent -> no_overlap x2
add_ref(2014, "A", "G", 0.003) # maf-out-of-bounds forward match x2: 2014-2015
add_ref(2015, "A", "G", 0.003)
# FIXT006: empty source AF column -> reference fallback, 1020-1029, maf=0.30
for (bp in 1020:1029) add_ref(bp, "A", "G", 0.30)
# FIXT007: no source AF column at all -> reference fallback, 1030-1039, maf=0.30
for (bp in 1030:1039) add_ref(bp, "A", "G", 0.30)
# FIXT008: ancestry with no configured resource; still put data on chr1 to
# prove the skip is config-driven (ancestry->resource mapping), not data-driven.
for (bp in 1040:1049) add_ref(bp, "A", "G", 0.30)
# FIXT009: low overlap -> reuses FIXT001 positions 1000-1001 (already present)
# FIXT010: unstable implied SD, 3000-3005, maf=0.30
for (bp in 3000:3005) add_ref(bp, "A", "G", 0.30)

# --- Filtered source files + analyses.tsv rows --------------------------
analyses <- list()
write_ssf <- function(filename, dt) {
  fwrite(dt, file.path(filtered_dir, filename), sep = "\t", na = "")
}

base_row <- function(analysis_id, stored_effect_scale, original_effect_scale, original_sd,
                      original_sd_method, assigned_ancestry, filtered_file,
                      n_cases = "", n_controls = "") {
  data.table(
    analysis_index = length(analyses), analysis_id = analysis_id, source_analysis_id = analysis_id,
    source_label = sprintf("Fixture analysis %s", analysis_id),
    trait_ontology_name = "", trait_ontology_id = "",
    source_file = file.path("filtered", filtered_file), filtered_file = filtered_file,
    source_bundle_id = "", checksum = "", checksum_algorithm = "sha256", size_bytes = "",
    source_genome_build = "GRCh38", license = "test-fixture",
    publication_doi = "", publication_pmid = "", consortium = "",
    source_ancestry_label = assigned_ancestry, assigned_ancestry = assigned_ancestry,
    ancestry_assignment_method = "source_trusted_no_af",
    original_effect_scale = original_effect_scale, original_sd = original_sd,
    original_sd_method = original_sd_method, stored_effect_scale = stored_effect_scale,
    sample_size_kind = if (stored_effect_scale == "log_or") "case_control" else "total",
    sample_size_scope = "analysis_level", sample_size = N,
    n_cases = n_cases, n_controls = n_controls,
    analysis_group_id = "FIXTURES", inclusion_reason = "effect_scale_validation_fixture",
    exclude_from_build = ""
  )
}

ssf_skeleton <- function(chromosome, bp, effect_allele, other_allele, se, af = NULL) {
  dt <- data.table(
    chromosome = chromosome, base_pair_location = bp,
    effect_allele = effect_allele, other_allele = other_allele,
    beta = 0.01, standard_error = se, p_value = 0.5,
    variant_id = sprintf("%s:%d", chromosome, bp)
  )
  if (!is.null(af)) dt[, effect_allele_frequency := af]
  dt
}

# FIXT001: declared_standardised, implied SD ~ 1 -> passed
se1 <- implied_se(1.0, 0.30)
write_ssf("FIXT001.filtered.tsv.gz", ssf_skeleton("1", 1000:1009, "A", "G", se1, af = ""))
analyses[[length(analyses) + 1]] <- base_row("FIXT001", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT001.filtered.tsv.gz")

# FIXT002: declared_standardised, implied SD ~ 3 -> failed
se2 <- implied_se(3.0, 0.30)
write_ssf("FIXT002.filtered.tsv.gz", ssf_skeleton("1", 1010:1019, "A", "G", se2, af = ""))
analyses[[length(analyses) + 1]] <- base_row("FIXT002", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT002.filtered.tsv.gz")

# FIXT003: allele-matching mix -> still passes overall (8 good variants)
se_good <- implied_se(1.0, 0.30)
fixt003 <- rbindlist(list(
  ssf_skeleton("1", 2000:2004, "A", "G", se_good, af = ""),           # forward-good x5
  ssf_skeleton("1", 2005:2007, "G", "A", se_good, af = ""),           # swapped-good x3
  ssf_skeleton("1", 2008:2009, "A", "T", se_good, af = ""),           # palindromic x2
  ssf_skeleton("1", 2010:2011, "G", "T", se_good, af = ""),           # mismatch x2
  ssf_skeleton("1", 2012:2013, "A", "G", se_good, af = ""),           # no_overlap x2
  ssf_skeleton("1", 2014:2015, "A", "G", se_good, af = "")            # maf-out-of-bounds x2
))
write_ssf("FIXT003.filtered.tsv.gz", fixt003)
analyses[[length(analyses) + 1]] <- base_row("FIXT003", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT003.filtered.tsv.gz")

# FIXT004: binary/log_or -> skipped, non_quantitative_effect_scale
write_ssf("FIXT004.filtered.tsv.gz", ssf_skeleton("1", 1000:1004, "A", "G", 0.05, af = ""))
analyses[[length(analyses) + 1]] <- base_row("FIXT004", "log_or", "logOR", "", "binary_trait",
                                              "European", "FIXT004.filtered.tsv.gz",
                                              n_cases = 5000, n_controls = 5000)

# FIXT005: usable source AF -> af_source = source (chr 99 has no reference data
# at all, proving reference is never consulted when source AF is usable)
se5 <- implied_se(1.0, 0.30)
write_ssf("FIXT005.filtered.tsv.gz", ssf_skeleton("99", 5000:5007, "A", "G", se5, af = 0.30))
analyses[[length(analyses) + 1]] <- base_row("FIXT005", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT005.filtered.tsv.gz")

# FIXT006: AF column present but empty (Sun-pilot style) -> reference fallback
se6 <- implied_se(1.0, 0.30)
write_ssf("FIXT006.filtered.tsv.gz", ssf_skeleton("1", 1020:1029, "A", "G", se6, af = ""))
analyses[[length(analyses) + 1]] <- base_row("FIXT006", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT006.filtered.tsv.gz")

# FIXT007: no AF column at all -> reference fallback
se7 <- implied_se(1.0, 0.30)
ssf7 <- ssf_skeleton("1", 1030:1039, "A", "G", se7, af = NULL)
write_ssf("FIXT007.filtered.tsv.gz", ssf7)
analyses[[length(analyses) + 1]] <- base_row("FIXT007", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT007.filtered.tsv.gz")

# FIXT008: assigned ancestry with no configured reference resource -> skipped
se8 <- implied_se(1.0, 0.30)
write_ssf("FIXT008.filtered.tsv.gz", ssf_skeleton("1", 1040:1049, "A", "G", se8, af = ""))
analyses[[length(analyses) + 1]] <- base_row("FIXT008", "sd", "sd", "", "declared_standardised",
                                              "African", "FIXT008.filtered.tsv.gz")

# FIXT009: low overlap (only 2 retained variants; threshold in test config = 5)
se9 <- implied_se(1.0, 0.30)
write_ssf("FIXT009.filtered.tsv.gz", ssf_skeleton("1", 1000:1001, "A", "G", se9, af = ""))
analyses[[length(analyses) + 1]] <- base_row("FIXT009", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT009.filtered.tsv.gz")

# FIXT010: unstable implied SD (high dispersion) -> warning
se_lo <- implied_se(1.0, 0.30)
se_hi <- implied_se(5.0, 0.30)
write_ssf("FIXT010.filtered.tsv.gz", ssf_skeleton("1", 3000:3005, "A", "G",
                                                    c(se_lo, se_lo, se_lo, se_hi, se_hi, se_hi), af = ""))
analyses[[length(analyses) + 1]] <- base_row("FIXT010", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT010.filtered.tsv.gz")

# FIXT011: not yet standardised, no source AF -> estimation populates
# original_sd / original_sd_method = estimated_from_reference_maf
se11 <- implied_se(1.7, 0.30)
write_ssf("FIXT011.filtered.tsv.gz", ssf_skeleton("1", 1050:1059, "A", "G", se11, af = ""))
for (bp in 1050:1059) add_ref(bp, "A", "G", 0.30)
analyses[[length(analyses) + 1]] <- base_row("FIXT011", "sd", "cm", "", "unavailable",
                                              "European", "FIXT011.filtered.tsv.gz")

# FIXT012: not yet standardised, usable source AF -> estimation populates
# original_sd / original_sd_method = estimated_from_source_maf
se12 <- implied_se(2.1, 0.30)
write_ssf("FIXT012.filtered.tsv.gz", ssf_skeleton("99", 6000:6009, "A", "G", se12, af = 0.30))
analyses[[length(analyses) + 1]] <- base_row("FIXT012", "sd", "cm", "", "unavailable",
                                              "European", "FIXT012.filtered.tsv.gz")

# FIXT013: chr1 rows 1000-1004 (forward, maf=0.30) + chr2 rows at the same bp
# values (forward, maf=0.10, different alleles) -> both chromosomes' variants
# must be retained (10 total), proving the lookup is scoped per-chromosome.
se13_chr1 <- implied_se(1.0, 0.30)
se13_chr2 <- implied_se(1.0, 0.10)
fixt013 <- rbindlist(list(
  ssf_skeleton("1", 1000:1004, "A", "G", se13_chr1, af = ""),
  ssf_skeleton("2", 1000:1004, "C", "T", se13_chr2, af = "")
))
write_ssf("FIXT013.filtered.tsv.gz", fixt013)
analyses[[length(analyses) + 1]] <- base_row("FIXT013", "sd", "sd", "", "declared_standardised",
                                              "European", "FIXT013.filtered.tsv.gz")

ref_table <- rbindlist(ref_rows)
fwrite(ref_table, file.path(ref_dir, "1000-3100.tsv"), sep = "\t")
ref_table_chr2 <- rbindlist(ref_rows_chr2)
fwrite(ref_table_chr2, file.path(ref_dir_chr2, "1000-1004.tsv"), sep = "\t")

analyses_dt <- rbindlist(analyses, fill = TRUE)
analyses_dt[, analysis_index := .I - 1L]
dir.create(release_dir, recursive = TRUE, showWarnings = FALSE)
fwrite(analyses_dt, file.path(release_dir, "analyses.tsv"), sep = "\t", na = "")

# The effect-scale stage mutates validation.yaml (checks/warnings) and
# analyses.tsv (original_sd/original_sd_method) in place. Reset validation.yaml
# to a pristine not_run baseline on every regeneration so repeated test runs
# are idempotent rather than accumulating warnings across invocations.
writeLines(c(
  "status: not_run",
  "validated_at: ~",
  "validator:",
  "  name: ~",
  "  version: ~",
  "checks:",
  "  schema: not_run",
  "  files: not_run",
  "  reader_smoke_test: not_run",
  "  ancestry: not_run",
  "  effect_scale: not_run",
  "  sd_estimation: not_run",
  "  sparse_regions: not_run",
  "reports: {}",
  "warnings: []",
  "errors: []"
), file.path(release_dir, "validation.yaml"))

cat(sprintf("Wrote %d fixture analyses to %s\n", nrow(analyses_dt), release_dir))
