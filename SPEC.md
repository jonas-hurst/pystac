# STAC Embeddings extension

## Problem

PySTAC users who work with geospatial embedding products (e.g. chip or pixel
embeddings produced by running a geospatial foundation model on Earth observation
data) need to read and write the STAC Embeddings extension fields (`emb:*`) on
Items and Collections. Without library support they must reach into raw JSON
`extra_fields`, which is error-prone, skips validation, and bypasses the normal
`ext` accessor that users expect from a supported extension.

## Solution

Add a new PySTAC extension package that implements the STAC Embeddings extension
v1.0.0, following the same pattern as the existing extension packages. It exposes
the `emb:*` fields as typed, validated properties on the object types the spec
allows, accessible through the standard `ext` accessor.

## User stories

1. As a PySTAC user, I want to read `emb:type`, `emb:dimensions`, and the other
   `emb:*` fields from an Item or Collection via `ext.embeddings`, so that I can
   consume embedding metadata without touching raw JSON.
2. As a PySTAC user, I want to set these fields with validation, so that invalid
   values are caught as early as possible.
3. As a PySTAC user, I want Collection summaries for these fields, so that a
   Collection can describe its embedding products at the collection level.

## Decisions

- Implement the STAC Embeddings extension at v1.0.0 (field prefix `emb`).
- Follow the existing extension package pattern: a separate workspace package.
- Support Collection top-level fields, Item properties, Collection summaries,
  Assets, and Item Asset Definitions.
- Name the Python property for `emb:type` `emb_type`, to avoid shadowing the
  builtin `type` and clashing with the STAC object `type` field.
- Validate values on assignment and raise `ValueError` on invalid input (enum
  values and the positive-integer array constraints).
- Do not model the extension's link relation types (`emb:encoder_model`,
  `emb:decoder_model`, `emb:benchmark`, `emb:grid`, `emb:quantization`) as helpers.
- Do not provide a helper for assets carrying the `embeddings` role.
- Do not support Catalogs or Bands for this extension.
- Target only v1.0.0; no extra version/migration logic beyond the base hook.
- Use the spec's example Item and Collection as test fixtures with known expected
  values.

## Checks

- Run the extension test suite with `uv run pytest extensions/embeddings/tests`.
- Known worked example (expected result known without running the code): reading
  the spec's example Collection yields `emb:type == "chip"`,
  `emb:dimensions == [768]`, `emb:chip_size == [16, 16]`,
  `emb:stride == [16, 16]`, and `emb:grid_id == "MAJORTOM"`; reading the example
  Item's embeddings asset yields `emb:type == "chip"` and `emb:dimensions == [768]`.
- Setting an invalid `emb:type` (a value other than `pixel` or `chip`) raises
  `ValueError`.
- The workspace still lints, type-checks, and passes its core test suite.

## Must keep working

- Existing PySTAC core behaviour and every other extension package keep passing
  their tests.
- The workspace still resolves and builds (uv sync / uv lock).
- The `ext` accessor continues to work for all existing extensions.
- Ruff linting, mypy type checking, and the docs build still pass.

## Out of scope

- Modeling the extension's link relation types.
- A helper for getting/setting assets with the `embeddings` role.
- Support for Catalogs or Bands for the `emb:*` fields.
- Support for extension versions other than v1.0.0 (no additional migration logic).
- Any functionality beyond reading, writing, and summarizing the `emb:*` fields.
