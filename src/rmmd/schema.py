
# Full Schema
from typing import Literal

from .keys import CitationKey, EntityKey, SpeciesName
from .rmess import Point, QmCalculation
from .metadata import Citation, CitationKeyOrDirectReference, Reference
from .species import CanonicalEntity, Reaction, Species

from pydantic import BaseModel, Field


class Schema(BaseModel):
    """The final schema, encapsulating all information"""

    ### mechanism view ###
    species: dict[SpeciesName, Species] = Field(default_factory=dict)
    """chemical species in the dataset"""
    entities: dict[EntityKey, CanonicalEntity] = Field(default_factory=dict)
    """canonical representation of the species in the dataset. InChiKeys are generated including the fixed-H layer"""
    reactions: list[Reaction] = Field(default_factory=list)
    """reactions in the dataset"""


    ### electronic structure view ###
    points: list[Point] = Field(default_factory=list)
    """points in the dataset"""
    calculations: list[QmCalculation] = Field(default_factory=list)
    """quantum chemistry calculations"""

    ### metadata ###
    schema_version: Literal["0.1.0b0"] = "0.1.0b0"
    """version of the schema used"""
    license: str
    """license of this dataset"""

    preferred_citation: Citation|None = None
    """how this dataset should be cited"""
    references: list[CitationKeyOrDirectReference]|None = None
    """literature describing this dataset, e.g., a set of papers describing how the data was obtained"""
    literature: dict[CitationKey, Reference] = Field(default_factory=dict)
    """table of all literature referenced in this file"""


Schema.model_rebuild()
