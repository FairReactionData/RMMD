from __future__ import annotations

from typing import Annotated

from annotated_types import MinLen
from pydantic import BaseModel, ConfigDict

RMMD_DEFAULT_CONFIG = ConfigDict(
    extra="forbid",
    use_attribute_docstrings=True,
)
"""default configuration for all RMMD data models."""


class RmmdBaseModel(BaseModel):
    """base class for all RMMD data models"""

    model_config = RMMD_DEFAULT_CONFIG


class RmmdFrozenBaseModel(BaseModel, frozen=True):
    """base class for all frozen RMMD data models"""

    model_config = RMMD_DEFAULT_CONFIG | ConfigDict(
        frozen=True,
    )


# Deliberately not an ``RmmdBaseModel`` subclass: pydantic's frozen/non-frozen
# consistency check (enforced by its pyright plugin) forbids mixing a frozen and
# a non-frozen ``BaseModel`` in one MRO
# Still works as a mixin, if listed in the MRO before (Frozen)RmmdBaseModel.
class HasDescriptionMixin:
    """Mixin adding an optional human-readable description field."""

    description: Annotated[str, MinLen(1)] | None = None
    """human-readable description providing more details"""
