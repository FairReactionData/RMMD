"""Tests for rmmd.registry (HasKeyMixin and Registry)."""

import pytest
from pydantic import ValidationError

from rmmd.registry import HasKeyMixin, Registry


##############################################################################
# Fixtures / helpers
##############################################################################


class Item(HasKeyMixin):
    name: str


class ItemRegistry(Registry[Item], prefix="item"): ...


class OtherRegistry(Registry[Item], prefix="other"): ...


##############################################################################
# Registry construction and validation
##############################################################################


class TestRegistryConstruction:
    def test_empty_construction(self):
        r = ItemRegistry()
        assert len(r) == 0

    def test_construction_from_dict(self):
        r = ItemRegistry({"k1": Item(name="foo")})
        assert len(r) == 1
        assert r["k1"].name == "foo"

    def test_model_validate_assigns_key_field(self):
        r = ItemRegistry.model_validate({"k1": {"name": "foo"}})
        assert r["k1"].key == "k1"

    def test_model_validate_rejects_key_mismatch(self):
        with pytest.raises(ValidationError, match="key mismatch"):
            ItemRegistry.model_validate({"k1": {"name": "foo", "key": "wrong"}})

    def test_construction_sets_key_field(self):
        r = ItemRegistry({"k1": Item(name="foo")})
        assert r["k1"].key == "k1"

    def test_construction_allows_pre_set_matching_key(self):
        r = ItemRegistry({"k1": Item(name="foo", key="k1")})
        assert r["k1"].key == "k1"


##############################################################################
# __setitem__
##############################################################################


class TestSetItem:
    def test_setitem_assigns_key_when_none(self):
        r = ItemRegistry()
        i = Item(name="foo")
        r["k1"] = i
        assert i.key == "k1"

    def test_setitem_accepts_matching_key(self):
        r = ItemRegistry()
        i = Item(name="foo", key="k1")
        r["k1"] = i
        assert r["k1"] is i

    def test_setitem_rejects_mismatched_key(self):
        r = ItemRegistry()
        i = Item(name="foo", key="other")
        with pytest.raises(ValueError, match="key mismatch"):
            r["k1"] = i


##############################################################################
# add()
##############################################################################


class TestAdd:
    def test_add_auto_assigns_key(self):
        r = ItemRegistry()
        key = r.add(Item(name="foo"))
        assert key == "item-0001"
        assert r["item-0001"].name == "foo"

    def test_add_increments_key(self):
        r = ItemRegistry()
        k1 = r.add(Item(name="first"))
        k2 = r.add(Item(name="second"))
        assert k1 == "item-0001"
        assert k2 == "item-0002"

    def test_add_uses_pre_set_key(self):
        r = ItemRegistry()
        key = r.add(Item(name="foo", key="my-key"))
        assert key == "my-key"
        assert r["my-key"].name == "foo"

    def test_add_skips_existing_keys(self):
        r = ItemRegistry({"item-0001": Item(name="existing")})
        key = r.add(Item(name="new"))
        assert key == "item-0002"

    def test_add_counter_starts_above_highest_existing(self):
        r = ItemRegistry({"item-0005": Item(name="a"), "item-0003": Item(name="b")})
        key = r.add(Item(name="new"))
        assert key == "item-0006"

    def test_add_ignores_non_prefix_keys_for_counter(self):
        r = ItemRegistry({"custom-key": Item(name="a")})
        key = r.add(Item(name="new"))
        assert key == "item-0001"

    def test_add_sets_key_field_on_item(self):
        r = ItemRegistry()
        i = Item(name="foo")
        r.add(i)
        assert i.key == "item-0001"


##############################################################################
# Subclass prefix isolation
##############################################################################


class TestPrefixIsolation:
    def test_subclass_uses_own_prefix(self):
        r = OtherRegistry()
        key = r.add(Item(name="foo"))
        assert key == "other-0001"


##############################################################################
# Serialization / deserialization round-trip
##############################################################################


class TestSerialization:
    def test_model_dump_is_plain_dict(self):
        r = ItemRegistry({"k1": Item(name="foo"), "k2": Item(name="bar")})
        d = r.model_dump()
        assert d == {"k1": {"name": "foo"}, "k2": {"name": "bar"}}

    def test_key_absent_from_serialized_items(self):
        r = ItemRegistry()
        r.add(Item(name="foo"))
        d = r.model_dump()
        assert "key" not in d["item-0001"]

    def test_model_dump_json_round_trips(self):
        r = ItemRegistry({"k1": Item(name="foo")})
        r2 = ItemRegistry.model_validate_json(r.model_dump_json())
        assert r2["k1"].name == "foo"
        assert r2["k1"].key == "k1"

    def test_embedded_in_parent_model_round_trips(self):
        from pydantic import BaseModel

        class Parent(BaseModel):
            items: ItemRegistry = ItemRegistry()

        p = Parent(items={"k1": {"name": "foo"}})
        d = p.model_dump()
        assert d == {"items": {"k1": {"name": "foo"}}}

        p2 = Parent.model_validate(d)
        assert p2.items["k1"].name == "foo"
        assert p2.items["k1"].key == "k1"
