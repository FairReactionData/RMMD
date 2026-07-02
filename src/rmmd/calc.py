from __future__ import annotations

from typing import Annotated, Generic, Literal, TypeVar

from annotated_types import MinLen

from ._base import RmmdBaseModel
from .keys import CalcIndex
from .metadata import CitationKeyOrDirectReference, UrlNoDoiOrg
from .registry import HasKeyMixin

##############################################################################
# Base classes for calculation input and output
##############################################################################


class CalculationInputBase(RmmdBaseModel):
    """Base class for the input of a calculation.

    All specific input types should inherit from this class. The ``sources``
    field can be used to reference the location of the input data (e.g., an
    input file in the dataset) without or in addition to providing structured
    data in the subclass fields.
    """

    sources: list[CitationKeyOrDirectReference] | None = None
    """Location of the input data, e.g., a file in the current dataset or a
    reference to a published dataset."""


class CalculationOutputBase(RmmdBaseModel):
    """Base class for the output of a calculation.

    All specific output types should inherit from this class. The ``sources``
    field can be used to reference the location of the output data (e.g., an
    output file in the dataset) without or in addition to providing structured
    data in the subclass fields.
    """

    sources: list[CitationKeyOrDirectReference] | None = None
    """Location of the output data, e.g., a file in the current dataset or a
    reference to a published dataset."""


# non-optional sources filed to allow supplying just the sources without any structured
# data. Useful for cases where no schema was defined for a specific kind of calculation,
# but not recommended for cases where it was.
class CalculationInputSourcesOnly(RmmdBaseModel):
    """Calculation input defined only by referencing other resources, e.g., input files."""

    sources: list[CitationKeyOrDirectReference]


class CalculationOutputSourcesOnly(RmmdBaseModel):
    """Calculation output defined only by referencing other resources, e.g., log files."""

    sources: list[CitationKeyOrDirectReference]


class Software(RmmdBaseModel):
    """computer software used to perform a calculation"""

    name: Annotated[str, MinLen(1)]
    """name of the software"""
    version: Annotated[str, MinLen(1)]
    """version number or Git hash of the software used for the calculation"""
    repository: UrlNoDoiOrg | None = None
    """URL to the software repository, e.g., GitHub or GitLab"""


class OutputOf(RmmdBaseModel):
    """helper class to declare that a calculation's output is the input for another"""

    output_of: CalcIndex
    """index of the calculation that produces the output of this calculation"""


InputT = TypeVar("InputT", bound=CalculationInputBase | CalculationInputSourcesOnly)
OutputT = TypeVar("OutputT", bound=CalculationOutputBase | CalculationOutputSourcesOnly)


class CalculationBase(HasKeyMixin, Generic[InputT, OutputT]):
    type: str
    """type of the calculation"""

    software: Software
    """software used for the calculation"""

    description: str | None = None
    """description of the calculation, e.g., the method used"""

    references: list[CitationKeyOrDirectReference] | None = None
    """literature describing the calculation

    .. note::

        This field should not be confused with the reference to the data/files
        produced by this calculation, which should be given in
        ``output.sources``.

    Can be used in addition to the references for the whole dataset, e.g., to
    reference a specific paper describing the method used for this calculation.
    """

    input: InputT | CalculationInputSourcesOnly | None = None
    """input data/parameters for the calculation

    Structured input data specific to the calculation type (recommended), or, if
    structured data is not available, the input can be given as a reference to
    another resource containing the data (e.g. a file in this dataset) by providing
    ``input.sources``.
    """

    output: OutputT | CalculationOutputSourcesOnly | None = None
    """output data for the calculation

    Structured output data specific to the calculation type (recommended), or, if
    unavailable, a references to the raw output data provided via ``output.sources``.
    """


class NestedCalculation(CalculationBase[CalculationInputBase, CalculationOutputBase]):
    """Sometimes, it is more convenient to reference multiple calculations together,
    e.g., when they were performed in a single run of a quantum chemistry
    software and share a single output file. In that case, this class can
    be used to reference multiple calculations together.
    """

    type: Literal["nested"] = "nested"
    """type of the calculation"""

    calculations: Annotated[list[CalcIndex], MinLen(2)]
    """list of calculation ids that are referenced together in this nested
    calculation
    """


class GeneralCalculation(
    CalculationBase[CalculationInputSourcesOnly, CalculationOutputSourcesOnly]
):
    """General calculation to use if no suitable specific calculation class is available.

    The specification of input and output data is limited to providing references to the
    raw data files via ``input.sources`` and ``output.sources``. No structured data is
    provided in the RMMD file in this case.
    """

    type: Literal["general"] = "general"
    """type of the calculation"""
