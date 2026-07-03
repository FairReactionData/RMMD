"""Registry: a string-keyed mapping with automatic key assignment.

Provides HasKeyMixin and Registry for use in the root schema instead of plain lists.
Each item carries an optional ``key`` field (excluded from serialization) that is
kept in sync with its position in the mapping.
"""

from __future__ import annotations

from collections.abc import MutableMapping
import itertools
from typing import ClassVar, Generic, Self, TypeVar

from pydantic import Field, PrivateAttr, RootModel, model_validator
from .keys import RegistryKey

from ._base import RmmdBaseModel


class HasKeyMixin(RmmdBaseModel):
    """Mixin for models stored in a Registry.

    Adds an optional ``key`` field that mirrors the item's mapping key.
    The field is excluded from serialization to avoid redundancy.
    """

    key: RegistryKey | None = Field(exclude=True, default=None)


T = TypeVar("T", bound=HasKeyMixin)


class Registry(
    RootModel[dict[RegistryKey, T]],
    MutableMapping[RegistryKey, T],
    Generic[T],
):
    """A mapping of string key -> item with automatic key assignment.

    Subclass with a ``prefix`` keyword argument to control the prefix used
    for auto-generated keys::

        class CalcRegistry(Registry[Calculation], prefix="calc"): ...

    Auto-generated keys have the form ``"<prefix>-<index:04d>"``, e.g.
    ``"calc-0001"``.  The counter starts above the highest index already
    present so that adding items to a loaded registry never produces
    collisions.
    """

    prefix: ClassVar[str] = "item"

    root: dict[RegistryKey, T] = Field(default_factory=dict)

    _counter: itertools.count[int] = PrivateAttr()

    def __init_subclass__(cls, prefix: str = "item", **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls.prefix = prefix

    def model_post_init(self, __context: object) -> None:
        highest_idx = 0
        p_dash = f"{self.prefix}-"
        for k in self.root:
            if k.startswith(p_dash):
                try:
                    highest_idx = max(highest_idx, int(k[len(p_dash) :]))
                except ValueError:
                    pass
        self._counter = itertools.count(highest_idx + 1)

    ##########################################################################
    # MutableMapping ABC
    ##########################################################################

    def __getitem__(self, key: RegistryKey) -> T:
        return self.root[key]

    def __iter__(self):
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __delitem__(self, key: RegistryKey) -> None:
        del self.root[key]

    def __contains__(self, key: object) -> bool:
        return key in self.root

    def __setitem__(self, key: RegistryKey, value: T) -> None:
        if value.key is None:
            object.__setattr__(value, "key", key)
        elif value.key != key:
            raise ValueError(
                f"key mismatch: mapping key '{key}' does not match "
                f"value.key '{value.key}'"
            )
        self.root[key] = value

    ##########################################################################
    # Convenience API
    ##########################################################################

    def _next_key(self) -> str:
        """Return the next auto-generated key that is not already in use."""
        while (key := f"{self.prefix}-{next(self._counter):04d}") in self.root:
            pass
        return key

    def add(self, value: T) -> RegistryKey:
        """Add *value*, auto-assigning a key when ``value.key`` is ``None``.

        Returns the key under which the item was stored.  If the item
        already has a ``key``, that key is used unchanged.  An existing
        entry with the same key is overwritten.
        """
        if value.key is None:
            object.__setattr__(value, "key", self._next_key())
            assert value.key is not None  # for type checker
        self[value.key] = value
        return value.key

    def __str__(self) -> str:
        return str(self.root)

    ##########################################################################
    # Pydantic hooks
    ##########################################################################

    @model_validator(mode="after")
    def _sync_key_fields(self) -> Self:
        """Populate ``item.key`` for items that lack one; raise on mismatch."""
        mismatched: list[tuple[str, str]] = []

        for key, value in self.root.items():
            if value.key is None:
                object.__setattr__(value, "key", key)
            elif value.key != key:
                mismatched.append((key, value.key))

        if mismatched:
            details = ", ".join(
                f"mapping key '{k}' != item.key '{vk}'" for k, vk in mismatched
            )
            raise ValueError(f"key mismatch: {details}")

        return self
