# OpenGWASDB Store Operations

This context describes the planning and operational language for expected and produced OpenGWASDB store assets.

## Language

**Store Registry**:
The authoritative record of intended and produced Store Releases, including their identity, source inputs, build recipes, release lineage, and operational priority.
_Avoid_: catalogue, service catalogue

**Access Posture**:
The declared availability category for a Source Collection, Store Family, or Store Release, such as public, controlled, or embargoed.
_Avoid_: access control, authorisation

**Build Priority**:
Store Family or Store Release metadata used to decide what should be produced next, based on value, readiness, cost, risk, and strategic fit.
_Avoid_: scheduler state, job priority

**Store Family**:
A named collection of related Store Releases built from one Source Collection and sharing an intended biological scope, source release process, access posture, release cadence, and query or discovery promise.
_Avoid_: project, dataset group

**Candidate Store Family**:
A proposed Store Family being assessed for value, readiness, cost, risk, and scope before receiving a permanent Store Family ID.
_Avoid_: draft release, planned store

**Store Family ID**:
A stable human-readable slug for a Store Family that may appear in paths, manifests, APIs, documentation, and citations, and must not be repurposed after publication.
_Avoid_: opaque family ID, display name

**Source Collection**:
A homogeneous upstream set of summary-statistics inputs with one Source Format and one Source Reader Capability, recorded with its provider, provenance, location, access constraints, and validation state.
_Avoid_: input folder, data dump

**Source Inventory**:
A discovered list or snapshot of upstream Analyses available in a Source Collection, including source IDs, locations, checksums, sizes, and basic readiness metadata where available.
_Avoid_: release manifest, store manifest

**Source Bundle**:
A named group of source files shared by one or more Analyses when a single `source_file` column is insufficient.
_Avoid_: store release, source collection

**Source Format**:
The structural format of upstream summary-statistics inputs, such as GWAS-VCF, GWAS-SSF, BESD, or custom tabular.
_Avoid_: source collection, store layout

**Source Reader Capability**:
The OpenGWASDB capability assigned to a Source Collection for reading and normalising all analyses in that collection.
_Avoid_: source format, build recipe

**Manifest Generator**:
A Store Family-specific orchestration program that discovers or selects upstream inputs from the family's Source Collection and emits a Release Manifest candidate.
_Avoid_: selector, manifest script

**Release Manifest**:
A standardised, declarative, accepted bundle describing the concrete Analyses, Traits, files, checksums, metadata, and build inputs from one Source Collection for one Store Release.
_Avoid_: study list, input list

**Analysis**:
One statistical analysis of one Trait, producing associations between that Trait and variants. Every Analysis in a Release Manifest has a stable registry analysis ID and a trait ID.
_Avoid_: dataset, trait, phenotype

**Source Analysis ID**:
The analysis identifier supplied by the upstream Source Collection and preserved in the Release Manifest as provenance.
_Avoid_: analysis ID, trait ID

**Trait**:
A measured or derived biological outcome analysed against genetic variants. Every Trait in a Release Manifest has a trait ID, assigned by the registry when a stable upstream ID is unavailable.
_Avoid_: phenotype, analysis

**Source Trait ID**:
The trait identifier supplied by the upstream Source Collection and preserved in the Release Manifest as provenance.
_Avoid_: trait ID, analysis ID

**Release Manifest Candidate**:
The output of a Manifest Generator before it has been accepted as the reproducible input record for a Store Release.
_Avoid_: draft release, generated release

**Build Recipe**:
A declarative description of the release shape to produce from an accepted Release Manifest, including layout, completion mode, indexing, validation, and execution parameters.
_Avoid_: pipeline, script, release manifest

**Reference Resource**:
An auxiliary build-time resource such as an LD reference panel or genome reference used by a Build Recipe without becoming the Source Collection for a Store Family.
_Avoid_: source collection, store family

**Store Layout**:
The storage organisation used for a Store Release, such as dense observed-only, dense reference-completed, ragged observed-only, or ragged reference-completed.
_Avoid_: store family, source format

**Store Release**:
A versioned, immutable, validated OpenGWASDB analytical asset within a Store Family, produced from an accepted Release Manifest and material Build Recipe choices.
_Avoid_: database, live store

**Release Lineage**:
The relationship between Store Releases in a Store Family, including observed-only releases, reference-completed releases, corrected releases, and other derived releases.
_Avoid_: family hierarchy, source lineage

**Release Status**:
The registry lifecycle state for a release bundle: candidate, accepted, built, validated, superseded, or withdrawn.
_Avoid_: job state, scheduler state

**Association Coverage**:
Release-level metadata describing what associations are expected to be present, such as full GWAS, cis, trans, cis-plus-signals, top hits, or unknown.
_Avoid_: per-analysis coverage

**Validation Record**:
A release-level summary of validation status, checks, tool versions, timestamps, and pointers to detailed logs or benchmark reports.
_Avoid_: validation log, build report

**Family Release ID**:
A stable release identifier that is unique within a Store Family and follows the naming convention natural to that family's source or release process.
_Avoid_: global version, universal release version

**Trait Annotation**:
Descriptive metadata about traits in a Store Release that may be curated after release without changing the analytical asset itself.
_Avoid_: trait release, study manifest

**Source Trait Label**:
The trait label supplied by the upstream Source Collection and preserved in the Release Manifest as provenance.
_Avoid_: curated trait label, analysis label

**Analytical Metadata**:
Metadata that affects the interpretation of association statistics in a Store Release, such as sample size, ancestry, genome build, units, case-control counts, allele conventions, and harmonisation assumptions.
_Avoid_: trait annotation, display metadata

**Effect Scale**:
The OpenGWASDB controlled vocabulary value describing the scale of stored effects for an Analysis, such as `sd_units`, `log_or`, or `log_hazard`.
_Avoid_: source effect label

**Source Ancestry Label**:
The ancestry or population label supplied by the upstream Source Collection and preserved as provenance.
_Avoid_: assigned ancestry

**Assigned Ancestry**:
The registry-normalised ancestry label used for store inclusion, routing, grouping, and ancestry-specific build choices.
_Avoid_: source ancestry label

**Ancestry Assignment Method**:
The controlled value describing how Assigned Ancestry was produced, such as AF-based assignment, source fallback, source trusted because allele frequencies were unavailable, or unassigned.
_Avoid_: ancestry confidence, ancestry status

**Sample Size Metadata**:
Analysis-level or variant-level metadata describing participant count, case-control counts, effective sample size, or unknown sample-size semantics.
_Avoid_: sample size

**Source License**:
The licence or usage terms attached to an upstream Analysis or source file, inherited from the Source Collection default unless overridden per Analysis.
_Avoid_: access posture, authorisation

**Publication Metadata**:
Compact bibliographic provenance for an Analysis or Source Collection, such as DOI, PMID, and consortium.
_Avoid_: trait annotation, analytical metadata

**Release Erratum**:
A recorded correction or warning for a published Store Release, used when an analytical interpretation issue is discovered after publication.
_Avoid_: metadata update, silent fix
