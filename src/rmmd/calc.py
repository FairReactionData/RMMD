from __future__ import annotations

from typing import Annotated, Generic, Literal, TypeVar
from annotated_types import MinLen
from pydantic import BaseModel
from rmmd.keys import CalcIndex
from rmmd.metadata import CitationKeyOrDirectReference, HttpUrlReference

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Software(BaseModel):
    """computer software used to perform a calculation"""

    name: Annotated[str, MinLen(1)]
    """name of the software"""
    version: Annotated[str, MinLen(1)]
    """version number or Git hash of the software used for the calculation"""
    repository: HttpUrlReference | None = None
    """URL to the software repository, e.g., GitHub or GitLab"""


class CalculationBase(BaseModel, Generic[InputT, OutputT]):
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

    input: list[CitationKeyOrDirectReference] | InputT | None = None
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
