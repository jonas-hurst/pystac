"""Implements the :stac-ext:`Embeddings Extension <embeddings>`."""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar, cast

import pystac
from pystac.extensions.base import ExtensionManagementMixin, PropertiesExtension
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

#: Valid values for the ``emb:type`` field.
VALID_TYPES: tuple[str, ...] = ("pixel", "chip")


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


class EmbeddingsExtension(
    Generic[T],
    PropertiesExtension,
    ExtensionManagementMixin[pystac.Item | pystac.Collection],
):
    """An abstract class that can be used to extend the properties of a
    :class:`~pystac.Item` (or later, a :class:`~pystac.Collection`,
    :class:`~pystac.Asset`, or :class:`~pystac.ItemAssetDefinition`) with properties
    from the :stac-ext:`Embeddings Extension <embeddings>`. This class is generic over
    the type of STAC Object to be extended.

    To create a concrete instance of :class:`EmbeddingsExtension`, use the
    :meth:`EmbeddingsExtension.ext` method. For example:

    .. code-block:: python

       >>> item: pystac.Item = ...
       >>> emb_ext = EmbeddingsExtension.ext(item)
    """

    name: Literal["embeddings"] = "embeddings"

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

    @classmethod
    def get_schema_uri(cls) -> str:
        return SCHEMA_URI

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> EmbeddingsExtension[T]:
        """Extends the given STAC Object with properties from the
        :stac-ext:`Embeddings Extension <embeddings>`.

        This extension can be applied to instances of :class:`~pystac.Item`.

        Raises:

            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Item):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(EmbeddingsExtension[T], ItemEmbeddingsExtension(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))


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


class EmbeddingsExtensionHooks(ExtensionHooks):
    schema_uri: str = SCHEMA_URI
    prev_extension_ids: set[str] = set()
    stac_object_types = {pystac.STACObjectType.ITEM}


EMBEDDINGS_EXTENSION_HOOKS: ExtensionHooks = EmbeddingsExtensionHooks()
