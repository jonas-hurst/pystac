import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Any, cast

import jsonschema
import pytest
from requests_mock import Mocker

import pystac
import pystac.validation
from pystac.cache import CollectionCache
from pystac.serialization.common_properties import merge_common_properties
from pystac.utils import get_opt
from pystac.validation import GetSchemaError, JsonSchemaSTACValidator
from tests.utils import TestCases
from tests.utils.test_cases import ExampleInfo


class TestValidate:
    @pytest.mark.vcr()
    def test_validate_current_version(self) -> None:
        catalog = pystac.read_file(
            TestCases.get_path("data-files/catalogs/test-case-1/catalog.json")
        )
        catalog.validate()

        collection = pystac.read_file(
            TestCases.get_path(
                "data-files/catalogs/test-case-1//country-1/area-1-1/collection.json"
            )
        )
        collection.validate()

        item = pystac.read_file(TestCases.get_path("data-files/item/sample-item.json"))
        item.validate()

    @pytest.mark.vcr()
    @pytest.mark.parametrize("example", TestCases.get_examples_info())
    def test_validate_examples(self, example: ExampleInfo) -> None:
        stac_version = example.stac_version
        path = example.path
        valid = example.valid

        with open(path, encoding="utf-8") as f:
            stac_json = json.load(f)

        # Check if common properties need to be merged
        if stac_version < "1.0" and example.object_type == pystac.STACObjectType.ITEM:
            collection_cache = CollectionCache()
            merge_common_properties(stac_json, collection_cache, path)

        if valid:
            pystac.validation.validate_dict(stac_json)
        else:
            with pytest.raises(pystac.STACValidationError):
                try:
                    pystac.validation.validate_dict(stac_json)
                except pystac.STACValidationError as e:
                    assert isinstance(e.source, list)
                    assert isinstance(e.source[0], jsonschema.ValidationError)
                    raise e

    @pytest.mark.vcr()
    def test_validate_error_contains_href(self) -> None:
        # Test that the exception message contains the HREF of the object if available.
        cat = TestCases.case_1()
        item = next(cat.get_items("area-1-1-labels", recursive=True))
        assert item.get_self_href() is not None

        item.geometry = {"type": "INVALID"}

        with pytest.raises(pystac.STACValidationError):
            try:
                item.validate()
            except pystac.STACValidationError as e:
                assert get_opt(item.get_self_href()) in str(e)
                raise e

    @pytest.mark.vcr()
    def test_validate_all_deprecated_dict_arg(self) -> None:
        catalog = TestCases.case_1()

        with pytest.warns(DeprecationWarning, match="use validate_all_dict"):
            pystac.validation.validate_all(catalog.to_dict(), catalog.get_self_href())

    @pytest.mark.vcr()
    def test_validate_all_deprecated_dict_arg_missing_href(self) -> None:
        catalog = TestCases.case_1()

        with pytest.warns(DeprecationWarning, match="use validate_all_dict"):
            with pytest.raises(ValueError, match="href must be set"):
                pystac.validation.validate_all(catalog.to_dict())

    @pytest.mark.vcr()
    def test_validate_all_unexpected_href(self) -> None:
        catalog = TestCases.case_1()

        with pytest.raises(ValueError, match="href must be None"):
            pystac.validation.validate_all(catalog, catalog.get_self_href())

    @pytest.mark.vcr()
    def test_validate_all(self) -> None:
        catalog = TestCases.case_1()

        pystac.validation.validate_all(catalog)

    @pytest.mark.vcr()
    @pytest.mark.parametrize("test_case", TestCases.all_test_catalogs())
    def test_validate_all_dict(self, test_case: pystac.Catalog) -> None:
        catalog_href = test_case.get_self_href()
        if catalog_href is not None:
            stac_dict = pystac.StacIO.default().read_json(catalog_href)

            pystac.validation.validate_all_dict(stac_dict, catalog_href)

        # Modify a 0.8.1 collection in a catalog to be invalid with a
        # since-renamed extension and make sure it catches the validation error.

        with tempfile.TemporaryDirectory() as tmp_dir:
            dst_dir = os.path.join(tmp_dir, "catalog")
            # Copy test case 7 to the temporary directory
            catalog_href = get_opt(TestCases.case_7().get_self_href())
            shutil.copytree(os.path.dirname(catalog_href), dst_dir)

            new_cat_href = os.path.join(dst_dir, "catalog.json")

            # Make sure it's valid before modification
            pystac.validation.validate_all_dict(
                pystac.StacIO.default().read_json(new_cat_href), new_cat_href
            )

            # Modify a contained collection to add an extension for which the
            # collection is invalid.
            with open(
                os.path.join(dst_dir, "acc/collection.json"), encoding="utf-8"
            ) as f:
                col = json.load(f)
            col["stac_extensions"] = ["asset"]
            with open(
                os.path.join(dst_dir, "acc/collection.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(col, f)

            stac_dict = pystac.StacIO.default().read_json(new_cat_href)

            with pytest.raises(pystac.STACValidationError):
                pystac.validation.validate_all_dict(stac_dict, new_cat_href)

    @pytest.mark.vcr()
    def test_validates_geojson_with_tuple_coordinates(self) -> None:
        """This unit tests guards against a bug where if a geometry
        dict has tuples instead of lists for the coordinate sequence,
        which can be produced by shapely, then the geometry still passes
        validation.
        """
        geom: dict[str, Any] = {
            "type": "Polygon",
            # Last , is required to ensure tuple creation.
            "coordinates": (
                (
                    (-115.305, 36.126),
                    (-115.305, 36.128),
                    (-115.307, 36.128),
                    (-115.307, 36.126),
                    (-115.305, 36.126),
                ),
            ),
        }

        item = pystac.Item(
            id="test-item",
            geometry=geom,
            bbox=[-115.308, 36.126, -115.305, 36.129],
            datetime=datetime.now(timezone.utc),
            properties={},
        )

        # Should not raise.
        item.validate()

    @pytest.mark.vcr()
    def test_validate_custom_validator(self) -> None:
        """This test verifies the use of a custom validator class passed as
        input to :meth:`~pystac.stac_object.STACObject.validate` and every
        underlying function. This validator is effective only for the call
        for which it was provided, contrary to
        :class:`~pystac.validation.RegisteredValidator`
        that persists it globally until reset.
        """
        custom_extension_uri = (
            "https://stac-extensions.github.io/custom-extension/v1.0.0/schema.json"
        )
        custom_extension_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": f"{custom_extension_uri}#",
            "type": "object",
            "properties": {
                "properties": {
                    "type": "object",
                    "required": ["custom-extension:test"],
                    "properties": {"custom-extension:test": {"type": "integer"}},
                }
            },
        }
        item = cast(
            pystac.Item,
            pystac.read_file(TestCases.get_path("data-files/item/sample-item.json")),
        )
        item.stac_extensions.append(custom_extension_uri)
        item.properties["custom-extension:test"] = 123

        with pytest.raises(pystac.validation.GetSchemaError):
            item.validate()  # default validator does not know the extension

        class CustomValidator(JsonSchemaSTACValidator):
            def _get_schema(self, schema_uri: str) -> dict[str, Any]:
                if schema_uri == custom_extension_uri:
                    return custom_extension_schema
                return super()._get_schema(schema_uri)

        # validate that the custom schema is found with the custom validator
        custom_validator = CustomValidator()
        item.validate(validator=custom_validator)

        # make sure validation is effective
        item.properties["custom-extension:test"] = "bad-value"
        with pytest.raises(pystac.errors.STACValidationError):
            item.validate(validator=custom_validator)

        # verify that the custom validator is not persisted
        with pytest.raises(pystac.validation.GetSchemaError):
            item.validate()


@pytest.mark.block_network
def test_catalog_latest_version_uses_local(catalog: pystac.Catalog) -> None:
    assert catalog.validate()


@pytest.mark.block_network
def test_collection_latest_version_uses_local(collection: pystac.Collection) -> None:
    assert collection.validate()


@pytest.mark.block_network
def test_item_latest_version_uses_local(item: pystac.Item) -> None:
    assert item.validate()


def test_404_schema_url(requests_mock: Mocker, item: pystac.Item) -> None:
    requests_mock.get(
        "http://pystac-extensions.test/a-fake-schema.json", status_code=404
    )
    item.stac_extensions = ["http://pystac-extensions.test/a-fake-schema.json"]
    with pytest.raises(
        GetSchemaError, match="http://pystac-extensions.test/a-fake.schema.json"
    ):
        item.validate()
