
# Full Schema
from typing import Literal

from .keys import CitationKey, SpeciesName
from .rmess import Point, QcCalculation
from .metadata import Citation, Reference
from .species import Reaction, Species

from pydantic import BaseModel, Field


class Schema(BaseModel):
    """The final schema, encapsulating all information"""

    ### mechanism view ###
    species: dict[SpeciesName, Species] = Field(default_factory=dict)
    """chemical species in the dataset"""
    reactions: list[Reaction] = Field(default_factory=list)
    """reactions in the dataset"""

    ### electronic structure view ###
    points: list[Point] = Field(default_factory=list)
    """points in the dataset"""
    calculations: list[QcCalculation] = Field(default_factory=list)
    """quantum chemistry calculations"""

    ### metadata ###
    schema_version: Literal["1.0.0b0"] = "1.0.0b0"
    """version of the schema used"""
    license: str
    """license of this dataset"""

    preferred_citation: Citation|None = None
    """how this dataset should be cited"""
    references: list[CitationKey]|None = None
    """literature describing this dataset, e.g., a set of papers describing how the data was obtained"""
    literature: dict[CitationKey, Reference] = Field(default_factory=dict)
    """table of all literature referenced in this file"""

