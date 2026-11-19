"""Tests for pystac.extensions.embeddings."""

from datetime import datetime

import pytest

import pystac
from pystac.extensions.embeddings import EmbeddingsExtension

TYPE_PROP = "emb:type"
DIMENSIONS_PROP = "emb:dimensions"


@pytest.fixture
def item() -> pystac.Item:
    start = datetime(2023, 1, 1)
    item = pystac.Item(
        id="test-item", geometry=None, bbox=None, datetime=start, properties={}
    )
    EmbeddingsExtension.add_to(item)
    return item


def test_stac_extensions(item: pystac.Item) -> None:
    assert EmbeddingsExtension.has_extension(item)


def test_item_repr(item: pystac.Item) -> None:
    ext = EmbeddingsExtension.ext(item)
    assert f"<ItemEmbeddingsExtension Item id={item.id}>" == ext.__repr__()


def test_ext_embeddings_accessor(item: pystac.Item) -> None:
    ext = item.ext.embeddings
    assert isinstance(ext, EmbeddingsExtension)


def test_emb_type(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    assert "chip" == item.ext.embeddings.emb_type
    item.validate()


def test_dimensions(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    assert [768] == item.ext.embeddings.dimensions
    item.validate()


def test_invalid_emb_type(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.embeddings.emb_type = "not-a-valid-type"


def test_invalid_dimensions(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.embeddings.dimensions = [0]


def test_to_from_dict(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]

    d = item.to_dict()
    assert "chip" == d["properties"][TYPE_PROP]
    assert [768] == d["properties"][DIMENSIONS_PROP]

    item2 = pystac.Item.from_dict(d)
    assert "chip" == item2.ext.embeddings.emb_type
    assert [768] == item2.ext.embeddings.dimensions
