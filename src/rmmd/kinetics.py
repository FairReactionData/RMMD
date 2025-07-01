from typing import Annotated, Literal

from pydantic import BaseModel, Field
from .keys import CitationKey


class _RateCoefficientBase(BaseModel):
    """Base class for rate coefficients"""

    type: str
    """unique identifier for the type of rate coefficient"""

    references: list[CitationKey] | None = None
    """Related literature describing how the data was obtained. Can be used in addition to the references list of the main dataset/Schema."""
    source: list[CitationKey]
    """Literature reference where the data was obtained from."""


class ModifiedArrhenius(_RateCoefficientBase):
    """Modified Arrhenius rate coefficient"""

    type: Literal["modified Arrhenius"] = "modified Arrhenius"

    A: float
    """pre-exponential factor in SI units"""
    b: float
    """temperature exponent"""
    Ea: float
    """activation energy in J/mol"""


class RateTable(_RateCoefficientBase):
    """Rate coefficient table for a specific reaction"""

    type: Literal["T rate table"] = "T rate table"

    T: list[float]
    """Temperature points in K"""
    p: list[float] | float
    """Pressure points in Pa"""
    k: list[float]
    """rate coefficients in SI units"""


# TODO add rates from TST, master equation, etc.

RateCoefficient = Annotated[ModifiedArrhenius, Field(discriminator="type")]
