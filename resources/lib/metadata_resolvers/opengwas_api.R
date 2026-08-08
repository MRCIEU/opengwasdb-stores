# Metadata resolver for the `opengwas-gwas-vcf` Source Collection (issue
# #49; see docs/release-metadata-schema.md, "Metadata resolvers"). Resolves
# `stored_effect_scale`/`sample_size_kind`/`sample_size`/`n_cases`/
# `n_controls` from the OpenGWAS API's own study-level metadata ("gwasinfo"
# record), never from the source GWAS-VCF file's `##SAMPLE` header. This is
# the concrete motivating example from issue #15: `ieu-a-7` (Coronary Heart
# Disease) declares `StudyType=Continuous` in its VCF header with no
# case/control counts at all, while the OpenGWAS API JSON for the same
# study correctly reports `ncase=60801`/`ncontrol=123504`.
#
# Field names below (id, ncase, ncontrol, sample_size, ...) match the
# OpenGWAS API's own published GwasInfo schema
# (https://api.opengwas.io/api/swagger.json, definitions.GwasInfo).
#
# Conforms to the resolver contract established by
# resources/lib/metadata_resolvers/gwas_catalog_ssf.R (issue #48): one
# resolved record per Analysis, resolution_status always explicit.

suppressPackageStartupMessages(library(data.table))
source("resources/lib/metadata_resolvers/contract.R")

#' Resolve one study's analytical metadata from an already-fetched OpenGWAS
#' API "gwasinfo" record (see fetch_opengwas_gwasinfo() below to obtain
#' one). Deliberately takes the parsed record rather than an id and doing
#' the HTTP call itself, so this resolver stays independently testable via
#' fixture without a live network call or an API token.
#'
#' @param gwasinfo a named list as returned by one element of
#'   jsonlite::fromJSON() on an OpenGWAS API gwasinfo response: relevant
#'   fields are `ncase`, `ncontrol`, `sample_size` (all optional/nullable
#'   per the API's own schema).
#' @return a one-row data.table, same shape as
#'   resolve_gwas_catalog_ssf_metadata(): resolution_status,
#'   resolution_notes, stored_effect_scale, sample_size_kind, sample_size,
#'   n_cases, n_controls.
resolve_opengwas_api_metadata <- function(gwasinfo) {
  if (is.null(gwasinfo) || length(gwasinfo) == 0) {
    return(unresolved_metadata_record("no gwasinfo record returned by the OpenGWAS API"))
  }

  # The API represents "not applicable"/"unknown" counts inconsistently
  # (absent field, NULL, NA, or 0) depending on dataset vintage; treat all
  # of those as "not usable" rather than trusting a bare 0 case/control
  # count or sample size.
  as_count <- function(x) {
    if (is.null(x)) return(NA_real_)
    v <- suppressWarnings(as.numeric(x))
    if (length(v) == 0 || is.na(v) || v <= 0) NA_real_ else v
  }

  n_cases <- as_count(gwasinfo$ncase)
  n_controls <- as_count(gwasinfo$ncontrol)
  sample_size <- as_count(gwasinfo$sample_size)

  is_case_control <- !is.na(n_cases) && !is.na(n_controls)
  if (is_case_control) {
    return(data.table(
      resolution_status = "resolved",
      resolution_notes = NA_character_,
      stored_effect_scale = "log_or",
      sample_size_kind = "case_control",
      sample_size = if (!is.na(sample_size)) sample_size else n_cases + n_controls,
      n_cases = n_cases,
      n_controls = n_controls
    ))
  }

  if (!is.na(sample_size)) {
    return(data.table(
      resolution_status = "resolved",
      resolution_notes = NA_character_,
      stored_effect_scale = "sd",
      sample_size_kind = "total",
      sample_size = sample_size,
      n_cases = NA_real_,
      n_controls = NA_real_
    ))
  }

  unresolved_metadata_record("gwasinfo record had neither a usable ncase/ncontrol pair nor a usable sample_size")
}

#' Fetches one study's gwasinfo record from the live OpenGWAS API
#' (`GET /api/gwasinfo?id=<id>`). Requires an OpenGWAS API JWT (see
#' https://api.opengwas.io/) supplied via the OPENGWAS_JWT environment
#' variable or the `jwt` argument.
#'
#' This is registry-side metadata acquisition (resolving Analytical Metadata
#' before a build starts, per docs/adr/0017-opengwasdb-owns-shared-analysis-schema.md),
#' not a reusable source reader in the sense
#' docs/adr/0012-manifest-generators-own-orchestration-only.md reserves for
#' OpenGWASDB: nothing here reads GWAS summary-statistics rows, and
#' OpenGWASDB's build engine never needs to call this API itself (by build
#' time, the resolved scalars already live in analyses.tsv). Registry-side
#' network acquisition of external build-input data already has precedent
#' in this repository (resources/scripts/ld-panel/acquire_hgdp1kgp.py).
#'
#' Not exercised by this repository's automated tests: this repository's
#' test suites are documented as data-only and network-free (see
#' resources/scripts/run_all_tests.py), and a live call additionally needs a
#' per-user secret token. resolve_opengwas_api_metadata() above is the
#' tested, independently callable part of this resolver; this function is
#' the thin, untested transport it is deliberately decoupled from.
#'
#' @param id OpenGWAS study ID, e.g. "ieu-a-7".
#' @param jwt OpenGWAS API bearer token.
#' @return a parsed gwasinfo record (named list) for `id`, or NULL if the
#'   API returned no record for it.
fetch_opengwas_gwasinfo <- function(id, jwt = Sys.getenv("OPENGWAS_JWT")) {
  if (!requireNamespace("httr", quietly = TRUE) || !requireNamespace("jsonlite", quietly = TRUE)) {
    stop("fetch_opengwas_gwasinfo() requires the httr and jsonlite packages")
  }
  if (!nzchar(jwt)) {
    stop("fetch_opengwas_gwasinfo() requires an OpenGWAS API JWT (set OPENGWAS_JWT or pass jwt=)")
  }
  response <- httr::GET(
    "https://api.opengwas.io/api/gwasinfo",
    query = list(id = id),
    httr::add_headers(Authorization = paste("Bearer", jwt))
  )
  httr::stop_for_status(response)
  parsed <- jsonlite::fromJSON(
    httr::content(response, "text", encoding = "UTF-8"),
    simplifyVector = FALSE
  )
  if (is.null(parsed) || length(parsed) == 0) return(NULL)
  parsed[[1]]
}
