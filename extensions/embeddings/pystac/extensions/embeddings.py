"""Implements the :stac-ext:`Embeddings Extension <embeddings>`."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Generic, Literal, TypeVar, cast

import pystac
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
    SummariesExtension,
)
from pystac.extensions.hooks import ExtensionHooks

#: Generalized version of :class:`~pystac.Item`, :class:`~pystac.Collection`,
#: :class:`~pystac.Asset`, or :class:`~pystac.ItemAssetDefinition`
T = TypeVar(
    "T", pystac.Item, pystac.Collection, pystac.Asset, pystac.ItemAssetDefinition
)

SCHEMA_URI: str = "https://stac-extensions.github.io/embeddings/v1.0.0/schema.json"
PREFIX: str = "emb:"

# Field names
TYPE_PROP: str = PREFIX + "type"
DIMENSIONS_PROP: str = PREFIX + "dimensions"
CHIP_SIZE_PROP: str = PREFIX + "chip_size"
STRIDE_PROP: str = PREFIX + "stride"
GRID_ID_PROP: str = PREFIX + "grid_id"
TEMPORAL_PERIOD_PROP: str = PREFIX + "temporal_period"
QUANTIZATION_METHOD_PROP: str = PREFIX + "quantization_method"
ORIGINAL_DATA_TYPE_PROP: str = PREFIX + "original_data_type"

#: Valid values for the ``emb:type`` field.
VALID_TYPES: tuple[str, ...] = ("pixel", "chip")

#: Valid values for the ``emb:original_data_type`` field.
VALID_ORIGINAL_DATA_TYPES: tuple[str, ...] = (
    "int8",
    "int16",
    "int32",
    "int64",
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "float16",
    "float32",
    "float64",
    "cint16",
    "cint32",
    "cfloat32",
    "cfloat64",
)

#: Pattern for the ``emb:temporal_period`` ISO 8601 duration string, taken from the
#: v1.0.0 JSON schema.
TEMPORAL_PERIOD_PATTERN = re.compile(
    r"^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?$"
)


def validated_type(v: str) -> str:
    if not isinstance(v, str) or v not in VALID_TYPES:
        raise ValueError(
            f"Invalid emb:type: {v!r} must be one of {', '.join(VALID_TYPES)}"
        )
    return v


def validated_dimensions(v: list[int]) -> list[int]:
    if not isinstance(v, list) or len(v) < 1:
        raise ValueError(
            "Invalid emb:dimensions: must be a non-empty array of positive integers"
        )
    for i in v:
        if isinstance(i, bool) or not isinstance(i, int) or i < 1:
            raise ValueError(
                "Invalid emb:dimensions: all values must be positive integers"
            )
    return v


def validated_positive_int_pair(v: list[int], prop_name: str) -> list[int]:
    if not isinstance(v, list) or len(v) != 2:
        raise ValueError(
            f"Invalid {prop_name}: must be an array of two positive integers"
        )
    for i in v:
        if isinstance(i, bool) or not isinstance(i, int) or i < 1:
            raise ValueError(
                f"Invalid {prop_name}: all values must be positive integers"
            )
    return v


def validated_string(v: str, prop_name: str) -> str:
    if not isinstance(v, str):
        raise ValueError(f"Invalid {prop_name}: must be a string")
    return v


def validated_temporal_period(v: str) -> str:
    if not isinstance(v, str) or not TEMPORAL_PERIOD_PATTERN.fullmatch(v):
        raise ValueError(
            f"Invalid {TEMPORAL_PERIOD_PROP}: {v!r} must be an ISO 8601 duration"
        )
    return v


def validated_original_data_type(v: str) -> str:
    if not isinstance(v, str) or v not in VALID_ORIGINAL_DATA_TYPES:
        raise ValueError(
            f"Invalid {ORIGINAL_DATA_TYPE_PROP}: {v!r} must be one of "
            f"{', '.join(VALID_ORIGINAL_DATA_TYPES)}"
        )
    return v


class EmbeddingsExtension(
    Generic[T],
    PropertiesExtension,
    ExtensionManagementMixin[pystac.Item | pystac.Collection],
):
    """An abstract class that can be used to extend the properties of a
    :class:`~pystac.Item`, :class:`~pystac.Collection`, :class:`~pystac.Asset`, or
    :class:`~pystac.ItemAssetDefinition` with properties from the
    :stac-ext:`Embeddings Extension <embeddings>`. This class is generic over the type
    of STAC Object to be extended.

    To create a concrete instance of :class:`EmbeddingsExtension`, use the
    :meth:`EmbeddingsExtension.ext` method. For example:

    .. code-block:: python

       >>> item: pystac.Item = ...
       >>> emb_ext = EmbeddingsExtension.ext(item)
    """

    name: Literal["emb"] = "emb"

    @property
    def emb_type(self) -> str | None:
        """Get or sets the type of the embeddings.

        One of ``"pixel"`` or ``"chip"``.
        """
        return self._get_property(TYPE_PROP, str)

    @emb_type.setter
    def emb_type(self, v: str) -> None:
        self._set_property(TYPE_PROP, validated_type(v), pop_if_none=False)

    @property
    def dimensions(self) -> list[int] | None:
        """Get or sets the dimensions of the embeddings.

        A non-empty array of positive integers.
        """
        return self._get_property(DIMENSIONS_PROP, list[int])

    @dimensions.setter
    def dimensions(self, v: list[int]) -> None:
        self._set_property(DIMENSIONS_PROP, validated_dimensions(v), pop_if_none=False)

    @property
    def chip_size(self) -> list[int] | None:
        """Get or sets the chip size of the embeddings.

        An array of two positive integers representing ``[height, width]``.
        """
        return self._get_property(CHIP_SIZE_PROP, list[int])

    @chip_size.setter
    def chip_size(self, v: list[int]) -> None:
        self._set_property(
            CHIP_SIZE_PROP,
            validated_positive_int_pair(v, CHIP_SIZE_PROP),
            pop_if_none=False,
        )

    @property
    def stride(self) -> list[int] | None:
        """Get or sets the stride between neighbouring chips.

        An array of two positive integers representing ``[row_stride, col_stride]``.
        """
        return self._get_property(STRIDE_PROP, list[int])

    @stride.setter
    def stride(self, v: list[int]) -> None:
        self._set_property(
            STRIDE_PROP, validated_positive_int_pair(v, STRIDE_PROP), pop_if_none=False
        )

    @property
    def grid_id(self) -> str | None:
        """Get or sets the grid system the chips are aligned to."""
        return self._get_property(GRID_ID_PROP, str)

    @grid_id.setter
    def grid_id(self, v: str) -> None:
        self._set_property(
            GRID_ID_PROP, validated_string(v, GRID_ID_PROP), pop_if_none=False
        )

    @property
    def temporal_period(self) -> str | None:
        """Get or sets the temporal compositing period.

        An ISO 8601 duration string (e.g. ``P1Y``, ``P3M``).
        """
        return self._get_property(TEMPORAL_PERIOD_PROP, str)

    @temporal_period.setter
    def temporal_period(self, v: str) -> None:
        self._set_property(
            TEMPORAL_PERIOD_PROP, validated_temporal_period(v), pop_if_none=False
        )

    @property
    def quantization_method(self) -> str | None:
        """Get or sets the quantization method (e.g. ``linear``)."""
        return self._get_property(QUANTIZATION_METHOD_PROP, str)

    @quantization_method.setter
    def quantization_method(self, v: str) -> None:
        self._set_property(
            QUANTIZATION_METHOD_PROP,
            validated_string(v, QUANTIZATION_METHOD_PROP),
            pop_if_none=False,
        )

    @property
    def original_data_type(self) -> str | None:
        """Get or sets the data type of the embeddings before quantization."""
        return self._get_property(ORIGINAL_DATA_TYPE_PROP, str)

    @original_data_type.setter
    def original_data_type(self, v: str) -> None:
        self._set_property(
            ORIGINAL_DATA_TYPE_PROP,
            validated_original_data_type(v),
            pop_if_none=False,
        )

    @classmethod
    def get_schema_uri(cls) -> str:
        return SCHEMA_URI

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> EmbeddingsExtension[T]:
        """Extends the given STAC Object with properties from the
        :stac-ext:`Embeddings Extension <embeddings>`.

        This extension can be applied to instances of :class:`~pystac.Item`,
        :class:`~pystac.Collection`, :class:`~pystac.Asset`, or
        :class:`~pystac.ItemAssetDefinition`.

        Raises:

            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Item):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(EmbeddingsExtension[T], ItemEmbeddingsExtension(obj))
        elif isinstance(obj, pystac.Collection):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(EmbeddingsExtension[T], CollectionEmbeddingsExtension(obj))
        elif isinstance(obj, pystac.Asset):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(EmbeddingsExtension[T], AssetEmbeddingsExtension(obj))
        elif isinstance(obj, pystac.ItemAssetDefinition):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(EmbeddingsExtension[T], ItemAssetsEmbeddingsExtension(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))

    @classmethod
    def summaries(
        cls, obj: pystac.Collection, add_if_missing: bool = False
    ) -> SummariesEmbeddingsExtension:
        """Returns the extended summaries object for the given collection."""
        cls.ensure_has_extension(obj, add_if_missing)
        return SummariesEmbeddingsExtension(obj)


class ItemEmbeddingsExtension(EmbeddingsExtension[pystac.Item]):
    """A concrete implementation of :class:`EmbeddingsExtension` on an
    :class:`~pystac.Item` that extends the properties of the Item to include
    properties defined in the :stac-ext:`Embeddings Extension <embeddings>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`EmbeddingsExtension.ext` on an :class:`~pystac.Item` to extend it.
    """

    item: pystac.Item
    """The :class:`~pystac.Item` being extended."""

    properties: dict[str, Any]
    """The :class:`~pystac.Item` properties, including extension properties."""

    def __init__(self, item: pystac.Item) -> None:
        self.item = item
        self.properties = item.properties

    def __repr__(self) -> str:
        return f"<ItemEmbeddingsExtension Item id={self.item.id}>"


class CollectionEmbeddingsExtension(EmbeddingsExtension[pystac.Collection]):
    """A concrete implementation of :class:`EmbeddingsExtension` on a
    :class:`~pystac.Collection` that extends the top-level fields of the Collection to
    include properties defined in the :stac-ext:`Embeddings Extension <embeddings>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`EmbeddingsExtension.ext` on a :class:`~pystac.Collection` to extend it.
    """

    collection: pystac.Collection
    """The :class:`~pystac.Collection` being extended."""

    properties: dict[str, Any]
    """The :class:`~pystac.Collection` extra fields, including extension properties."""

    def __init__(self, collection: pystac.Collection) -> None:
        self.collection = collection
        self.properties = collection.extra_fields

    def __repr__(self) -> str:
        return f"<CollectionEmbeddingsExtension Collection id={self.collection.id}>"


class AssetEmbeddingsExtension(EmbeddingsExtension[pystac.Asset]):
    """A concrete implementation of :class:`EmbeddingsExtension` on an
    :class:`~pystac.Asset` that extends the Asset fields to include properties defined
    in the :stac-ext:`Embeddings Extension <embeddings>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`EmbeddingsExtension.ext` on an :class:`~pystac.Asset` to extend it.
    """

    asset_href: str
    """The ``href`` value of the :class:`~pystac.Asset` being extended."""

    properties: dict[str, Any]
    """The :class:`~pystac.Asset` fields, including extension properties."""

    additional_read_properties: Iterable[dict[str, Any]] | None = None
    """If present, this will be a list containing 1 dictionary representing the
    properties of the owning :class:`~pystac.Item`."""

    def __init__(self, asset: pystac.Asset) -> None:
        self.asset_href = asset.href
        self.properties = asset.extra_fields
        if asset.owner and isinstance(asset.owner, pystac.Item):
            self.additional_read_properties = [asset.owner.properties]

    def __repr__(self) -> str:
        return f"<AssetEmbeddingsExtension Asset href={self.asset_href}>"


class ItemAssetsEmbeddingsExtension(EmbeddingsExtension[pystac.ItemAssetDefinition]):
    """A concrete implementation of :class:`EmbeddingsExtension` on an
    :class:`~pystac.ItemAssetDefinition` that extends the Asset Definition fields to
    include properties defined in the :stac-ext:`Embeddings Extension <embeddings>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`EmbeddingsExtension.ext` on an :class:`~pystac.ItemAssetDefinition` to
    extend it.
    """

    properties: dict[str, Any]
    """The :class:`~pystac.ItemAssetDefinition` fields, including extension
    properties."""

    asset_definition: pystac.ItemAssetDefinition
    """The :class:`~pystac.ItemAssetDefinition` being extended."""

    def __init__(self, item_asset: pystac.ItemAssetDefinition) -> None:
        self.properties = item_asset.properties
        self.asset_definition = item_asset

    def __repr__(self) -> str:
        return "<ItemAssetsEmbeddingsExtension AssetDefinition={}>".format(
            self.asset_definition
        )


class SummariesEmbeddingsExtension(SummariesExtension):
    """A concrete implementation of :class:`~pystac.extensions.base.SummariesExtension`
    that extends the ``summaries`` field of a :class:`~pystac.Collection` to include
    properties defined in the :stac-ext:`Embeddings Extension <embeddings>`.
    """

    @property
    def emb_type(self) -> list[str] | None:
        """Get or sets the summary of :attr:`EmbeddingsExtension.emb_type` values
        for this Collection.
        """
        return self.summaries.get_list(TYPE_PROP)

    @emb_type.setter
    def emb_type(self, v: list[str] | None) -> None:
        self._set_summary(TYPE_PROP, v)

    @property
    def dimensions(self) -> list[list[int]] | None:
        """Get or sets the summary of :attr:`EmbeddingsExtension.dimensions` values
        for this Collection.
        """
        return self.summaries.get_list(DIMENSIONS_PROP)

    @dimensions.setter
    def dimensions(self, v: list[list[int]] | None) -> None:
        self._set_summary(DIMENSIONS_PROP, v)

    @property
    def chip_size(self) -> list[list[int]] | None:
        """Get or sets the summary of :attr:`EmbeddingsExtension.chip_size` values
        for this Collection.
        """
        return self.summaries.get_list(CHIP_SIZE_PROP)

    @chip_size.setter
    def chip_size(self, v: list[list[int]] | None) -> None:
        self._set_summary(CHIP_SIZE_PROP, v)

    @property
    def stride(self) -> list[list[int]] | None:
        """Get or sets the summary of :attr:`EmbeddingsExtension.stride` values
        for this Collection.
        """
        return self.summaries.get_list(STRIDE_PROP)

    @stride.setter
    def stride(self, v: list[list[int]] | None) -> None:
        self._set_summary(STRIDE_PROP, v)

    @property
    def grid_id(self) -> list[str] | None:
        """Get or sets the summary of :attr:`EmbeddingsExtension.grid_id` values
        for this Collection.
        """
        return self.summaries.get_list(GRID_ID_PROP)

    @grid_id.setter
    def grid_id(self, v: list[str] | None) -> None:
        self._set_summary(GRID_ID_PROP, v)

    @property
    def temporal_period(self) -> list[str] | None:
        """Get or sets the summary of :attr:`EmbeddingsExtension.temporal_period`
        values for this Collection.
        """
        return self.summaries.get_list(TEMPORAL_PERIOD_PROP)

    @temporal_period.setter
    def temporal_period(self, v: list[str] | None) -> None:
        self._set_summary(TEMPORAL_PERIOD_PROP, v)

    @property
    def quantization_method(self) -> list[str] | None:
        """Get or sets the summary of :attr:`EmbeddingsExtension.quantization_method`
        values for this Collection.
        """
        return self.summaries.get_list(QUANTIZATION_METHOD_PROP)

    @quantization_method.setter
    def quantization_method(self, v: list[str] | None) -> None:
        self._set_summary(QUANTIZATION_METHOD_PROP, v)

    @property
    def original_data_type(self) -> list[str] | None:
        """Get or sets the summary of :attr:`EmbeddingsExtension.original_data_type`
        values for this Collection.
        """
        return self.summaries.get_list(ORIGINAL_DATA_TYPE_PROP)

    @original_data_type.setter
    def original_data_type(self, v: list[str] | None) -> None:
        self._set_summary(ORIGINAL_DATA_TYPE_PROP, v)


class EmbeddingsExtensionHooks(ExtensionHooks):
    schema_uri: str = SCHEMA_URI
    prev_extension_ids: set[str] = set()
    stac_object_types = {
        pystac.STACObjectType.ITEM,
        pystac.STACObjectType.COLLECTION,
    }


EMBEDDINGS_EXTENSION_HOOKS: ExtensionHooks = EmbeddingsExtensionHooks()
