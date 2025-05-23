from __future__ import annotations

import json
import os
import posixpath
import tempfile
from collections import defaultdict
from collections.abc import Iterator
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest

import pystac
from pystac import (
    HIERARCHICAL_LINKS,
    Asset,
    Catalog,
    CatalogType,
    Collection,
    Item,
    MediaType,
)
from pystac.errors import STACError
from pystac.layout import (
    APILayoutStrategy,
    BestPracticesLayoutStrategy,
    HrefLayoutStrategy,
    TemplateLayoutStrategy,
)
from pystac.utils import (
    is_absolute_href,
    make_absolute_href,
    make_posix_style,
    make_relative_href,
)
from tests.utils import (
    ARBITRARY_BBOX,
    ARBITRARY_EXTENT,
    ARBITRARY_GEOM,
    MockStacIO,
    TestCases,
)


class TestCatalogType:
    def test_determine_type_for_absolute_published(self) -> None:
        cat = TestCases.case_1()
        with tempfile.TemporaryDirectory() as tmp_dir:
            cat.normalize_and_save(tmp_dir, catalog_type=CatalogType.ABSOLUTE_PUBLISHED)
            cat_json = pystac.StacIO.default().read_json(
                os.path.join(tmp_dir, "catalog.json")
            )

        catalog_type = CatalogType.determine_type(cat_json)
        assert catalog_type == CatalogType.ABSOLUTE_PUBLISHED

    def test_determine_type_for_relative_published(self) -> None:
        cat = TestCases.case_2()
        with tempfile.TemporaryDirectory() as tmp_dir:
            cat.normalize_and_save(tmp_dir, catalog_type=CatalogType.RELATIVE_PUBLISHED)
            cat_json = pystac.StacIO.default().read_json(
                os.path.join(tmp_dir, "catalog.json")
            )

        catalog_type = CatalogType.determine_type(cat_json)
        assert catalog_type == CatalogType.RELATIVE_PUBLISHED

    def test_determine_type_for_self_contained(self) -> None:
        cat_json = pystac.StacIO.default().read_json(
            TestCases.get_path("data-files/catalogs/test-case-1/catalog.json")
        )
        catalog_type = CatalogType.determine_type(cat_json)
        assert catalog_type == CatalogType.SELF_CONTAINED

    def test_determine_type_for_unknown(self) -> None:
        catalog = Catalog(id="test", description="test desc")
        subcat = Catalog(id="subcat", description="subcat desc")
        catalog.add_child(subcat)
        catalog.normalize_hrefs("http://example.com")
        d = catalog.to_dict(include_self_link=False)

        assert CatalogType.determine_type(d) is None


class TestCatalog:
    def test_create_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cat_dir = os.path.join(tmp_dir, "catalog")
            catalog = TestCases.case_1()

            catalog.normalize_and_save(
                cat_dir, catalog_type=CatalogType.ABSOLUTE_PUBLISHED
            )

            read_catalog = Catalog.from_file(f"{cat_dir}/catalog.json")

            collections = catalog.get_children()
            assert len(list(collections)) == 2

            items = read_catalog.get_items(recursive=True)

            assert len(list(items)) == 8

    def test_from_dict_preserves_dict(self) -> None:
        catalog_dict = TestCases.case_1().to_dict()
        param_dict = deepcopy(catalog_dict)

        # test that the parameter is preserved
        _ = Catalog.from_dict(param_dict)
        assert param_dict == catalog_dict

        # assert that the parameter is not preserved with
        # non-default parameter
        _ = Catalog.from_dict(param_dict, preserve_dict=False, migrate=False)
        assert param_dict != catalog_dict

    def test_from_file_bad_catalog(self) -> None:
        with pytest.raises(pystac.errors.STACTypeError) as ctx:
            _ = Catalog.from_file(TestCases.get_path(TestCases.bad_catalog_case))
        assert "(id = broken_cat) does not represent a STACObject" in ctx.value.args[0]
        assert "is Catalog" in ctx.value.args[0]

    def test_from_dict_set_root(self) -> None:
        path = TestCases.get_path("data-files/catalogs/test-case-1/catalog.json")
        with open(path) as f:
            cat_dict = json.load(f)
        root_cat = pystac.Catalog(id="test", description="test desc")
        collection = Catalog.from_dict(cat_dict, root=root_cat)
        assert collection.get_root() is root_cat

    @pytest.mark.vcr()
    def test_read_remote(self) -> None:
        catalog_url = (
            "https://raw.githubusercontent.com/stac-extensions/label/main/"
            "examples/multidataset/catalog.json"
        )
        cat = Catalog.from_file(catalog_url)

        zanzibar = cat.get_child("zanzibar-collection")
        assert zanzibar is not None

        assert len(list(zanzibar.get_items())) == 2

    def test_clear_items_removes_from_cache(self) -> None:
        catalog = Catalog(id="test", description="test")
        subcat = Catalog(id="subcat", description="test")
        catalog.add_child(subcat)
        item = Item(
            id="test-item",
            geometry=ARBITRARY_GEOM,
            bbox=ARBITRARY_BBOX,
            datetime=datetime.now(timezone.utc),
            properties={"key": "one"},
        )
        subcat.add_item(item)

        items = list(catalog.get_items(recursive=True))
        assert len(items) == 1
        assert items[0].properties["key"] == "one"

        subcat.clear_items()
        item = Item(
            id="test-item",
            geometry=ARBITRARY_GEOM,
            bbox=ARBITRARY_BBOX,
            datetime=datetime.now(timezone.utc),
            properties={"key": "two"},
        )
        subcat.add_item(item)

        items = list(catalog.get_items(recursive=True))
        assert len(items) == 1
        assert items[0].properties["key"] == "two"

        subcat.remove_item("test-item")
        item = Item(
            id="test-item",
            geometry=ARBITRARY_GEOM,
            bbox=ARBITRARY_BBOX,
            datetime=datetime.now(timezone.utc),
            properties={"key": "three"},
        )
        subcat.add_item(item)

        items = list(catalog.get_items(recursive=True))
        assert len(items) == 1
        assert items[0].properties["key"] == "three"

    def test_clear_children_removes_from_cache(self) -> None:
        catalog = Catalog(id="test", description="test")
        subcat = Catalog(id="subcat", description="test")
        catalog.add_child(subcat)

        children = list(catalog.get_children())
        assert len(children) == 1
        assert children[0].description == "test"

        catalog.clear_children()
        subcat = Catalog(id="subcat", description="test2")
        catalog.add_child(subcat)

        children = list(catalog.get_children())
        assert len(children) == 1
        assert children[0].description == "test2"

        catalog.remove_child("subcat")
        subcat = Catalog(id="subcat", description="test3")
        catalog.add_child(subcat)

        children = list(catalog.get_children())
        assert len(children) == 1
        assert children[0].description == "test3"

    def test_clear_children_sets_parent_and_root_to_None(self) -> None:
        catalog = Catalog(id="test", description="test")
        subcat1 = Catalog(id="subcat", description="test")
        subcat2 = Catalog(id="subcat2", description="test2")
        catalog.add_children([subcat1, subcat2])

        assert subcat1.get_parent() is not None
        assert subcat2.get_parent() is not None
        assert subcat1.get_root() is not None
        assert subcat2.get_root() is not None

        children = list(catalog.get_children())
        assert len(children) == 2

        catalog.clear_children()

        assert subcat1.get_parent() is None
        assert subcat2.get_parent() is None
        assert subcat1.get_root() is None
        assert subcat2.get_root() is None

    def test_add_child_throws_if_item(self) -> None:
        cat = TestCases.case_1()
        item = next(cat.get_items(recursive=True))
        with pytest.raises(pystac.STACError):
            cat.add_child(item)  # type:ignore

    def test_add_child_returns_link(self) -> None:
        parent = Catalog(id="parent", description="test")
        child = Catalog(id="child", description="test")
        link = parent.add_child(child)
        assert isinstance(link, pystac.Link)
        link.extra_fields["foo"] = "bar"
        link2 = parent.get_single_link("child")
        assert link2 is not None
        assert link2.extra_fields["foo"] == "bar"

    def test_add_children_returns_links(self) -> None:
        parent = Catalog(id="parent", description="test")
        child1 = Catalog(id="child", description="test")
        child2 = Catalog(id="child2", description="test")
        links = parent.add_children([child1, child2])
        assert isinstance(links, list)
        assert len(links) == 2
        assert isinstance(links[0], pystac.Link)
        assert isinstance(links[1], pystac.Link)
        links2 = parent.get_links("child")
        assert links[0] in links2
        assert links[1] in links2

    def test_add_child_override_parent(self) -> None:
        parent1 = Catalog(id="parent1", description="test1")
        parent2 = Catalog(id="parent2", description="test2")
        child = Catalog(id="child", description="test3")
        assert child.get_parent() is None

        parent1.add_child(child)
        assert child.get_parent() is parent1

        parent2.add_child(child)
        assert child.get_parent() is parent2

    def test_add_child_set_parent_false(self) -> None:
        parent1 = Catalog(id="parent1", description="test1")
        parent2 = Catalog(id="parent2", description="test2")
        child = Catalog(id="child", description="test3")
        assert child.get_parent() is None

        parent1.add_child(child, set_parent=False)
        assert child.get_parent() is not parent1

        parent1.add_child(child)
        parent2.add_child(child, set_parent=False)
        assert child.get_parent() is parent1

    def test_add_item_override_parent(self) -> None:
        parent1 = Catalog(id="parent1", description="test1")
        parent2 = Catalog(id="parent2", description="test2")
        child = Item(
            id="child",
            geometry=None,
            bbox=None,
            datetime=datetime.now(),
            properties={},
        )
        assert child.get_parent() is None

        parent1.add_item(child)
        assert child.get_parent() is parent1

        parent2.add_item(child)
        assert child.get_parent() is parent2

    def test_add_item_set_parent_false(self) -> None:
        parent1 = Catalog(id="parent1", description="test1")
        parent2 = Catalog(id="parent2", description="test2")
        child = Item(
            id="child",
            geometry=None,
            bbox=None,
            datetime=datetime.now(),
            properties={},
        )
        assert child.get_parent() is None

        parent1.add_item(child, set_parent=False)
        assert child.get_parent() is not parent1

        parent1.add_item(child)
        parent2.add_item(child, set_parent=False)
        assert child.get_parent() is parent1

    def test_add_item_throws_if_child(self) -> None:
        cat = TestCases.case_1()
        child = next(iter(cat.get_children()))
        with pytest.raises(pystac.STACError):
            cat.add_item(child)  # type:ignore

    def test_add_item_returns_link(self) -> None:
        parent = Catalog(id="parent", description="test")
        child = Item(
            id="child",
            geometry=None,
            bbox=None,
            datetime=datetime.now(),
            properties={},
        )
        link = parent.add_item(child)
        assert isinstance(link, pystac.Link)
        link.extra_fields["foo"] = "bar"
        link2 = parent.get_single_link("item")
        assert link2 is not None
        assert link2.extra_fields["foo"] == "bar"

    def test_add_items_returns_links(self) -> None:
        parent = Catalog(id="parent", description="test")
        child1 = Item(
            id="child1",
            geometry=None,
            bbox=None,
            datetime=datetime.now(),
            properties={},
        )
        child2 = Item(
            id="child2",
            geometry=None,
            bbox=None,
            datetime=datetime.now(),
            properties={},
        )
        links = parent.add_items([child1, child2])
        assert isinstance(links, list)
        assert len(links) == 2
        assert isinstance(links[0], pystac.Link)
        assert isinstance(links[1], pystac.Link)
        links2 = parent.get_links("item")
        assert links[0] in links2
        assert links[1] in links2

    def test_get_child_returns_none_if_not_found(self) -> None:
        cat = TestCases.case_1()
        child = cat.get_child("thisshouldnotbeachildid", recursive=True)
        assert child is None

    def test_get_item_is_deprecated_but_still_works(self) -> None:
        cat = TestCases.case_1()
        with pytest.warns(DeprecationWarning):
            item = cat.get_item("area-2-1-imagery", recursive=True)
            assert item is not None

    def test_get_item_returns_none_if_not_found(self) -> None:
        cat = TestCases.case_1()
        with pytest.warns(DeprecationWarning):
            item = cat.get_item("thisshouldnotbeanitemid", recursive=True)
            assert item is None

    def test_get_all_items_is_deprecated_but_still_works(self) -> None:
        cat = TestCases.case_1()
        with pytest.warns(DeprecationWarning):
            all_items = cat.get_all_items()
        items = cat.get_items(recursive=True)
        assert all(a == i for a, i in zip(all_items, items))

    def test_get_items_returns_empty_generator_if_not_found(self) -> None:
        cat = TestCases.case_1()
        items = cat.get_items("thisshouldnotbeanitemid", recursive=True)
        assert next(items, None) is None

    def test_sets_catalog_type(self) -> None:
        cat = TestCases.case_1()

        assert cat.catalog_type == CatalogType.SELF_CONTAINED

    @pytest.mark.parametrize("catalog", TestCases.all_test_catalogs())
    def test_walk_iterates_correctly(self, catalog: Catalog) -> None:
        def test_catalog(cat: Catalog) -> None:
            expected_catalog_iterations = 1
            actual_catalog_iterations = 0
            for root, children, items in cat.walk():
                actual_catalog_iterations += 1
                expected_catalog_iterations += len(list(root.get_children()))

                assert {c.id for c in root.get_children()} == {
                    c.id for c in children
                }, "Children unequal"

                assert {c.id for c in root.get_items()} == {c.id for c in items}, (
                    "Items unequal"
                )

            assert actual_catalog_iterations == expected_catalog_iterations

        test_catalog(catalog)

    @pytest.mark.parametrize("catalog", TestCases.all_test_catalogs())
    def test_clone_generates_correct_links(self, catalog: Catalog) -> None:
        expected_link_types_to_counts: Any = {}
        actual_link_types_to_counts: Any = {}

        for root, _, items in catalog.walk():
            expected_link_types_to_counts[root.id] = defaultdict(int)
            actual_link_types_to_counts[root.id] = defaultdict(int)

            for link in root.get_links():
                expected_link_types_to_counts[root.id][link.rel] += 1

            for link in root.clone().get_links():
                actual_link_types_to_counts[root.id][link.rel] += 1

            for item in items:
                expected_link_types_to_counts[item.id] = defaultdict(int)
                actual_link_types_to_counts[item.id] = defaultdict(int)
                for link in item.get_links():
                    expected_link_types_to_counts[item.id][link.rel] += 1
                for link in item.get_links():
                    actual_link_types_to_counts[item.id][link.rel] += 1

        assert set(expected_link_types_to_counts.keys()) == set(
            actual_link_types_to_counts.keys()
        )

        for obj_id in actual_link_types_to_counts:
            expected_counts = expected_link_types_to_counts[obj_id]
            actual_counts = actual_link_types_to_counts[obj_id]
            assert set(expected_counts.keys()) == set(actual_counts.keys())
            for rel in expected_counts:
                assert actual_counts[rel] == expected_counts[rel], (
                    "Clone of {} has {} {} links, original has {}".format(
                        obj_id, actual_counts[rel], rel, expected_counts[rel]
                    )
                )

    def test_save_uses_previous_catalog_type(self) -> None:
        catalog = TestCases.case_1()
        assert catalog.catalog_type == CatalogType.SELF_CONTAINED
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog.normalize_hrefs(tmp_dir)
            href = catalog.self_href
            catalog.save()

            cat2 = pystac.Catalog.from_file(href)
            assert cat2.catalog_type == CatalogType.SELF_CONTAINED

    def test_save_to_provided_href(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = TestCases.case_1()
            href = "https://stac.test"
            folder = os.path.join(tmp_dir, "cat")
            catalog.normalize_hrefs(href)
            catalog.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED, dest_href=folder)

            catalog_path = os.path.join(folder, "catalog.json")
            assert os.path.exists(catalog_path)
            result_cat = Catalog.from_file(catalog_path)
            for link in result_cat.get_child_links():
                assert cast(str, link.target).startswith(href)

    def test_save_relative_published_no_self_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = TestCases.case_1()
            href = "https://stac.test"
            folder = os.path.join(tmp_dir, "cat")
            catalog.normalize_hrefs(href)
            catalog.save(catalog_type=CatalogType.RELATIVE_PUBLISHED, dest_href=folder)

            catalog_path = os.path.join(folder, "catalog.json")
            assert os.path.exists(catalog_path)
            result_cat = Catalog.from_file(catalog_path)

            # Check that Items do not have a self link
            # Since Item.from_dict automatically adds a self link, we need to look at
            # the JSON files themselves.
            stac_io = pystac.StacIO.default()

            for current_cat, _, __ in result_cat.walk():
                for item_link in current_cat.get_item_links():
                    item_dict = stac_io.read_json(item_link)
                    self_link = next(
                        (
                            link
                            for link in item_dict.get("links", [])
                            if link["rel"] == "self"
                        ),
                        None,
                    )
                    assert self_link is None

    def test_save_with_different_stac_io(self) -> None:
        catalog = Catalog.from_file(
            TestCases.get_path("data-files/catalogs/test-case-1/catalog.json")
        )
        stac_io = MockStacIO()
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog.normalize_hrefs(tmp_dir)
            catalog.save(
                catalog_type=CatalogType.ABSOLUTE_PUBLISHED,
                dest_href=tmp_dir,
                stac_io=stac_io,
            )

        hrefs = []
        for root, _, items in catalog.walk():
            hrefs.append(root.get_self_href())
            for item in items:
                hrefs.append(item.get_self_href())

        assert len(hrefs) == stac_io.mock.write_text.call_count
        for call_args_list in stac_io.mock.write_text.call_args_list:
            assert call_args_list[0][0] in hrefs

    def test_subcatalogs_saved_to_correct_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = TestCases.case_1()
            href = "https://stac.test"

            catalog.normalize_hrefs(href)
            catalog.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED, dest_href=tmp_dir)

            # Check the root catalog path
            expected_root_catalog_path = os.path.join(tmp_dir, "catalog.json")
            assert os.path.exists(expected_root_catalog_path), (
                f"{expected_root_catalog_path} does not exist."
            )
            assert os.path.isfile(expected_root_catalog_path), (
                f"{expected_root_catalog_path} is not a file."
            )

            # Check each child catalog
            for child_catalog in catalog.get_children():
                relative_path = make_relative_href(
                    child_catalog.self_href, catalog.self_href, start_is_dir=False
                )
                expected_child_path = make_absolute_href(
                    relative_path,
                    expected_root_catalog_path,
                    start_is_dir=False,
                )
                assert os.path.exists(expected_child_path), (
                    f"{expected_child_path} does not exist."
                )
                assert os.path.isfile(expected_child_path), (
                    f"{expected_child_path} is not a file."
                )

            # Check each item
            for item in catalog.get_items(recursive=True):
                relative_path = make_relative_href(
                    item.self_href, catalog.self_href, start_is_dir=False
                )
                expected_item_path = make_absolute_href(
                    relative_path,
                    expected_root_catalog_path,
                    start_is_dir=False,
                )
                assert os.path.exists(expected_item_path), (
                    f"{expected_item_path} does not exist."
                )
                assert os.path.isfile(expected_item_path), (
                    f"{expected_item_path} is not a file."
                )

    def test_clone_uses_previous_catalog_type(self) -> None:
        catalog = TestCases.case_1()
        assert catalog.catalog_type == CatalogType.SELF_CONTAINED
        clone = catalog.clone()
        assert clone.catalog_type == CatalogType.SELF_CONTAINED

    def test_normalize_hrefs_sets_all_hrefs(self) -> None:
        catalog = TestCases.case_1()
        catalog.normalize_hrefs("http://example.com")
        for root, _, items in catalog.walk():
            self_href = root.get_self_href()
            assert self_href is not None
            assert self_href.startswith("http://example.com")
            for link in root.links:
                if link.is_resolved():
                    target_href = cast(pystac.STACObject, link.target).self_href
                else:
                    target_href = link.absolute_href
                assert "http://example.com" in target_href, (
                    '[{}] {} does not contain "{}"'.format(
                        link.rel, target_href, "http://example.com"
                    )
                )
            for item in items:
                assert "http://example.com" in item.self_href

    def test_normalize_hrefs_makes_absolute_href(self) -> None:
        catalog = TestCases.case_1()
        catalog.normalize_hrefs("./relativepath")
        abspath = make_posix_style(os.path.abspath("./relativepath"))
        self_href = catalog.get_self_href()
        assert self_href is not None
        assert self_href.startswith(abspath)

    def test_normalize_hrefs_skip_unresolved(self) -> None:
        catalog = TestCases.case_1()
        catalog.normalize_hrefs("http://example.com", skip_unresolved=True)
        assert catalog.self_href.startswith("http://example.com")
        for link in catalog.links:
            if link.rel == "child" or link.rel == "item":
                assert not link.is_resolved()
        item = Item(
            "an-id",
            geometry=None,
            bbox=None,
            datetime=datetime.now(),
            properties={},
        )
        catalog.add_item(item, title="This is the test item")
        catalog.normalize_hrefs("http://example.com", skip_unresolved=True)
        for link in catalog.links:
            if link.title == "This is the test item":
                assert link.is_resolved()
                assert isinstance(link.target, pystac.STACObject)
                assert link.target.self_href.startswith("http://example.com")
            elif link.rel == "child" or link.rel == "item":
                assert not link.is_resolved()

    def test_save_unresolved(self) -> None:
        catalog = Catalog("an-id", "a description")
        item = Item(
            "an-id",
            geometry=None,
            bbox=None,
            datetime=datetime.now(),
            properties={},
        )
        catalog.add_item(item)
        catalog.add_link(pystac.Link("child", "/not/a/real/path/catalog.json"))
        with tempfile.TemporaryDirectory() as temporary_directory:
            catalog.set_self_href(os.path.join(temporary_directory, "catalog.json"))
            item.set_self_href(os.path.join(temporary_directory, "item.json"))
            catalog.save()
            assert len(os.listdir(temporary_directory)) == 2

        with tempfile.TemporaryDirectory() as temporary_directory:
            catalog.normalize_and_save(temporary_directory, skip_unresolved=True)
            assert len(os.listdir(temporary_directory)) == 2

        with tempfile.TemporaryDirectory() as temporary_directory:
            with pytest.raises(STACError, match="does not resolve to a STAC object"):
                catalog.normalize_and_save(temporary_directory, skip_unresolved=False)

    def test_generate_subcatalogs_works_with_custom_properties(self) -> None:
        catalog = TestCases.case_8()
        defaults = {"pl:item_type": "PlanetScope"}
        catalog.generate_subcatalogs(
            "${year}/${month}/${pl:item_type}", defaults=defaults
        )

        month_cat = catalog.get_child("8", recursive=True)
        assert month_cat is not None
        type_cats = {cat.id for cat in month_cat.get_children()}

        assert type_cats == {"PSScene4Band", "SkySatScene", "PlanetScope"}

    def test_generate_subcatalogs_does_not_change_item_count(self) -> None:
        catalog = TestCases.case_7()

        item_counts = {
            cat.id: len(list(cat.get_items(recursive=True)))
            for cat in catalog.get_children()
        }

        catalog.generate_subcatalogs("${year}/${day}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog.normalize_hrefs(tmp_dir)
            catalog.save(pystac.CatalogType.SELF_CONTAINED)

            cat2 = pystac.Catalog.from_file(os.path.join(tmp_dir, "catalog.json"))
            for child in cat2.get_children():
                actual = len(list(child.get_items(recursive=True)))
                expected = item_counts[child.id]
                assert actual == expected, f" for child '{child.id}'"

    def test_generate_subcatalogs_merge_template_elements(self) -> None:
        catalog = Catalog(id="test", description="Test")
        item_properties = [
            dict(property1=p1, property2=p2) for p1 in ("A", "B") for p2 in (1, 2)
        ]
        for ni, properties in enumerate(item_properties):
            catalog.add_item(
                Item(
                    id=f"item{ni}",
                    geometry=ARBITRARY_GEOM,
                    bbox=ARBITRARY_BBOX,
                    datetime=datetime.now(timezone.utc),
                    properties=properties,
                )
            )
        result = catalog.generate_subcatalogs("${property1}_${property2}")

        actual_subcats = {cat.id for cat in result}
        expected_subcats = {
            "{}_{}".format(d["property1"], d["property2"]) for d in item_properties
        }
        assert len(result) == len(expected_subcats)
        assert actual_subcats == expected_subcats

    def test_generate_subcatalogs_can_be_applied_multiple_times(self) -> None:
        catalog = TestCases.case_8()

        _ = catalog.generate_subcatalogs("${year}/${month}")
        catalog.normalize_hrefs("/tmp")
        expected_hrefs = {
            item.id: item.get_self_href() for item in catalog.get_items(recursive=True)
        }

        result = catalog.generate_subcatalogs("${year}/${month}")
        assert len(result) == 0
        catalog.normalize_hrefs("/tmp")
        for item in catalog.get_items(recursive=True):
            assert item.get_self_href() == expected_hrefs[item.id], (
                f" for item '{item.id}'"
            )

    def test_generate_subcatalogs_works_after_adding_more_items(self) -> None:
        catalog = Catalog(id="test", description="Test")
        properties = dict(property1="A", property2=1)
        catalog.add_item(
            Item(
                id="item1",
                geometry=ARBITRARY_GEOM,
                bbox=ARBITRARY_BBOX,
                datetime=datetime.now(timezone.utc),
                properties=properties,
            )
        )
        catalog.generate_subcatalogs("${property1}/${property2}")
        catalog.add_item(
            Item(
                id="item2",
                geometry=ARBITRARY_GEOM,
                bbox=ARBITRARY_BBOX,
                datetime=datetime.now(timezone.utc),
                properties=properties,
            )
        )
        catalog.generate_subcatalogs("${property1}/${property2}")

        catalog.normalize_hrefs("/tmp")
        item1 = next(catalog.get_items("item1", recursive=True))
        item1_parent = item1.get_parent()
        assert item1_parent is not None
        item2 = next(catalog.get_items("item2", recursive=True))
        item2_parent = item2.get_parent()
        assert item2_parent is not None
        assert item1_parent.get_self_href() == item2_parent.get_self_href()

    def test_generate_subcatalogs_works_for_branched_subcatalogs(self) -> None:
        catalog = Catalog(id="test", description="Test")
        item_properties = [
            dict(property1="A", property2=1, property3="i"),  # add 3 subcats
            dict(property1="A", property2=1, property3="j"),  # add 1 more
            dict(property1="A", property2=2, property3="i"),  # add 2 more
            dict(property1="B", property2=1, property3="i"),  # add 3 more
        ]
        for ni, properties in enumerate(item_properties):
            catalog.add_item(
                Item(
                    id=f"item{ni}",
                    geometry=ARBITRARY_GEOM,
                    bbox=ARBITRARY_BBOX,
                    datetime=datetime.now(timezone.utc),
                    properties=properties,
                )
            )
        result = catalog.generate_subcatalogs("${property1}/${property2}/${property3}")
        assert len(result) == 9

        actual_subcats = {cat.id for cat in result}
        expected_subcats = {"A", "B", "1", "2", "i", "j"}
        assert actual_subcats == expected_subcats

    def test_generate_subcatalogs_works_for_subcatalogs_with_same_ids(self) -> None:
        catalog = Catalog(id="test", description="Test")
        item_properties = [
            dict(property1=1, property2=1),  # add 2 subcats
            dict(property1=1, property2=2),  # add 1 more
            dict(property1=2, property2=1),  # add 2 more
            dict(property1=2, property2=2),  # add 1 more
        ]
        for ni, properties in enumerate(item_properties):
            catalog.add_item(
                Item(
                    id=f"item{ni}",
                    geometry=ARBITRARY_GEOM,
                    bbox=ARBITRARY_BBOX,
                    datetime=datetime.now(timezone.utc),
                    properties=properties,
                )
            )

        result = catalog.generate_subcatalogs("${property1}/${property2}")
        assert len(result) == 6

        catalog.normalize_hrefs("/")

        for item in catalog.get_items(recursive=True):
            item_parent = item.get_parent()
            assert item_parent is not None
            parent_href = item_parent.self_href
            path_to_parent, _ = os.path.split(parent_href)
            subcats = list(
                Path(path_to_parent).parts[1:]
            )  # Skip drive letter if present (Windows)

            assert len(subcats) == 2, f" for item '{item.id}'"

    def test_map_items(self) -> None:
        def item_mapper(item: pystac.Item) -> pystac.Item:
            item.properties["ITEM_MAPPER"] = "YEP"
            return item

        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = TestCases.case_1()

            new_cat = catalog.map_items(item_mapper)

            new_cat.normalize_hrefs(os.path.join(tmp_dir, "cat"))
            new_cat.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)

            result_cat = Catalog.from_file(os.path.join(tmp_dir, "cat", "catalog.json"))

            for item in result_cat.get_items(recursive=True):
                assert "ITEM_MAPPER" in item.properties

            for item in catalog.get_items(recursive=True):
                assert "ITEM_MAPPER" not in item.properties

    def test_map_items_multiple(self) -> None:
        def item_mapper(item: pystac.Item) -> list[pystac.Item]:
            item2 = item.clone()
            item2.id = item2.id + "_2"
            item.properties["ITEM_MAPPER_1"] = "YEP"
            item2.properties["ITEM_MAPPER_2"] = "YEP"
            return [item, item2]

        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = TestCases.case_1()
            catalog_items = list(catalog.get_items(recursive=True))

            new_cat = catalog.map_items(item_mapper)

            new_cat.normalize_hrefs(os.path.join(tmp_dir, "cat"))
            new_cat.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)

            result_cat = Catalog.from_file(os.path.join(tmp_dir, "cat", "catalog.json"))
            result_items = list(result_cat.get_items(recursive=True))

            assert len(catalog_items) * 2 == len(result_items)

            ones, twos = 0, 0
            for item in result_items:
                assert ("ITEM_MAPPER_1" in item.properties) or (
                    "ITEM_MAPPER_2" in item.properties
                )
                if "ITEM_MAPPER_1" in item.properties:
                    ones += 1

                if "ITEM_MAPPER_2" in item.properties:
                    twos += 1

            assert ones == twos

            for item in catalog.get_items(recursive=True):
                assert ("ITEM_MAPPER_1" not in item.properties) and (
                    "ITEM_MAPPER_2" not in item.properties
                )

    def test_map_items_multiple_2(self) -> None:
        catalog = Catalog(id="test-1", description="Test1")
        item1 = Item(
            id="item1",
            geometry=ARBITRARY_GEOM,
            bbox=ARBITRARY_BBOX,
            datetime=datetime.now(timezone.utc),
            properties={},
        )
        item1.add_asset("ortho", Asset(href="/some/ortho.tif"))
        catalog.add_item(item1)
        kitten = Catalog(id="test-kitten", description="A cuter version of catalog")
        catalog.add_child(kitten)
        item2 = Item(
            id="item2",
            geometry=ARBITRARY_GEOM,
            bbox=ARBITRARY_BBOX,
            datetime=datetime.now(timezone.utc),
            properties={},
        )
        item2.add_asset("ortho", Asset(href="/some/other/ortho.tif"))
        kitten.add_item(item2)

        def modify_item_title(item: pystac.Item) -> pystac.Item:
            item.properties["title"] = "Some title"
            return item

        def duplicate_item(item: pystac.Item) -> list[pystac.Item]:
            duplicated_item = item.clone()
            duplicated_item.id += "-duplicated"
            return [item, duplicated_item]

        c = catalog.map_items(modify_item_title)
        c = c.map_items(duplicate_item)
        new_catalog = c

        items = new_catalog.get_items(recursive=True)
        assert len(list(items)) == 4

    def test_map_assets_single(self) -> None:
        changed_asset = "d43bead8-e3f8-4c51-95d6-e24e750a402b"

        def asset_mapper(key: str, asset: pystac.Asset) -> pystac.Asset:
            if key == changed_asset:
                asset.title = "NEW TITLE"

            return asset

        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = TestCases.case_2()

            new_cat = catalog.map_assets(asset_mapper)

            new_cat.normalize_hrefs(os.path.join(tmp_dir, "cat"))
            new_cat.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)

            result_cat = Catalog.from_file(os.path.join(tmp_dir, "cat", "catalog.json"))

            found = False
            for item in result_cat.get_items(recursive=True):
                for key, asset in item.assets.items():
                    if key == changed_asset:
                        found = True
                        assert asset.title == "NEW TITLE"
                    else:
                        assert asset.title != "NEW TITLE"
            assert found

    def test_map_assets_tup(self) -> None:
        changed_assets: list[str] = []

        def asset_mapper(
            key: str, asset: pystac.Asset
        ) -> pystac.Asset | tuple[str, pystac.Asset]:
            if asset.media_type and "geotiff" in asset.media_type:
                asset.title = "NEW TITLE"
                changed_assets.append(key)
                return (f"{key}-modified", asset)
            else:
                return asset

        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = TestCases.case_2()

            new_cat = catalog.map_assets(asset_mapper)

            new_cat.normalize_hrefs(os.path.join(tmp_dir, "cat"))
            new_cat.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)

            result_cat = Catalog.from_file(os.path.join(tmp_dir, "cat", "catalog.json"))

            found = False
            not_found = False
            for item in result_cat.get_items(recursive=True):
                for key, asset in item.assets.items():
                    if key.replace("-modified", "") in changed_assets:
                        found = True
                        assert asset.title == "NEW TITLE"
                    else:
                        not_found = True
                        assert asset.title != "NEW TITLE"

            assert found
            assert not_found

    def test_map_assets_multi(self) -> None:
        changed_assets = []

        def asset_mapper(
            key: str, asset: pystac.Asset
        ) -> pystac.Asset | dict[str, pystac.Asset]:
            if asset.media_type and "geotiff" in asset.media_type:
                changed_assets.append(key)
                mod1 = asset.clone()
                mod1.title = "NEW TITLE 1"
                mod2 = asset.clone()
                mod2.title = "NEW TITLE 2"
                return {f"{key}-mod-1": mod1, f"{key}-mod-2": mod2}
            else:
                return asset

        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = TestCases.case_2()

            new_cat = catalog.map_assets(asset_mapper)

            new_cat.normalize_hrefs(os.path.join(tmp_dir, "cat"))
            new_cat.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)

            result_cat = Catalog.from_file(os.path.join(tmp_dir, "cat", "catalog.json"))

            found1 = False
            found2 = False
            not_found = False
            for item in result_cat.get_items(recursive=True):
                for key, asset in item.assets.items():
                    if key.replace("-mod-1", "") in changed_assets:
                        found1 = True
                        assert asset.title == "NEW TITLE 1"
                    elif key.replace("-mod-2", "") in changed_assets:
                        found2 = True
                        assert asset.title == "NEW TITLE 2"
                    else:
                        not_found = True
                        assert asset.title != "NEW TITLE"

            assert found1
            assert found2
            assert not_found

    def test_make_all_asset_hrefs_absolute(self) -> None:
        cat = TestCases.case_2()
        cat.make_all_asset_hrefs_absolute()
        ID = "cf73ec1a-d790-4b59-b077-e101738571ed"
        item = next(cat.get_items(ID, recursive=True))
        href = item.assets[ID].href
        assert is_absolute_href(href)

    def test_make_all_asset_hrefs_relative(self) -> None:
        cat = TestCases.case_2()
        ID = "cf73ec1a-d790-4b59-b077-e101738571ed"
        item = next(cat.get_items(ID, recursive=True))
        asset = item.assets[ID]
        original_href = asset.href
        cat.make_all_asset_hrefs_absolute()

        assert is_absolute_href(asset.href)

        cat.make_all_asset_hrefs_relative()

        assert not is_absolute_href(asset.href)
        assert asset.href == original_href

    @pytest.mark.parametrize("catalog", TestCases.all_test_catalogs())
    def test_make_all_links_relative_or_absolute(self, catalog: Catalog) -> None:
        def check_all_relative(cat: Catalog) -> None:
            for root, catalogs, items in cat.walk():
                for link in root.links:
                    if link.rel in HIERARCHICAL_LINKS:
                        assert not is_absolute_href(link.href)
                for item in items:
                    for link in item.links:
                        if link.rel in HIERARCHICAL_LINKS:
                            assert not is_absolute_href(link.href)

        def check_all_absolute(cat: Catalog) -> None:
            for root, catalogs, items in cat.walk():
                for link in root.links:
                    assert is_absolute_href(link.href)
                for item in items:
                    for link in item.links:
                        assert is_absolute_href(link.href)

        with tempfile.TemporaryDirectory() as tmp_dir:
            c2 = catalog.full_copy()
            c2.normalize_hrefs(tmp_dir)
            c2.catalog_type = CatalogType.RELATIVE_PUBLISHED
            check_all_relative(c2)
            c2.catalog_type = CatalogType.ABSOLUTE_PUBLISHED
            check_all_absolute(c2)

    @pytest.mark.block_network()
    def test_self_contained_catalog_collection_item_links(self) -> None:
        """See issue https://github.com/stac-utils/pystac/issues/657"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog = pystac.Catalog(
                id="catalog-issue-657", description="catalog-issue-657"
            )
            collection = pystac.Collection(
                "collection-issue-657",
                "collection-issue-657",
                pystac.Extent(
                    spatial=pystac.SpatialExtent([[-180.0, -90.0, 180.0, 90.0]]),
                    temporal=pystac.TemporalExtent([[datetime(2021, 11, 1), None]]),
                ),
                license="other",
            )

            item = pystac.Item(
                id="item-issue-657",
                stac_extensions=[],
                geometry=ARBITRARY_GEOM,
                bbox=ARBITRARY_BBOX,
                datetime=datetime(2021, 11, 1),
                properties={},
            )

            collection.add_item(item)
            catalog.add_child(collection)

            catalog.normalize_hrefs(tmp_dir)
            catalog.validate_all()

            catalog.save(catalog_type=CatalogType.SELF_CONTAINED)
            with open(
                f"{tmp_dir}/collection-issue-657/item-issue-657/item-issue-657.json"
            ) as f:
                item_json = json.load(f)

            for link in item_json["links"]:
                # self links are always absolute
                if link["rel"] == "self":
                    continue

                href = link["href"]
                assert not is_absolute_href(href), (
                    f"Link with rel={link['rel']} is absolute!"
                )

    def test_full_copy_and_normalize_works_with_created_stac(self) -> None:
        cat = TestCases.case_3()
        cat_copy = cat.full_copy()
        cat_copy.normalize_hrefs("http://example.com")
        for root, catalogs, items in cat_copy.walk():
            for link in root.links:
                if link.rel != "self":
                    assert link.target is not None
            for item in items:
                for link in item.links:
                    if link.rel != "self":
                        assert link.get_href() is not None

    def test_extra_fields(self) -> None:
        catalog = TestCases.case_1()

        catalog.extra_fields["custom_field"] = "Special content"

        with tempfile.TemporaryDirectory() as tmp_dir:
            p = os.path.join(tmp_dir, "catalog.json")
            catalog.save_object(include_self_link=False, dest_href=p)
            with open(p) as f:
                cat_json = json.load(f)
            assert "custom_field" in cat_json
            assert cat_json["custom_field"] == "Special content"

            read_cat = pystac.Catalog.from_file(p)
            assert "custom_field" in read_cat.extra_fields
            assert read_cat.extra_fields["custom_field"] == "Special content"

    @pytest.mark.parametrize("cat", TestCases.all_test_catalogs())
    @pytest.mark.vcr()
    def test_validate_all(self, cat: Catalog) -> None:
        # If hrefs are not set, it will fail validation.
        if cat.get_self_href() is None:
            cat.normalize_hrefs("/tmp")
        cat.validate_all()

    @pytest.mark.vcr()
    def test_validate_all_invalid(self) -> None:
        # Make one invalid, write it off, read it in, ensure it throws
        cat = TestCases.case_1()
        item = next(cat.get_items("area-1-1-labels", recursive=True))
        item.geometry = {"type": "INVALID", "coordinates": "NONE"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            cat.normalize_hrefs(tmp_dir)
            cat.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

            cat2 = pystac.Catalog.from_file(os.path.join(tmp_dir, "catalog.json"))

            with pytest.raises(pystac.STACValidationError):
                cat2.validate_all()

    def test_set_hrefs_manually(self) -> None:
        catalog = TestCases.case_1()

        # Modify the datetimes
        year = 2004
        month = 2
        for item in catalog.get_items(recursive=True):
            assert item.datetime is not None
            item.datetime = item.datetime.replace(year=year, month=month)
            year += 1
            month += 1

        with tempfile.TemporaryDirectory() as tmp_dir:
            for root, _, items in catalog.walk():
                # Set root's HREF based off the parent
                parent = root.get_parent()
                if parent is None:
                    root_dir = tmp_dir
                else:
                    d = os.path.dirname(parent.self_href)
                    root_dir = os.path.join(d, root.id)
                root_href = os.path.join(root_dir, root.DEFAULT_FILE_NAME)
                root.set_self_href(root_href)

                # Set each item's HREF based on it's datetime
                for item in items:
                    assert item.datetime is not None
                    item_href = "{}/{}-{}/{}.json".format(
                        root_dir, item.datetime.year, item.datetime.month, item.id
                    )
                    item.set_self_href(item_href)

            catalog.save(catalog_type=CatalogType.SELF_CONTAINED)

            read_catalog = Catalog.from_file(os.path.join(tmp_dir, "catalog.json"))

            for root, _, items in read_catalog.walk():
                parent = root.get_parent()
                if parent is None:
                    assert root.get_self_href() == make_posix_style(
                        os.path.join(tmp_dir, "catalog.json")
                    )
                else:
                    d = os.path.dirname(parent.self_href)
                    assert root.get_self_href() == make_posix_style(
                        os.path.join(d, root.id, root.DEFAULT_FILE_NAME)
                    )
                for item in items:
                    assert item.datetime is not None
                    end = posixpath.join(
                        f"{item.datetime.year}-{item.datetime.month}",
                        f"{item.id}.json",
                    )
                    self_href = item.get_self_href()
                    assert self_href is not None
                    assert self_href.endswith(end), "{} does not end with {}".format(
                        self_href, end
                    )

    @pytest.mark.parametrize("cat", TestCases.all_test_catalogs())
    def test_collections_cache_correctly(self, cat: Catalog) -> None:
        mock_io = MockStacIO()
        cat._stac_io = mock_io
        expected_collection_reads = set()
        for root, _, items in cat.walk():
            if isinstance(root, Collection) and root != cat:
                expected_collection_reads.add(root.get_self_href())

            # Iterate over items to make sure they are read
            assert list(items) is not None

        call_uris: list[Any] = [
            call[0][0]
            for call in mock_io.mock.read_text.call_args_list
            if call[0][0] in expected_collection_reads
        ]

        for collection_uri in expected_collection_reads:
            calls = len([x for x in call_uris if x == collection_uri])
            assert calls == 1, "{} was read {} times instead of once!".format(
                collection_uri, calls
            )

    def test_reading_iterating_and_writing_works_as_expected(self) -> None:
        """Test case to cover issue #88"""
        stac_uri = TestCases.get_path("data-files/catalogs/test-case-6/catalog.json")
        cat = Catalog.from_file(stac_uri)

        # Iterate over the items. This was causing failure in
        # in the later iterations as per issue #88
        for item in cat.get_items(recursive=True):
            pass

        with tempfile.TemporaryDirectory() as tmp_dir:
            new_stac_uri = os.path.join(tmp_dir, "test-case-6")
            cat.normalize_hrefs(new_stac_uri)
            cat.save(catalog_type=CatalogType.SELF_CONTAINED)

            # Open the local copy and iterate over it.
            cat2 = Catalog.from_file(os.path.join(new_stac_uri, "catalog.json"))

            for item in cat2.get_items(recursive=True):
                # Iterate again over the items. This would fail in #88
                pass

    def test_get_children_cbers(self) -> None:
        cat = TestCases.case_6()
        assert len(list(cat.get_children())) == 4

    def test_resolve_planet(self) -> None:
        """Test against a bug that caused infinite recursion during link resolution"""
        cat = TestCases.case_8()
        for root, _, items in cat.walk():
            for item in items:
                item.resolve_links()
            root.resolve_links()

    def test_handles_children_with_same_id(self) -> None:
        # This catalog has the root and child collection share an ID.
        cat = pystac.Catalog.from_file(
            TestCases.get_path("data-files/invalid/shared-id/catalog.json")
        )
        items = list(cat.get_items(recursive=True))

        assert len(items) == 1

    def test_catalog_with_href_caches_by_href(self) -> None:
        cat = TestCases.case_1()
        cache = cat._resolved_objects

        # Since all of our STAC objects have HREFs, everything should be
        # cached only by HREF
        assert len(cache.id_keys_to_objects) == 0

    def test_from_invalid_dict_raises_exception(self) -> None:
        stac_io = pystac.StacIO.default()
        collection_dict = stac_io.read_json(
            TestCases.get_path("data-files/collections/multi-extent.json")
        )
        with pytest.raises(pystac.STACTypeError):
            _ = pystac.Catalog.from_dict(collection_dict)

    def test_get_collections(self) -> None:
        catalog = TestCases.case_2()
        collections = list(catalog.get_collections())

        assert len(collections) > 0
        assert all(isinstance(c, pystac.Collection) for c in collections)

    def test_get_all_collections(self) -> None:
        catalog = TestCases.case_1()
        all_collections = list(catalog.get_all_collections())

        assert len(all_collections) == 4
        assert all(isinstance(c, pystac.Collection) for c in all_collections)

    def test_get_single_links_media_type(self) -> None:
        catalog = TestCases.case_1()

        catalog.links.append(
            pystac.Link(rel="search", target="./search.html", media_type="text/html")
        )
        catalog.links.append(
            pystac.Link(
                rel="search", target="./search.json", media_type="application/geo+json"
            )
        )

        html_link = catalog.get_single_link(rel="search")
        assert html_link is not None
        assert html_link.href == "./search.html"
        html_link = catalog.get_single_link(media_type="text/html")
        assert html_link is not None
        assert html_link.href == "./search.html"
        json_link = catalog.get_single_link(
            rel="search", media_type="application/geo+json"
        )
        assert json_link is not None
        assert json_link.href == "./search.json"
        no_link = catalog.get_single_link(rel="via")
        assert no_link is None
        first_link = catalog.get_single_link()
        assert first_link is not None
        assert first_link.rel == "self"

    def test_get_links(self) -> None:
        catalog = TestCases.case_1()

        catalog.links.append(
            pystac.Link(rel="search", target="./search.html", media_type="text/html")
        )
        catalog.links.append(
            pystac.Link(
                rel="search", target="./search.json", media_type="application/geo+json"
            )
        )
        assert (
            len(catalog.get_links(rel="search", media_type="application/geo+json")) == 1
        )
        assert len(catalog.get_links(media_type="text/html")) == 1
        assert (
            len(catalog.get_links(media_type=["text/html", "application/geo+json"]))
            == 2
        )
        assert len(catalog.get_links(rel="search")) == 2
        assert len(catalog.get_links(rel="via")) == 0
        assert len(catalog.get_links()) == 6

    def test_to_dict_no_self_href(self) -> None:
        catalog = Catalog(id="an-id", description="A test Catalog")
        d = catalog.to_dict(include_self_link=False)
        Catalog.from_dict(d)


class TestFullCopy:
    def check_link(self, link: pystac.Link, tag: str) -> None:
        if link.is_resolved():
            target_href: str = cast(pystac.STACObject, link.target).self_href
        else:
            target_href = str(link.target)
        assert tag in target_href, '[{}] {} does not contain "{}"'.format(
            link.rel, target_href, tag
        )

    def check_item(self, item: Item, tag: str) -> None:
        for link in item.links:
            self.check_link(link, tag)

    def check_catalog(self, c: Catalog, tag: str) -> None:
        assert len(c.get_links("root")) == 1, f"Failure for catalog: {c}"

        for link in c.links:
            self.check_link(link, tag)

        for child in c.get_children():
            self.check_catalog(child, tag)

        for item in c.get_items():
            self.check_item(item, tag)

    def test_full_copy_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cat = Catalog(id="test", description="test catalog")

            item = Item(
                id="test_item",
                geometry=ARBITRARY_GEOM,
                bbox=ARBITRARY_BBOX,
                datetime=datetime.now(timezone.utc),
                properties={},
            )

            cat.add_item(item)

            cat.normalize_hrefs(os.path.join(tmp_dir, "catalog-full-copy-1-source"))
            cat2 = cat.full_copy()
            cat2.normalize_hrefs(os.path.join(tmp_dir, "catalog-full-copy-1-dest"))

            self.check_catalog(cat, "source")
            self.check_catalog(cat2, "dest")

    def test_full_copy_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cat = Catalog(id="test", description="test catalog")
            image_item = Item(
                id="Imagery",
                geometry=ARBITRARY_GEOM,
                bbox=ARBITRARY_BBOX,
                datetime=datetime.now(timezone.utc),
                properties={},
            )
            for key in ["ortho", "dsm"]:
                image_item.add_asset(
                    key,
                    Asset(href=f"some/{key}.tif", media_type=MediaType.GEOTIFF),
                )

            label_item = Item(
                id="Labels",
                geometry=ARBITRARY_GEOM,
                bbox=ARBITRARY_BBOX,
                datetime=datetime.now(timezone.utc),
                properties={},
            )
            cat.add_items([image_item, label_item])

            cat.normalize_hrefs(os.path.join(tmp_dir, "catalog-full-copy-2-source"))
            cat.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)
            cat2 = cat.full_copy()
            cat2.normalize_hrefs(os.path.join(tmp_dir, "catalog-full-copy-2-dest"))
            cat2.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)

            self.check_catalog(cat, "source")
            self.check_catalog(cat2, "dest")

    def test_full_copy_3(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_cat = TestCases.case_1()
            root_cat.normalize_hrefs(
                os.path.join(tmp_dir, "catalog-full-copy-3-source")
            )
            root_cat.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)
            cat2 = root_cat.full_copy()
            cat2.normalize_hrefs(os.path.join(tmp_dir, "catalog-full-copy-3-dest"))
            cat2.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)

            self.check_catalog(root_cat, "source")
            self.check_catalog(cat2, "dest")

    def test_full_copy_4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_cat = TestCases.case_2()
            root_cat.normalize_hrefs(
                os.path.join(tmp_dir, "catalog-full-copy-4-source")
            )
            root_cat.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)
            cat2 = root_cat.full_copy()
            cat2.normalize_hrefs(os.path.join(tmp_dir, "catalog-full-copy-4-dest"))
            cat2.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)

            self.check_catalog(root_cat, "source")
            self.check_catalog(cat2, "dest")

            # Check that the relative asset link was saved correctly in the copy.
            ID = "cf73ec1a-d790-4b59-b077-e101738571ed"
            item = next(cat2.get_items(ID, recursive=True))
            href = item.assets[ID].get_absolute_href()
            assert href is not None
            assert os.path.exists(href)


class TestCatalogSubClass:
    """This tests cases related to creating classes inheriting from pystac.Catalog to
    ensure that inheritance, class methods, etc. function as expected."""

    case_1 = TestCases.get_path("data-files/catalogs/test-case-1/catalog.json")

    class BasicCustomCatalog(pystac.Catalog):
        def get_items(self) -> Iterator[Item]:  # type: ignore
            # This get_items does not have the `recursive` kwarg. This mimics
            # the current state of pystac-client and is intended to test
            # backwards compatibility of inherited classes
            return super().get_items()

    def test_from_dict_returns_subclass(self) -> None:
        self.stac_io = pystac.StacIO.default()
        catalog_dict = self.stac_io.read_json(self.case_1)
        custom_catalog = self.BasicCustomCatalog.from_dict(catalog_dict)
        assert isinstance(custom_catalog, self.BasicCustomCatalog)

    def test_from_file_returns_subclass(self) -> None:
        custom_catalog = self.BasicCustomCatalog.from_file(self.case_1)
        assert isinstance(custom_catalog, self.BasicCustomCatalog)

    def test_clone(self) -> None:
        custom_catalog = self.BasicCustomCatalog.from_file(self.case_1)
        cloned_catalog = custom_catalog.clone()
        assert isinstance(cloned_catalog, self.BasicCustomCatalog)

    def test_get_all_items_works(self) -> None:
        custom_catalog = self.BasicCustomCatalog.from_file(self.case_1)
        cloned_catalog = custom_catalog.clone()
        with pytest.warns(DeprecationWarning):
            cloned_catalog.get_all_items()

    def test_get_item_works(self) -> None:
        custom_catalog = self.BasicCustomCatalog.from_file(self.case_1)
        cloned_catalog = custom_catalog.clone()
        with pytest.warns(DeprecationWarning):
            cloned_catalog.get_item("area-1-1-imagery")


def test_custom_catalog_from_dict(catalog: Catalog) -> None:
    # https://github.com/stac-utils/pystac/issues/862
    class CustomCatalog(Catalog):
        @classmethod
        def from_dict(
            cls,
            d: dict[str, Any],
            href: str | None = None,
            root: Catalog | None = None,
            migrate: bool = True,
            preserve_dict: bool = True,
        ) -> CustomCatalog:
            return super().from_dict(d)

    _ = CustomCatalog.from_dict(catalog.to_dict())


@pytest.mark.parametrize("add_canonical", (True, False))
def test_remove_hierarchical_links(
    test_case_1_catalog: Catalog, add_canonical: bool
) -> None:
    test_case_1_catalog.remove_hierarchical_links(add_canonical=add_canonical)
    for link in test_case_1_catalog.links:
        assert not link.is_hierarchical()
    assert bool(test_case_1_catalog.get_single_link("canonical")) == add_canonical


def test_fully_resolve(tmp_path: Path, test_case_1_catalog: Catalog) -> None:
    test_case_1_catalog.save(dest_href=str(tmp_path / "before"))
    assert len(list((tmp_path / "before").glob("**/*.json"))) == 1
    test_case_1_catalog.fully_resolve()
    test_case_1_catalog.save(dest_href=str(tmp_path / "after"))
    assert len(list((tmp_path / "after").glob("**/*.json"))) == 15


def test_get_items_with_multiple_ids(test_case_1_catalog: Catalog) -> None:
    cat = test_case_1_catalog
    items = cat.get_items("area-2-1-imagery", "area-1-1-labels", recursive=True)
    assert len(list(items)) == 2


@pytest.mark.vcr()
def test_validate_all_with_max_n(test_case_1_catalog: Catalog) -> None:
    cat = test_case_1_catalog
    assert cat.validate_all() == 8
    assert cat.validate_all(max_items=6) == 6
    assert cat.validate_all(max_items=1) == 1


@pytest.mark.vcr()
def test_validate_all_with_recusive_off(test_case_1_catalog: Catalog) -> None:
    cat = test_case_1_catalog
    assert cat.validate_all() == 8
    assert cat.validate_all(recursive=False) == 0


@pytest.fixture
def nested_catalog() -> pystac.Catalog:
    """
    Structure:

    ├── catalog.json
    ├── products
    │   ├── catalog.json
    │   └── product_a
    │       └── catalog.json
    └── variables
        ├── catalog.json
        └── variable_a
            └── catalog.json
                └── variable_a_1
                    └── collection.json
    """
    root = pystac.Catalog("root", "root")
    variables = pystac.Catalog("variables", "variables")
    products = pystac.Catalog("products", "products")

    root.add_child(variables)
    root.add_child(products)

    variable_a = pystac.Catalog("variable_a", "variable_a")
    product_a = pystac.Catalog("product_a", "product_a")

    variables.add_child(variable_a)
    products.add_child(product_a)

    variable_a_1 = pystac.Collection(
        "variable_a_1", "variable_a_1", extent=ARBITRARY_EXTENT
    )
    variable_a.add_child(variable_a_1)

    return root


def test_get_all_collections_deeply_nested(nested_catalog: pystac.Catalog) -> None:
    catalog = nested_catalog
    all_collections = list(catalog.get_all_collections())

    assert len(all_collections) == 1
    assert all(isinstance(c, pystac.Collection) for c in all_collections)


def test_set_parent_false_stores_in_proper_place_on_normalize_and_save(
    nested_catalog: pystac.Catalog, tmp_path: Path
) -> None:
    root = nested_catalog
    product_a = next(root.get_child("products").get_children())  # type: ignore
    variable_a = next(root.get_child("variables").get_children())  # type: ignore

    variable_a.add_child(product_a, set_parent=False)

    root.normalize_and_save(
        root_href=str(tmp_path), catalog_type=pystac.CatalogType.ABSOLUTE_PUBLISHED
    )
    assert (tmp_path / "products" / "product_a").exists()
    assert not (tmp_path / "variables" / "variable_a" / "product_a").exists()


def test_set_parent_false_stores_in_proper_place_on_save(
    nested_catalog: pystac.Catalog, tmp_path: Path
) -> None:
    nested_catalog.normalize_and_save(
        root_href=str(tmp_path), catalog_type=pystac.CatalogType.ABSOLUTE_PUBLISHED
    )
    root = pystac.Catalog.from_file(tmp_path / "catalog.json")
    product_a = next(root.get_child("products").get_children())  # type: ignore
    variable_a = next(root.get_child("variables").get_children())  # type: ignore

    variable_a.add_child(product_a, set_parent=False)

    root.save(pystac.CatalogType.SELF_CONTAINED, dest_href=str(tmp_path))

    assert (tmp_path / "products" / "product_a").exists()
    assert not (tmp_path / "variables" / "variable_a" / "product_a").exists()


BEST_PRACTICE_CATALOG_TEMPLATE = "{id}"
BEST_PRACTICE_ITEM_TEMPLATE = "{id}"
TEST_CATALOG_TEMPLATE = "cat/${id}/${description}"
TEST_ITEM_TEMPLATE = "cat/items/${id}"
STRATEGY = TemplateLayoutStrategy(
    catalog_template=TEST_CATALOG_TEMPLATE, item_template=TEST_ITEM_TEMPLATE
)


@pytest.mark.parametrize(
    "root_strategy,sub_strategy,provided_root_strategy,provided_sub_strategy,root_template,sub_template",
    [
        (
            None,
            None,
            None,
            None,
            BEST_PRACTICE_CATALOG_TEMPLATE,
            BEST_PRACTICE_CATALOG_TEMPLATE,
        ),
        (STRATEGY, None, None, None, TEST_CATALOG_TEMPLATE, TEST_CATALOG_TEMPLATE),
        (
            STRATEGY,
            BestPracticesLayoutStrategy(),
            None,
            None,
            TEST_CATALOG_TEMPLATE,
            BEST_PRACTICE_CATALOG_TEMPLATE,
        ),
        (
            STRATEGY,
            None,
            BestPracticesLayoutStrategy(),
            None,
            BEST_PRACTICE_CATALOG_TEMPLATE,
            TEST_CATALOG_TEMPLATE,
        ),
        (
            STRATEGY,
            None,
            None,
            BestPracticesLayoutStrategy(),
            TEST_CATALOG_TEMPLATE,
            BEST_PRACTICE_CATALOG_TEMPLATE,
        ),
    ],
)
def test_add_child_layout_strategy(
    root_strategy: HrefLayoutStrategy,
    sub_strategy: HrefLayoutStrategy,
    provided_root_strategy: HrefLayoutStrategy,
    provided_sub_strategy: HrefLayoutStrategy,
    root_template: str,
    sub_template: str,
) -> None:
    """Test for layout strategy when adding a child.

    If no layout strategy is specified, children HREF should
    always follow BestPracticesLayoutStrategy.
    If only root strategy is set, all children HREFs should
    follow than strategy.
    If root and child strategy are set, root and child children
    may follow different strategies.
    Strategy provided to `add_child` always overrides other settings.
    """

    base_url = "http://example.com"
    catalog = Catalog(
        id="test",
        description="test desc",
        href=f"{base_url}/catalog.json",
        strategy=root_strategy,
    )
    subcat = Catalog(id="subcat", description="subcat desc", strategy=sub_strategy)
    subsubcat = Catalog(id="subsubcat", description="subsubcat desc")

    catalog.add_child(subcat, strategy=provided_root_strategy)
    subcat.add_child(subsubcat, strategy=provided_sub_strategy)

    root_template = root_template.format(
        id=subcat.id, description=subcat.description
    ).replace("$", "")
    sub_template = sub_template.format(
        id=subsubcat.id, description=subsubcat.description
    ).replace("$", "")

    assert subcat.self_href == f"{base_url}/{root_template}/catalog.json"
    assert (
        subsubcat.self_href == f"{base_url}/{root_template}/{sub_template}/catalog.json"
    )


@pytest.mark.parametrize(
    "root_strategy,sub_strategy,provided_root_strategy,"
    "root_template,sub_template,norm_template",
    [
        (
            None,
            None,
            None,
            BEST_PRACTICE_CATALOG_TEMPLATE,
            BEST_PRACTICE_CATALOG_TEMPLATE,
            BEST_PRACTICE_CATALOG_TEMPLATE,
        ),
        (
            STRATEGY,
            None,
            None,
            TEST_CATALOG_TEMPLATE,
            TEST_CATALOG_TEMPLATE,
            TEST_CATALOG_TEMPLATE,
        ),
        (
            STRATEGY,
            BestPracticesLayoutStrategy(),
            None,
            TEST_CATALOG_TEMPLATE,
            BEST_PRACTICE_CATALOG_TEMPLATE,
            TEST_CATALOG_TEMPLATE,
        ),
        (
            STRATEGY,
            None,
            BestPracticesLayoutStrategy(),
            TEST_CATALOG_TEMPLATE,
            TEST_CATALOG_TEMPLATE,
            BEST_PRACTICE_CATALOG_TEMPLATE,
        ),
    ],
)
def test_add_child_layout_strategy_normalize(
    root_strategy: HrefLayoutStrategy,
    sub_strategy: HrefLayoutStrategy,
    provided_root_strategy: HrefLayoutStrategy,
    root_template: str,
    sub_template: str,
    norm_template: str,
) -> None:
    """Test for layout strategy when adding a child and normalizing HREFs.

    If no layout strategy is specified, children HREF
    should always follow BestPracticesLayoutStrategy.
    If only root strategy is set, all children HREFs
    should follow than strategy.
    If root and child strategy are set, root strategy
    overrides child strategy.
    Strategy provided to `normalize_href` always
    overrides other settings.
    """

    base_url = "http://example.com"
    catalog = Catalog(
        id="test",
        description="test desc",
        href=f"{base_url}/catalog.json",
        strategy=root_strategy,
    )
    subcat = Catalog(id="subcat", description="subcat desc", strategy=sub_strategy)
    subsubcat = Catalog(id="subsubcat", description="subsubcat desc")
    catalog.add_child(subcat)
    subcat.add_child(subsubcat)

    _root_template = root_template.format(
        id=subcat.id, description=subcat.description
    ).replace("$", "")
    _sub_template = sub_template.format(
        id=subsubcat.id, description=subsubcat.description
    ).replace("$", "")

    assert subcat.self_href == f"{base_url}/{_root_template}/catalog.json"
    assert (
        subsubcat.self_href
        == f"{base_url}/{_root_template}/{_sub_template}/catalog.json"
    )

    catalog.normalize_hrefs(base_url, strategy=provided_root_strategy)

    _root_template = norm_template.format(
        id=subcat.id, description=subcat.description
    ).replace("$", "")
    _sub_template = norm_template.format(
        id=subsubcat.id, description=subsubcat.description
    ).replace("$", "")

    assert subcat.self_href == f"{base_url}/{_root_template}/catalog.json"
    assert (
        subsubcat.self_href
        == f"{base_url}/{_root_template}/{_sub_template}/catalog.json"
    )


@pytest.mark.parametrize(
    "root_strategy,provided_strategy,template",
    [
        (None, None, BEST_PRACTICE_ITEM_TEMPLATE),
        (STRATEGY, None, TEST_ITEM_TEMPLATE),
        (STRATEGY, BestPracticesLayoutStrategy(), BEST_PRACTICE_ITEM_TEMPLATE),
    ],
)
def test_add_item_layout_strategy(
    root_strategy: HrefLayoutStrategy,
    provided_strategy: HrefLayoutStrategy,
    template: str,
) -> None:
    """Test for layout strategy when adding an item.

    If no layout strategy is specified, item HREF
    should always follow BestPracticesLayoutStrategy.
    If only root strategy is set, all item HREFs
    should follow than strategy.
    Strategy provided to `add_item` always overrides other settings.
    """

    base_url = "http://example.com"
    item_id = "item_id"
    catalog = Catalog(
        id="test",
        description="test desc",
        href=f"{base_url}/catalog.json",
        strategy=root_strategy,
    )
    item = Item(
        id=item_id,
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [180.0, -90.0],
                    [180.0, 90.0],
                    [-180.0, 90.0],
                    [-180.0, -90.0],
                    [180.0, -90.0],
                ]
            ],
        },
        bbox=[-180, -90, 180, 90],
        datetime=datetime(2023, 1, 1),
        properties={},
        assets={
            "data": Asset(
                href="http://example.com/assets/data.tif",
                roles=["data"],
                title="DATA",
            )
        },
    )

    catalog.add_item(item, strategy=provided_strategy)

    template = template.format(id=item.id).replace("$", "")

    assert item.self_href == f"{base_url}/{template}/{item_id}.json"


def test_APILayoutStrategy_requires_root_to_be_url(
    catalog: Catalog, collection: Collection, item: Item
) -> None:
    collection.add_item(item)
    catalog.add_child(collection)
    with pytest.raises(
        pystac.errors.STACError,
        match="When using APILayoutStrategy the root_href must be a URL",
    ):
        catalog.normalize_hrefs(root_href="issues-1486", strategy=APILayoutStrategy())


def test_get_child_links_cares_about_media_type(catalog: pystac.Catalog) -> None:
    catalog.links.extend(
        [
            pystac.Link(
                rel="child", target="./child-1.json", media_type="application/json"
            ),
            pystac.Link(
                rel="child", target="./child-2.json", media_type="application/geo+json"
            ),
            pystac.Link(rel="child", target="./child-3.json"),
            # this one won't get counted since it's the wrong media_type
            pystac.Link(rel="child", target="./child.html", media_type="text/html"),
        ]
    )

    assert len(catalog.get_child_links()) == 3


def test_get_item_links_cares_about_media_type(catalog: pystac.Catalog) -> None:
    catalog.links.extend(
        [
            pystac.Link(
                rel="item", target="./item-1.json", media_type="application/json"
            ),
            pystac.Link(
                rel="item", target="./item-2.json", media_type="application/geo+json"
            ),
            pystac.Link(rel="item", target="./item-3.json"),
            # this one won't get counted since it's the wrong media_type
            pystac.Link(rel="item", target="./item.html", media_type="text/html"),
        ]
    )

    assert len(catalog.get_item_links()) == 3


def test_get_root_link_cares_about_media_type(catalog: pystac.Catalog) -> None:
    catalog.links.insert(
        0, pystac.Link(rel="root", target="./self.json", media_type="text/html")
    )
    root_link = catalog.get_root_link()
    assert root_link and root_link.target != "./self.json"
