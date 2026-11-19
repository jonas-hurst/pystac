"""Tests for pystac.extensions.embeddings."""

from datetime import datetime

import pytest

import pystac
from pystac.extensions.embeddings import EmbeddingsExtension

TYPE_PROP = "emb:type"
DIMENSIONS_PROP = "emb:dimensions"
CHIP_SIZE_PROP = "emb:chip_size"
STRIDE_PROP = "emb:stride"
GRID_ID_PROP = "emb:grid_id"
TEMPORAL_PERIOD_PROP = "emb:temporal_period"
QUANTIZATION_METHOD_PROP = "emb:quantization_method"
ORIGINAL_DATA_TYPE_PROP = "emb:original_data_type"


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


def test_chip_size(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    item.ext.embeddings.chip_size = [16, 16]
    assert [16, 16] == item.ext.embeddings.chip_size
    item.validate()


def test_stride(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    item.ext.embeddings.stride = [16, 16]
    assert [16, 16] == item.ext.embeddings.stride
    item.validate()


def test_grid_id(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    item.ext.embeddings.grid_id = "MAJORTOM"
    assert "MAJORTOM" == item.ext.embeddings.grid_id
    item.validate()


def test_temporal_period(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    item.ext.embeddings.temporal_period = "P1Y"
    assert "P1Y" == item.ext.embeddings.temporal_period
    item.validate()


def test_quantization_method(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    item.ext.embeddings.quantization_method = "linear"
    assert "linear" == item.ext.embeddings.quantization_method
    item.validate()


def test_original_data_type(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    item.ext.embeddings.original_data_type = "float32"
    assert "float32" == item.ext.embeddings.original_data_type
    item.validate()


def test_invalid_chip_size(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.embeddings.chip_size = [16]
    with pytest.raises(ValueError):
        item.ext.embeddings.chip_size = [0, 16]
    with pytest.raises(ValueError):
        item.ext.embeddings.chip_size = [16, 16, 16]


def test_invalid_stride(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.embeddings.stride = [16]
    with pytest.raises(ValueError):
        item.ext.embeddings.stride = [-1, 16]


def test_invalid_original_data_type(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.embeddings.original_data_type = "not-a-data-type"


def test_invalid_temporal_period(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.embeddings.temporal_period = "not-a-duration"


def test_to_from_dict_optional_fields(item: pystac.Item) -> None:
    item.ext.embeddings.emb_type = "chip"
    item.ext.embeddings.dimensions = [768]
    item.ext.embeddings.chip_size = [16, 16]
    item.ext.embeddings.stride = [16, 16]
    item.ext.embeddings.grid_id = "MAJORTOM"
    item.ext.embeddings.temporal_period = "P1Y"
    item.ext.embeddings.quantization_method = "linear"
    item.ext.embeddings.original_data_type = "float32"

    d = item.to_dict()
    assert [16, 16] == d["properties"][CHIP_SIZE_PROP]
    assert [16, 16] == d["properties"][STRIDE_PROP]
    assert "MAJORTOM" == d["properties"][GRID_ID_PROP]
    assert "P1Y" == d["properties"][TEMPORAL_PERIOD_PROP]
    assert "linear" == d["properties"][QUANTIZATION_METHOD_PROP]
    assert "float32" == d["properties"][ORIGINAL_DATA_TYPE_PROP]

    item2 = pystac.Item.from_dict(d)
    assert [16, 16] == item2.ext.embeddings.chip_size
    assert [16, 16] == item2.ext.embeddings.stride
    assert "MAJORTOM" == item2.ext.embeddings.grid_id
    assert "P1Y" == item2.ext.embeddings.temporal_period
    assert "linear" == item2.ext.embeddings.quantization_method
    assert "float32" == item2.ext.embeddings.original_data_type
