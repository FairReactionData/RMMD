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
