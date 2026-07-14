from typing import Annotated, Literal

from pydantic import Discriminator, Field, Tag, model_validator
from .calc import CalculationBase, CalculationInputBase, CalculationOutputBase
from .thermo import FittedToLiterature, FittedToOtherCalculation
from ._base import RmmdBaseModel

from .keys import CitationKey, KineticsIndex
from .registry import HasKeyMixin


class _RateCoefficientBase(HasKeyMixin):
    """Base class for rate coefficients"""

    type: str
    """unique identifier for the type of rate coefficient"""

    references: list[CitationKey] | None = None
    """Related literature describing how the data was obtained. Can be used in addition to the references list of the main dataset/Schema."""
    sources: list[CitationKey] | None = None
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


class PressureDependentArrhenius(_RateCoefficientBase):
    """Pressure-dependent Arrhenius rate coefficient"""

    type: Literal["pressure-dependent Arrhenius"] = "pressure-dependent Arrhenius"

    A: list[float]
    """pre-exponential factor in SI units"""
    b: list[float]
    """temperature exponent"""
    Ea: list[float]
    """activation energy in J/mol"""
    p: list[float]
    """pressure points in Pa"""

    @model_validator(mode="after")
    def _check_lengths(self):
        if not (len(self.A) == len(self.b) == len(self.Ea) == len(self.p)):
            raise ValueError(
                "The lengths of A, b, Ea, and p must be the same for pressure-dependent Arrhenius."
            )
        return self


class RateTable(_RateCoefficientBase):
    """Rate coefficient table for a specific reaction"""

    type: Literal["rate table"] = "rate table"

    T: list[float]
    """Temperature points in K"""
    p: list[float]
    """Pressure points in Pa"""
    k: list[list[float]]
    """rate coefficients in SI units

    n x m array of rate constants where n is the number of pressure points and m is the
    number of temperature points.
    """


# TODO add rates from TST, master equation, etc.

RateCoefficient = Annotated[
    ModifiedArrhenius | PressureDependentArrhenius | RateTable,
    Field(discriminator="type"),
]


###############################################################################
# fitting provenance
###############################################################################


class FittedToKineticData(RmmdBaseModel):
    """kinetic datat that the coefficients of this model were fitted to"""

    rate_constants: list[KineticsIndex]
    """kinetic datat that the coefficients of this model were fitted to"""


# annotated union for better error messages:
def _fitted_to_discriminator(value: dict | RmmdBaseModel) -> str | None:
    if isinstance(value, dict):
        if "sources" in value:
            return "literature"
        elif "rate_constants" in value:
            return "kinetic data"
        elif "output_of" in value:
            return "calculation output"

    else:
        if hasattr(value, "sources"):
            return "literature"
        elif hasattr(value, "rate_constants"):
            return "kinetic data"
        elif hasattr(value, "output_of"):
            return "calculation output"

    # Could not determine the type, return None to let Pydantic handle the error
    return None


_FittedToUnion = Annotated[
    Annotated[FittedToLiterature, Tag("literature")]
    | Annotated[FittedToKineticData, Tag("kinetic data")]
    | Annotated[FittedToOtherCalculation, Tag("calculation output")],
    Discriminator(_fitted_to_discriminator),
]


class KineticsParameterFittingInput(CalculationInputBase):
    """input data for a fitting calculation"""

    fitted_to: _FittedToUnion | None = None
    """data/model that the coefficients of this model were fitted to.

    If the model was fitted to data form this dataset, an integer (starting at
    0) to indicate the index of the data in the thermo list of this species.
    """


class KineticsParameterFittingOutput(CalculationOutputBase):
    """output data for a fitting calculation"""

    rate_constants: KineticsIndex
    """model parameters that were fitted to the data"""

    # TODO add fit quality metric


class KineticsParameterFitting(
    CalculationBase[KineticsParameterFittingInput, KineticsParameterFittingOutput]
):
    """calculation of thermochemical properties derived from fitting to data"""

    type: Literal["kinetic param fit"] = "kinetic param fit"
