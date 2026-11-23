# Plan

## Slice 5: Add the embeddings extension API reference page
- [ ] Done
- Delivers: New `docs/api/extensions/embeddings.rst` page documenting `pystac.extensions.embeddings`, in the same style as the other extension pages (`automodule` with `:members:` and `:undoc-members:`). The `:glob:` toctree in `docs/api/extensions.rst` picks it up, registering `EmbeddingsExtension` as a valid cross-reference target, so the four `py:class reference target not found: pystac.extensions.embeddings.EmbeddingsExtension` warnings disappear and the docs build passes with `-W --keep-going -n`.
- Check: `uv run make -C docs html SPHINXOPTS="-W --keep-going -n"`
- Depends on: none

## Slice 6: Register the embeddings class in the extensions autosummary
- [ ] Done
- Delivers: `embeddings.EmbeddingsExtension` added to the autosummary in `docs/api/extensions.rst`, so it appears in the extensions index table alongside the other extension classes.
- Check: `uv run make -C docs html SPHINXOPTS="-W --keep-going -n"`
- Depends on: 5

## Slice 7: List the embeddings extension in the API reference index
- [ ] Done
- Delivers: The embeddings extension added to the Extensions list in `docs/api.rst`, so it appears in the narrative Extensions section of the API reference index.
- Check: `uv run make -C docs html SPHINXOPTS="-W --keep-going -n"`
- Depends on: 5
