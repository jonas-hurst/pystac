"""Implements the Satellite extension.

https://github.com/stac-extensions/sat
"""

import enum
from datetime import datetime as Datetime
from typing import Dict, Any, Generic, Iterable, Optional, Set, TypeVar, cast

import pystac
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
)
from pystac.extensions.hooks import ExtensionHooks
from pystac.utils import str_to_datetime, datetime_to_str, map_opt

T = TypeVar("T", pystac.Item, pystac.Asset)

SCHEMA_URI = "https://stac-extensions.github.io/sat/v1.0.0/schema.json"

PREFIX: str = "sat:"
PLATFORM_INTERNATIONAL_DESIGNATOR_PROP: str = (
    PREFIX + "platform_international_designator"
)
ABSOLUTE_ORBIT_PROP: str = PREFIX + "absolute_orbit"
ORBIT_STATE_PROP: str = PREFIX + "orbit_state"
RELATIVE_ORBIT_PROP: str = PREFIX + "relative_orbit"
ANX_DATETIME_PROP: str = PREFIX + "anx_datetime"


class OrbitState(str, enum.Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"
    GEOSTATIONARY = "geostationary"


class SatExtension(
    Generic[T], PropertiesExtension, ExtensionManagementMixin[pystac.Item]
):
    """An abstract class that can be used to extend the properties of an
    :class:`~pystac.Item` or :class:`~pystac.Asset` with properties from the
    :stac-ext:`Satellite Extension <sat>`. This class is generic over the type of
    STAC Object to be extended (e.g. :class:`~pystac.Item`,
    :class:`~pystac.Collection`).

    To create a concrete instance of :class:`SatExtension`, use the
    :meth:`SatExtension.ext` method. For example:

    .. code-block:: python

       >>> item: pystac.Item = ...
       >>> sat_ext = SatExtension.ext(item)
    """

    def apply(
        self,
        orbit_state: Optional[OrbitState] = None,
        relative_orbit: Optional[int] = None,
        absolute_orbit: Optional[int] = None,
        platform_international_designator: Optional[str] = None,
        anx_datetime: Optional[Datetime] = None,
    ) -> None:
        """Applies ext extension properties to the extended :class:`~pystac.Item` or
        class:`~pystac.Asset`.

        Must specify at least one of orbit_state or relative_orbit in order
        for the sat extension to properties to be valid.

        Args:
            orbit_state : Optional state of the orbit. Either ascending or
                descending for polar orbiting satellites, or geostationary for
                geosynchronous satellites.
            relative_orbit : Optional non-negative integer of the orbit number at
                the time of acquisition.
        """

        self.platform_international_designator = platform_international_designator
        self.orbit_state = orbit_state
        self.absolute_orbit = absolute_orbit
        self.relative_orbit = relative_orbit
        self.anx_datetime = anx_datetime

    @property
    def platform_international_designator(self) -> Optional[str]:
        """Gets or sets the International Designator, also known as COSPAR ID, and
        NSSDCA ID."""
        return self._get_property(PLATFORM_INTERNATIONAL_DESIGNATOR_PROP, str)

    @platform_international_designator.setter
    def platform_international_designator(self, v: Optional[str]) -> None:
        self._set_property(PLATFORM_INTERNATIONAL_DESIGNATOR_PROP, v)

    @property
    def orbit_state(self) -> Optional[OrbitState]:
        """Get or sets an orbit state of the object."""
        return map_opt(
            lambda x: OrbitState(x), self._get_property(ORBIT_STATE_PROP, str)
        )

    @orbit_state.setter
    def orbit_state(self, v: Optional[OrbitState]) -> None:
        self._set_property(ORBIT_STATE_PROP, map_opt(lambda x: x.value, v))

    @property
    def absolute_orbit(self) -> Optional[int]:
        """Get or sets a absolute orbit number of the item."""
        return self._get_property(ABSOLUTE_ORBIT_PROP, int)

    @absolute_orbit.setter
    def absolute_orbit(self, v: Optional[int]) -> None:
        self._set_property(ABSOLUTE_ORBIT_PROP, v)

    @property
    def relative_orbit(self) -> Optional[int]:
        """Get or sets a relative orbit number of the item."""
        return self._get_property(RELATIVE_ORBIT_PROP, int)

    @relative_orbit.setter
    def relative_orbit(self, v: Optional[int]) -> None:
        self._set_property(RELATIVE_ORBIT_PROP, v)

    @property
    def anx_datetime(self) -> Optional[Datetime]:
        return map_opt(str_to_datetime, self._get_property(ANX_DATETIME_PROP, str))

    @anx_datetime.setter
    def anx_datetime(self, v: Optional[Datetime]) -> None:
        self._set_property(ANX_DATETIME_PROP, map_opt(datetime_to_str, v))

    @classmethod
    def get_schema_uri(cls) -> str:
        return SCHEMA_URI

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> "SatExtension[T]":
        """Extends the given STAC Object with properties from the :stac-ext:`Satellite
        Extension <sat>`.

        This extension can be applied to instances of :class:`~pystac.Item` or
        :class:`~pystac.Asset`.

        Raises:

            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Item):
            if add_if_missing:
                cls.add_to(obj)
            cls.validate_has_extension(obj)
            return cast(SatExtension[T], ItemSatExtension(obj))
        elif isinstance(obj, pystac.Asset):
            if add_if_missing and isinstance(obj.owner, pystac.Item):
                cls.add_to(obj.owner)
            cls.validate_has_extension(obj)
            return cast(SatExtension[T], AssetSatExtension(obj))
        else:
            raise pystac.ExtensionTypeError(
                f"Satellite extension does not apply to type '{type(obj).__name__}'"
            )


class ItemSatExtension(SatExtension[pystac.Item]):
    """A concrete implementation of :class:`SatExtension` on an :class:`~pystac.Item`
    that extends the properties of the Item to include properties defined in the
    :stac-ext:`Satellite Extension <sat>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`SatExtension.ext` on an :class:`~pystac.Item` to
    extend it.
    """

    item: pystac.Item
    """The :class:`~pystac.Item` being extended."""

    properties: Dict[str, Any]
    """The :class:`~pystac.Item` properties, including extension properties."""

    def __init__(self, item: pystac.Item):
        self.item = item
        self.properties = item.properties

    def __repr__(self) -> str:
        return "<ItemSatExtension Item id={}>".format(self.item.id)


class AssetSatExtension(SatExtension[pystac.Asset]):
    """A concrete implementation of :class:`SatExtension` on an :class:`~pystac.Asset`
    that extends the properties of the Asset to include properties defined in the
    :stac-ext:`Satellite Extension <sat>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`SatExtension.ext` on an :class:`~pystac.Asset` to
    extend it.
    """

    asset_href: str
    """The ``href`` value of the :class:`~pystac.Asset` being extended."""

    properties: Dict[str, Any]
    """The :class:`~pystac.Asset` fields, including extension properties."""

    additional_read_properties: Optional[Iterable[Dict[str, Any]]] = None
    """If present, this will be a list containing 1 dictionary representing the
    properties of the owning :class:`~pystac.Item`."""

    def __init__(self, asset: pystac.Asset):
        self.asset_href = asset.href
        self.properties = asset.properties
        if asset.owner and isinstance(asset.owner, pystac.Item):
            self.additional_read_properties = [asset.owner.properties]

    def __repr__(self) -> str:
        return "<AssetSatExtension Asset href={}>".format(self.asset_href)


class SatExtensionHooks(ExtensionHooks):
    schema_uri: str = SCHEMA_URI
    prev_extension_ids: Set[str] = set(["sat"])
    stac_object_types: Set[pystac.STACObjectType] = set([pystac.STACObjectType.ITEM])


SAT_EXTENSION_HOOKS: ExtensionHooks = SatExtensionHooks()
