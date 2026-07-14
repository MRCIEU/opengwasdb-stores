#!/usr/bin/env bash
#
# Render the reports and assemble the docs/ site that GitHub Pages serves
# (Settings -> Pages -> Source: main branch, /docs folder).
#
# Requires `quarto` and `Rscript` on PATH (run inside your activated conda env,
# where conda's quarto activation has set QUARTO_SHARE_PATH etc.).
#
# docs/index.html and docs/.nojekyll are hand-maintained and not regenerated
# here. The imputation-filters report needs a ~2 GB summary-statistics download
# plus its knitr cache, so it is only refreshed when a local render already
# exists; render it explicitly with:
#   quarto render resources/scripts/mvp-imputation-filters.qmd
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
DOCS="$ROOT/docs"
mkdir -p "$DOCS"

echo "==> store-curation report"
quarto render resources/scripts/ebi-studies.qmd --to html

echo "==> prioritisation dashboard"
Rscript resources/scripts/make-dashboard.r

echo "==> assembling docs/"
install_html() { cp -f "$1" "$2" && echo "    $(basename "$2")"; }
install_html resources/scripts/ebi-studies.html                         "$DOCS/store-curation.html"
install_html resources/data/derived/store-prioritisation-dashboard.html "$DOCS/prioritisation-dashboard.html"
if [ -f resources/scripts/mvp-imputation-filters.html ]; then
  install_html resources/scripts/mvp-imputation-filters.html            "$DOCS/imputation-filters.html"
else
  echo "    (skipped imputation-filters.html — render it first to refresh)"
fi

echo "Done. Commit docs/ and push to update GitHub Pages."
