#!/usr/bin/env Rscript
# Unit-level smoke test for the `opengwas-gwas-vcf` metadata resolver
# (issue #49). Run from the repository root:
#
#   Rscript tests/metadata-resolvers/opengwas-api/run_tests.R
#
# Exercises resolve_opengwas_api_metadata() directly against fixture
# "gwasinfo" records shaped like the OpenGWAS API's own published GwasInfo
# schema (https://api.opengwas.io/api/swagger.json). This repository's test
# suites are documented as data-only and network-free (see
# resources/scripts/run_all_tests.py); a live call additionally needs a
# per-user OpenGWAS API token this environment does not have, so
# fetch_opengwas_gwasinfo() (the thin HTTP transport) is deliberately not
# exercised here -- only the resolver logic it feeds.
#
# The resolver itself never sees the source GWAS-VCF file or its ##SAMPLE
# header (per the resolver contract in docs/release-metadata-schema.md,
# input is the provider's own metadata only); the "matches/contradicts the
# VCF header" framing below is narrative context establishing why each
# fixture matters, not an input to the function under test.

suppressPackageStartupMessages(library(data.table))

source("resources/lib/metadata_resolvers/opengwas_api.R")

fail <- function(...) stop(sprintf(...), call. = FALSE)
n_checks <- 0L
check <- function(cond, ...) {
  n_checks <<- n_checks + 1L
  if (!isTRUE(cond)) fail(...)
}

# --- Case-control, agreeing with what the source VCF's ##SAMPLE
# StudyType= header would say (a "boring" case: no override needed, but the
# resolver must still resolve it correctly on its own terms).
r <- resolve_opengwas_api_metadata(list(
  id = "fixt-cc-agree", trait = "Fixture case-control trait (header agrees)",
  ncase = 5000, ncontrol = 15000, sample_size = 20000
))
check(r$resolution_status == "resolved", "cc-agree: expected resolved, got %s", r$resolution_status)
check(r$stored_effect_scale == "log_or", "cc-agree: expected stored_effect_scale=log_or, got %s", r$stored_effect_scale)
check(r$sample_size_kind == "case_control", "cc-agree: expected sample_size_kind=case_control, got %s", r$sample_size_kind)
check(r$n_cases == 5000 && r$n_controls == 15000, "cc-agree: n_cases/n_controls mismatch")
check(r$sample_size == 20000, "cc-agree: expected sample_size=20000, got %s", r$sample_size)

# --- ieu-a-7 (issue #15's motivating example): the source GWAS-VCF
# ##SAMPLE header declares StudyType=Continuous with no case/control
# counts, but the OpenGWAS API's own gwasinfo record for the same study
# correctly reports it as case-control. Values are ieu-a-7's real published
# case/control counts as stated in issue #49 (ncase=60801/ncontrol=123504);
# a live authenticated fetch was not available in this environment (the
# OpenGWAS API's gwasinfo endpoint requires a per-user JWT this environment
# does not have -- confirmed via its own public, unauthenticated
# swagger.json, which is also where the GwasInfo field names below come
# from), so this fixture is a record built from those confirmed-real values
# rather than a captured live response.
r <- resolve_opengwas_api_metadata(list(
  id = "ieu-a-7", trait = "Coronary heart disease",
  ncase = 60801, ncontrol = 123504, sample_size = 184305
))
check(r$resolution_status == "resolved", "ieu-a-7: expected resolved, got %s", r$resolution_status)
check(r$stored_effect_scale == "log_or", "ieu-a-7: expected stored_effect_scale=log_or, got %s", r$stored_effect_scale)
check(r$sample_size_kind == "case_control", "ieu-a-7: expected sample_size_kind=case_control, got %s", r$sample_size_kind)
check(r$n_cases == 60801, "ieu-a-7: expected n_cases=60801, got %s", r$n_cases)
check(r$n_controls == 123504, "ieu-a-7: expected n_controls=123504, got %s", r$n_controls)

# --- Quantitative: no usable case/control counts, only a sample size.
r <- resolve_opengwas_api_metadata(list(
  id = "fixt-quant", trait = "Fixture quantitative trait",
  ncase = NULL, ncontrol = NULL, sample_size = 250000
))
check(r$resolution_status == "resolved", "quant: expected resolved, got %s", r$resolution_status)
check(r$stored_effect_scale == "sd", "quant: expected stored_effect_scale=sd, got %s", r$stored_effect_scale)
check(r$sample_size_kind == "total", "quant: expected sample_size_kind=total, got %s", r$sample_size_kind)
check(r$sample_size == 250000, "quant: expected sample_size=250000, got %s", r$sample_size)
check(is.na(r$n_cases) && is.na(r$n_controls), "quant: n_cases/n_controls should be NA")

# --- Unresolvable: no usable ncase/ncontrol pair and no usable sample_size
# (e.g. a withdrawn or placeholder dataset record). Must resolve to an
# explicit unresolved/unavailable state, never a defaulted 0.
r <- resolve_opengwas_api_metadata(list(id = "fixt-unresolvable", trait = "Fixture withdrawn dataset"))
check(r$resolution_status == "unresolved", "unresolvable: expected unresolved, got %s", r$resolution_status)
check(!is.na(r$resolution_notes) && nzchar(r$resolution_notes), "unresolvable: resolution_notes should explain the failure")
check(is.na(r$stored_effect_scale) && is.na(r$sample_size_kind) && is.na(r$sample_size),
      "unresolvable: resolved fields should all be NA, never a silent default")

# --- Unresolvable variant: a zero/placeholder ncase/ncontrol/sample_size
# (observed API convention for "not applicable", distinct from a genuinely
# missing field) must not be treated as a usable count.
r <- resolve_opengwas_api_metadata(list(id = "fixt-zero", trait = "Fixture zeroed counts", ncase = 0, ncontrol = 0, sample_size = 0))
check(r$resolution_status == "unresolved", "zero-counts: expected unresolved, got %s", r$resolution_status)

# --- Defensive: no record at all (API returned nothing for the id).
r <- resolve_opengwas_api_metadata(NULL)
check(r$resolution_status == "unresolved", "NULL record: expected unresolved, got %s", r$resolution_status)

cat(sprintf("ALL %d CHECKS PASSED\n", n_checks))
