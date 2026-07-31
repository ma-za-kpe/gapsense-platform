# Public CI Curriculum Fixture

This public-safe fixture contains:

- the complete 176-cell Ghana/Uganda official-authority catalogue;
- the sanitized 140-record source ledger and exact artifact-availability/page metadata;
- both canonical country roots;
- an explicit, versioned zero-record projection manifest.

It proves the application can represent every researched official cell and source boundary while
distinguishing an intentionally empty public projection set from a missing or malformed data
mount.

It contains no raw source PDF, substantial official curriculum text, or normalized projection. The
pinned file-level contract retains private-repository artifact identifiers, byte counts, and
checksums for validation; the public API does not expose those implementation details. The rendered
source ledger exposes only purposeful official links, provenance, phase, edition, artifact
presence, extraction, rights, review, page count, and known-gap metadata.

Hosted validation selects this directory through `GAPSENSE_DATA_HOST_PATH`. Local development
mounts the sibling private `gapsense-data` repository and displays its 170 machine-extracted
candidate trees.
