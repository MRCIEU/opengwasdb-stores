# QC panel before/after comparison (issue #31)

Re-running the 80-analysis metabolome-plasma-2023 pilot (issue #27 baseline)
with the fixed QC panel enabled (`filter.qc_panel`, issue #28/#29/#30),
without changing anything else about selection, thresholds, or gates.

## Ancestry assignment (`sidecars/ancestry.tsv`)

| | Baseline (#27) | With QC panel (#31) |
|---|---:|---:|
| `af_assigned` | 45 | **80** |
| `unassigned` (`gate_reason: overlap`) | 35 | **0** |
| `checks.ancestry` | `passed_with_warnings` | **`passed`** |
| `af_overlap` range | 8 - 73,609 | 4,908 - 80,614 |
| `source_assigned_mismatch = true` | 0 | 0 |

Every one of the 35 Analyses that previously gated out on `overlap` (all with
`af_overlap` under 100, several under 20) now clears `gates.n_min: 200` by
more than an order of magnitude (minimum overlap after enabling the panel:
4,908) and gets assigned correctly.

**No previously-correct conclusion changed**: all 45 Analyses that were
already `af_assigned` in the baseline keep the exact identical
`assigned_ancestry` after enabling the QC panel (verified analysis-by-analysis,
zero differences), and none of the newly-assigned 35 disagree with their
source-declared ancestry (`source_assigned_mismatch = false` for all 80). The
panel added statistical power to previously-starved Analyses; it did not
change any well-supported answer.

## Effect-scale validation (`sidecars/sd_estimation.tsv`)

| | Baseline (#27) | With QC panel (#31) |
|---|---:|---:|
| `passed` | 70 | **80** |
| `skipped` (`low_overlap`) | 10 | **0** |
| `checks.effect_scale` / `checks.sd_estimation` | `passed` / `passed` | `passed` / `passed` |

The 10 Analyses that previously skipped effect-scale validation for lacking
enough reference-AF overlap now have the QC panel's variants available and
pass.

## Interpretation

This confirms the issue #28 hypothesis directly: the 35 ancestry
gate-failures (and 10 effect-scale skips) in the #27 baseline were an
artifact of the signal-driven sparse-region filter starving low-power
Analyses of retained variants, not evidence of genuine ancestry ambiguity or
unvalidatable effect scale. Retaining a fixed, always-present QC panel
resolves this without altering any conclusion that already had adequate
support.
