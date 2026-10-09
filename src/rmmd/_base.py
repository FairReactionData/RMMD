from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

RMMD_DEFAULT_CONFIG = ConfigDict(
    extra="forbid",
    use_attribute_docstrings=True,
    # keep `frozen` unset here (not ``False``) to support a child freezing an unfrozen
    # RmmdBaseModel's fields by way of pydantic mergin the configs of all bases
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


NonEmptyStr = Annotated[str, Field(min_length=1)]
"""non-empty string type"""

NonEmptyOptionalStr = Annotated[NonEmptyStr | None, Field(default=None)]
"""non-empty optional string type"""


class HasDescriptionMixin(RmmdBaseModel):
    """Mixin adding an optional human-readable description field."""

    description: NonEmptyOptionalStr = None
    """human-readable description"""
