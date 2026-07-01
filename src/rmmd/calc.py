from __future__ import annotations

from typing import Annotated, Generic, Literal, TypeVar
from annotated_types import MinLen

from ._base import RmmdBaseModel
from .keys import CalcIndex
from .metadata import CitationKeyOrDirectReference, UrlNoDoiOrg

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


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


class CalculationBase(RmmdBaseModel, Generic[InputT, OutputT]):
    type: str
    """type of the calculation"""

    software: Software
    """software used for the calculation"""

    references: list[CitationKeyOrDirectReference] | None = None
    """literature describing the calculation

    .. note::

        This field should not be confused with the reference to the data that this
        calculation produced, which should be given  in the ``output`` field.

    Can be used in addition to the references for the whole dataset, e.g., to reference a
    specific paper describing the method used for this calculation.
    """

    input: list[CitationKeyOrDirectReference | OutputOf] | InputT | None = None
    """input data/parameters for the calculation

    Ideally, the data is given as structured RMMD data. Additionally, or if
    structured data is not available, the input can be given as a reference to
    a data set. In that case, the identifier should not point to the whole
    dataset, but to a specific file/directory in the dataset, e.g., the input
    file for a quantum chemistry calculation.
    """

    output: list[CitationKeyOrDirectReference] | OutputT | None = None
    """output data for the calculation

    Ideally, the data is given as structured RMMD data. Additionally, or if
    structured data is not available, the input can be given as a reference to
    a data set. In that case, the identifier should not point to the whole
    dataset, but to a specific file/directory in the dataset, e.g., the input
    file for a quantum chemistry calculation.
    """


class NestedCalculation(CalculationBase[InputT, OutputT]):
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
