"""Tests for pystac.extensions.embeddings."""

from datetime import datetime
from pathlib import Path

import pytest

import pystac
from pystac.extensions.embeddings import EmbeddingsExtension

DATA_FILES = Path(__file__).resolve().parent / "data-files"

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
    ext = item.ext.emb
    assert isinstance(ext, EmbeddingsExtension)


def test_emb_type(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    assert "chip" == item.ext.emb.emb_type
    item.validate()


def test_dimensions(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    assert [768] == item.ext.emb.dimensions
    item.validate()


def test_invalid_emb_type(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.emb.emb_type = "not-a-valid-type"


def test_invalid_dimensions(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.emb.dimensions = [0]


def test_to_from_dict(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]

    d = item.to_dict()
    assert "chip" == d["properties"][TYPE_PROP]
    assert [768] == d["properties"][DIMENSIONS_PROP]

    item2 = pystac.Item.from_dict(d)
    assert "chip" == item2.ext.emb.emb_type
    assert [768] == item2.ext.emb.dimensions


def test_chip_size(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    item.ext.emb.chip_size = [16, 16]
    assert [16, 16] == item.ext.emb.chip_size
    item.validate()


def test_stride(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    item.ext.emb.stride = [16, 16]
    assert [16, 16] == item.ext.emb.stride
    item.validate()


def test_grid_id(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    item.ext.emb.grid_id = "MAJORTOM"
    assert "MAJORTOM" == item.ext.emb.grid_id
    item.validate()


def test_temporal_period(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    item.ext.emb.temporal_period = "P1Y"
    assert "P1Y" == item.ext.emb.temporal_period
    item.validate()


def test_quantization_method(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    item.ext.emb.quantization_method = "linear"
    assert "linear" == item.ext.emb.quantization_method
    item.validate()


def test_original_data_type(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    item.ext.emb.original_data_type = "float32"
    assert "float32" == item.ext.emb.original_data_type
    item.validate()


def test_invalid_chip_size(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.emb.chip_size = [16]
    with pytest.raises(ValueError):
        item.ext.emb.chip_size = [0, 16]
    with pytest.raises(ValueError):
        item.ext.emb.chip_size = [16, 16, 16]


def test_invalid_stride(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.emb.stride = [16]
    with pytest.raises(ValueError):
        item.ext.emb.stride = [-1, 16]


def test_invalid_original_data_type(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.emb.original_data_type = "not-a-data-type"


def test_invalid_temporal_period(item: pystac.Item) -> None:
    with pytest.raises(ValueError):
        item.ext.emb.temporal_period = "not-a-duration"


def test_to_from_dict_optional_fields(item: pystac.Item) -> None:
    item.ext.emb.emb_type = "chip"
    item.ext.emb.dimensions = [768]
    item.ext.emb.chip_size = [16, 16]
    item.ext.emb.stride = [16, 16]
    item.ext.emb.grid_id = "MAJORTOM"
    item.ext.emb.temporal_period = "P1Y"
    item.ext.emb.quantization_method = "linear"
    item.ext.emb.original_data_type = "float32"

    d = item.to_dict()
    assert [16, 16] == d["properties"][CHIP_SIZE_PROP]
    assert [16, 16] == d["properties"][STRIDE_PROP]
    assert "MAJORTOM" == d["properties"][GRID_ID_PROP]
    assert "P1Y" == d["properties"][TEMPORAL_PERIOD_PROP]
    assert "linear" == d["properties"][QUANTIZATION_METHOD_PROP]
    assert "float32" == d["properties"][ORIGINAL_DATA_TYPE_PROP]

    item2 = pystac.Item.from_dict(d)
    assert [16, 16] == item2.ext.emb.chip_size
    assert [16, 16] == item2.ext.emb.stride
    assert "MAJORTOM" == item2.ext.emb.grid_id
    assert "P1Y" == item2.ext.emb.temporal_period
    assert "linear" == item2.ext.emb.quantization_method
    assert "float32" == item2.ext.emb.original_data_type


@pytest.fixture
def collection() -> pystac.Collection:
    start = datetime(2023, 1, 1)
    end = datetime(2023, 12, 31)
    extent = pystac.Extent(
        pystac.SpatialExtent([[-180.0, -60.0, 180.0, 84.0]]),
        pystac.TemporalExtent([[start, end]]),
    )
    collection = pystac.Collection(
        id="test-collection",
        description="Test Collection",
        extent=extent,
    )
    EmbeddingsExtension.add_to(collection)
    return collection


@pytest.fixture
def example_collection() -> pystac.Collection:
    return pystac.Collection.from_file(str(DATA_FILES / "collection.json"))


def test_collection_ext_accessor(collection: pystac.Collection) -> None:
    ext = collection.ext.emb
    assert isinstance(ext, EmbeddingsExtension)


def test_collection_emb_type(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    assert "chip" == collection.ext.emb.emb_type
    assert "chip" == collection.extra_fields[TYPE_PROP]


def test_collection_dimensions(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    collection.ext.emb.dimensions = [768]
    assert [768] == collection.ext.emb.dimensions
    assert [768] == collection.extra_fields[DIMENSIONS_PROP]


def test_collection_chip_size(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    collection.ext.emb.dimensions = [768]
    collection.ext.emb.chip_size = [16, 16]
    assert [16, 16] == collection.ext.emb.chip_size
    assert [16, 16] == collection.extra_fields[CHIP_SIZE_PROP]


def test_collection_stride(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    collection.ext.emb.dimensions = [768]
    collection.ext.emb.stride = [16, 16]
    assert [16, 16] == collection.ext.emb.stride
    assert [16, 16] == collection.extra_fields[STRIDE_PROP]


def test_collection_grid_id(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    collection.ext.emb.dimensions = [768]
    collection.ext.emb.grid_id = "MAJORTOM"
    assert "MAJORTOM" == collection.ext.emb.grid_id
    assert "MAJORTOM" == collection.extra_fields[GRID_ID_PROP]


def test_collection_temporal_period(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    collection.ext.emb.dimensions = [768]
    collection.ext.emb.temporal_period = "P1Y"
    assert "P1Y" == collection.ext.emb.temporal_period
    assert "P1Y" == collection.extra_fields[TEMPORAL_PERIOD_PROP]


def test_collection_quantization_method(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    collection.ext.emb.dimensions = [768]
    collection.ext.emb.quantization_method = "linear"
    assert "linear" == collection.ext.emb.quantization_method
    assert "linear" == collection.extra_fields[QUANTIZATION_METHOD_PROP]


def test_collection_original_data_type(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    collection.ext.emb.dimensions = [768]
    collection.ext.emb.original_data_type = "float32"
    assert "float32" == collection.ext.emb.original_data_type
    assert "float32" == collection.extra_fields[ORIGINAL_DATA_TYPE_PROP]


def test_collection_invalid_emb_type(collection: pystac.Collection) -> None:
    with pytest.raises(ValueError):
        collection.ext.emb.emb_type = "not-a-valid-type"


def test_collection_to_from_dict(collection: pystac.Collection) -> None:
    collection.ext.emb.emb_type = "chip"
    collection.ext.emb.dimensions = [768]
    collection.ext.emb.chip_size = [16, 16]
    collection.ext.emb.stride = [16, 16]
    collection.ext.emb.grid_id = "MAJORTOM"
    collection.ext.emb.temporal_period = "P1Y"
    collection.ext.emb.quantization_method = "linear"
    collection.ext.emb.original_data_type = "float32"

    d = collection.to_dict()
    assert "chip" == d[TYPE_PROP]
    assert [768] == d[DIMENSIONS_PROP]
    assert [16, 16] == d[CHIP_SIZE_PROP]
    assert [16, 16] == d[STRIDE_PROP]
    assert "MAJORTOM" == d[GRID_ID_PROP]
    assert "P1Y" == d[TEMPORAL_PERIOD_PROP]
    assert "linear" == d[QUANTIZATION_METHOD_PROP]
    assert "float32" == d[ORIGINAL_DATA_TYPE_PROP]

    collection2 = pystac.Collection.from_dict(d)
    assert "chip" == collection2.ext.emb.emb_type
    assert [768] == collection2.ext.emb.dimensions
    assert [16, 16] == collection2.ext.emb.chip_size
    assert [16, 16] == collection2.ext.emb.stride
    assert "MAJORTOM" == collection2.ext.emb.grid_id
    assert "P1Y" == collection2.ext.emb.temporal_period
    assert "linear" == collection2.ext.emb.quantization_method
    assert "float32" == collection2.ext.emb.original_data_type


def test_example_collection_worked_example(
    example_collection: pystac.Collection,
) -> None:
    ext = example_collection.ext.emb
    assert "chip" == ext.emb_type
    assert [768] == ext.dimensions
    assert [16, 16] == ext.chip_size
    assert [16, 16] == ext.stride
    assert "MAJORTOM" == ext.grid_id


def test_summaries(collection: pystac.Collection) -> None:
    summaries = EmbeddingsExtension.summaries(collection)

    # Get
    assert summaries.emb_type is None
    assert summaries.dimensions is None

    # Set
    summaries.emb_type = ["chip"]
    summaries.dimensions = [[768]]
    summaries.chip_size = [[16, 16]]
    summaries.stride = [[16, 16]]
    summaries.grid_id = ["MAJORTOM"]
    summaries.temporal_period = ["P1Y"]
    summaries.quantization_method = ["linear"]
    summaries.original_data_type = ["float32"]

    assert ["chip"] == summaries.emb_type
    assert [[768]] == summaries.dimensions
    assert [[16, 16]] == summaries.chip_size
    assert [[16, 16]] == summaries.stride
    assert ["MAJORTOM"] == summaries.grid_id
    assert ["P1Y"] == summaries.temporal_period
    assert ["linear"] == summaries.quantization_method
    assert ["float32"] == summaries.original_data_type

    d = collection.to_dict()
    assert ["chip"] == d["summaries"][TYPE_PROP]
    assert [[768]] == d["summaries"][DIMENSIONS_PROP]


def test_summaries_example_collection(
    example_collection: pystac.Collection,
) -> None:
    summaries = EmbeddingsExtension.summaries(example_collection)
    assert ["chip"] == summaries.emb_type
    assert [[768]] == summaries.dimensions


def test_summaries_adds_uri(collection: pystac.Collection) -> None:
    collection.stac_extensions = []
    with pytest.raises(
        pystac.ExtensionNotImplemented,
        match="Extension 'emb' is not implemented",
    ):
        EmbeddingsExtension.summaries(collection, add_if_missing=False)

    EmbeddingsExtension.summaries(collection, add_if_missing=True)
    assert EmbeddingsExtension.get_schema_uri() in collection.stac_extensions


@pytest.fixture
def item_with_asset() -> pystac.Item:
    start = datetime(2023, 1, 1)
    item = pystac.Item(
        id="test-item", geometry=None, bbox=None, datetime=start, properties={}
    )
    EmbeddingsExtension.add_to(item)
    asset = pystac.Asset(
        href="https://example.org/data/embeddings.parquet",
        media_type="application/vnd.apache.parquet",
    )
    item.add_asset("embeddings", asset)
    return item


@pytest.fixture
def example_item() -> pystac.Item:
    return pystac.Item.from_file(str(DATA_FILES / "item.json"))


@pytest.fixture
def item_asset_defn() -> pystac.ItemAssetDefinition:
    return pystac.ItemAssetDefinition.create(
        title="Chip embedding vectors",
        description="Chip embedding vectors",
        media_type="application/vnd.apache.parquet",
        roles=["data", "embeddings"],
    )


def test_asset_ext_accessor(item_with_asset: pystac.Item) -> None:
    ext = item_with_asset.assets["embeddings"].ext.emb
    assert isinstance(ext, EmbeddingsExtension)


def test_asset_all_fields(item_with_asset: pystac.Item) -> None:
    asset = item_with_asset.assets["embeddings"]
    ext = asset.ext.emb

    ext.emb_type = "chip"
    ext.dimensions = [768]
    ext.chip_size = [16, 16]
    ext.stride = [16, 16]
    ext.grid_id = "MAJORTOM"
    ext.temporal_period = "P1Y"
    ext.quantization_method = "linear"
    ext.original_data_type = "float32"

    assert "chip" == ext.emb_type
    assert [768] == ext.dimensions
    assert [16, 16] == ext.chip_size
    assert [16, 16] == ext.stride
    assert "MAJORTOM" == ext.grid_id
    assert "P1Y" == ext.temporal_period
    assert "linear" == ext.quantization_method
    assert "float32" == ext.original_data_type

    assert "chip" == asset.extra_fields[TYPE_PROP]
    assert [768] == asset.extra_fields[DIMENSIONS_PROP]
    assert [16, 16] == asset.extra_fields[CHIP_SIZE_PROP]
    assert [16, 16] == asset.extra_fields[STRIDE_PROP]
    assert "MAJORTOM" == asset.extra_fields[GRID_ID_PROP]
    assert "P1Y" == asset.extra_fields[TEMPORAL_PERIOD_PROP]
    assert "linear" == asset.extra_fields[QUANTIZATION_METHOD_PROP]
    assert "float32" == asset.extra_fields[ORIGINAL_DATA_TYPE_PROP]


def test_asset_invalid_emb_type(item_with_asset: pystac.Item) -> None:
    asset = item_with_asset.assets["embeddings"]
    with pytest.raises(ValueError):
        asset.ext.emb.emb_type = "not-a-valid-type"


def test_asset_to_from_dict(item_with_asset: pystac.Item) -> None:
    asset = item_with_asset.assets["embeddings"]
    asset.ext.emb.emb_type = "chip"
    asset.ext.emb.dimensions = [768]

    d = item_with_asset.to_dict()
    asset_dict = d["assets"]["embeddings"]
    assert "chip" == asset_dict[TYPE_PROP]
    assert [768] == asset_dict[DIMENSIONS_PROP]

    item2 = pystac.Item.from_dict(d)
    asset2 = item2.assets["embeddings"]
    assert "chip" == asset2.ext.emb.emb_type
    assert [768] == asset2.ext.emb.dimensions


def test_item_asset_definition_ext_accessor(
    item_asset_defn: pystac.ItemAssetDefinition,
) -> None:
    ext = item_asset_defn.ext.emb
    assert isinstance(ext, EmbeddingsExtension)


def test_item_asset_definition_all_fields(
    item_asset_defn: pystac.ItemAssetDefinition,
) -> None:
    ext = item_asset_defn.ext.emb

    ext.emb_type = "chip"
    ext.dimensions = [768]
    ext.chip_size = [16, 16]
    ext.stride = [16, 16]
    ext.grid_id = "MAJORTOM"
    ext.temporal_period = "P1Y"
    ext.quantization_method = "linear"
    ext.original_data_type = "float32"

    assert "chip" == ext.emb_type
    assert [768] == ext.dimensions
    assert [16, 16] == ext.chip_size
    assert [16, 16] == ext.stride
    assert "MAJORTOM" == ext.grid_id
    assert "P1Y" == ext.temporal_period
    assert "linear" == ext.quantization_method
    assert "float32" == ext.original_data_type

    assert "chip" == item_asset_defn.properties[TYPE_PROP]
    assert [768] == item_asset_defn.properties[DIMENSIONS_PROP]
    assert [16, 16] == item_asset_defn.properties[CHIP_SIZE_PROP]
    assert [16, 16] == item_asset_defn.properties[STRIDE_PROP]
    assert "MAJORTOM" == item_asset_defn.properties[GRID_ID_PROP]
    assert "P1Y" == item_asset_defn.properties[TEMPORAL_PERIOD_PROP]
    assert "linear" == item_asset_defn.properties[QUANTIZATION_METHOD_PROP]
    assert "float32" == item_asset_defn.properties[ORIGINAL_DATA_TYPE_PROP]


def test_example_item_asset_worked_example(example_item: pystac.Item) -> None:
    asset = example_item.assets["embeddings"]
    ext = asset.ext.emb
    assert "chip" == ext.emb_type
    assert [768] == ext.dimensions
