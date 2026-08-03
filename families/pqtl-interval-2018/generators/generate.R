#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (!any(grepl("^--config=", args))) {
  args <- c("--config=families/pqtl-interval-2018/generators/config.yaml", args)
}

status <- system2(
  "Rscript",
  c("resources/generators/gwas-ssf-ragged/generate.R", args)
)
quit(status = status)
