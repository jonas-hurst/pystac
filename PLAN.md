# Plan

## Slice 1: Package scaffold + Item support for the two required fields
- [x] Done
- note: uv.lock revision was lowered from 5 to 3 in the slice commit; `uv lock`/`uv lock --check` resolve cleanly with the current uv and produce no diff, so it is a cosmetic metadata change, not a reproducibility problem.
- Delivers: `extensions/embeddings` becomes a registered uv workspace package (added to `[tool.uv.sources]` and `[tool.mypy] mypy_path`), with the vendored v1.0.0 JSON schema, a `pystac.extensions.embeddings` module exposing `EMBEDDINGS_EXTENSION_HOOKS`, `py.typed`, and a README. `ext.embeddings` on an `Item` reads/writes `emb:type` (`emb_type`) and `emb:dimensions` (`dimensions`) with validation. Tests set/get these on an Item, round-trip to dict, and assert an invalid `emb:type` raises `ValueError`.
- Check: `uv run pytest extensions/embeddings/tests`
- Depends on: none

## Slice 2: Item support for the remaining optional fields
- [ ] Done
- Delivers: `ext.embeddings` on an `Item` also reads/writes `emb:chip_size` (`chip_size`), `emb:stride` (`stride`), `emb:grid_id` (`grid_id`), `emb:temporal_period` (`temporal_period`), `emb:quantization_method` (`quantization_method`), `emb:original_data_type` (`original_data_type`), each validated on assignment (positive-integer array constraints, data-type enum). Tests cover each field.
- Check: `uv run pytest extensions/embeddings/tests`
- Depends on: 1

## Slice 3: Collection top-level fields + summaries
- [ ] Done
- Delivers: `ext.embeddings` on a `Collection` reads/writes all 8 fields at top level; `EmbeddingsExtension.summaries(collection)` reads/writes them as collection summaries. Adds the spec's example Collection as a fixture and tests the worked-example values (`emb_type == "chip"`, `dimensions == [768]`, `chip_size == [16, 16]`, `stride == [16, 16]`, `grid_id == "MAJORTOM"`).
- Check: `uv run pytest extensions/embeddings/tests`
- Depends on: 2

## Slice 4: Asset + Item Asset Definition support
- [ ] Done
- Delivers: `ext.embeddings` on an `Asset` and on an `ItemAssetDefinition` reads/writes all 8 fields. Adds the spec's example Item as a fixture and tests the worked-example values from the item's `embeddings` asset (`emb_type == "chip"`, `dimensions == [768]`). Confirms the workspace still lints, type-checks, and passes its core test suite.
- Check: `uv run pytest extensions/embeddings/tests`
- Depends on: 3

The "workspace still lints, type-checks, and passes its core test suite" requirement is cross-cutting; every slice must keep it green, and slice 4 explicitly confirms it.
