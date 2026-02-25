# Full Schema
from typing import Annotated, Literal, TypeAlias

from rmmd.calc import NestedCalculation

from .kinetics import RateCoefficient

from .thermo import (
    STATE_1_BAR_298_K,
    EmpiricalThermo,
    ReferenceState,
    TabularThermo,
    ThermoQmCalc,
)

from .keys import CitationKey, EntityKey, SpeciesName
from .pes import Conformation, QmCalculation
from .metadata import Citation, CitationKeyOrDirectReference, Reference
from .species import MolecularEntity, Reaction, Species, TransportProperty

from pydantic import BaseModel, Field


# items in the thermo list below. Used for validation.
_ThermoItem: TypeAlias = Annotated[
    # TODO replace BoltzmannWeithedEnsemble with more general ThermoCalculation
    EmpiricalThermo | TabularThermo,
    Field(discriminator="type"),
]

_CalculationItem: TypeAlias = Annotated[
    QmCalculation | ThermoQmCalc | NestedCalculation,
    Field(discriminator="type"),
]


class Schema(BaseModel, extra="forbid"):
    """The final schema, encapsulating all information"""

    ### mechanism view ###
    species: dict[SpeciesName, Species] = Field(default_factory=dict)
    """chemical species in the dataset"""
    entities: dict[EntityKey, MolecularEntity] = Field(default_factory=dict)
    """canonical representation of the species in the dataset. InChiKeys are generated including the fixed-H layer"""
    reactions: list[Reaction] = Field(default_factory=list)
    """reactions in the dataset"""
    default_reference_state: ReferenceState = Field(default=STATE_1_BAR_298_K)
    """default thermodynamic reference state for the dataset"""
    thermo: list[_ThermoItem] = Field(default_factory=list)
    """thermodynamic models for species and reactions in the dataset,
    e.g., NASA polynomials"""
    transport: list[TransportProperty] = Field(default_factory=list)
    """transport properties for species in the dataset"""
    rate_coefficients: list[RateCoefficient] = Field(default_factory=list)
    """kinetic models for reactions in the dataset, e.g., Arrhenius expressions or rate tables"""

    ### electronic structure view ###
    conformations: list[Conformation] = Field(default_factory=list)
    """conformations in the dataset"""
    calculations: list[_CalculationItem] = Field(default_factory=list)
    """quantum chemistry calculations"""

    ### metadata ###
    schema_version: Literal["0.1.0b0"] = "0.1.0b0"
    """version of the schema used"""
    license: str
    """license of this dataset"""

    preferred_citation: Citation | None = None
    """how this dataset should be cited"""
    references: list[CitationKeyOrDirectReference] | None = None
    """literature describing this dataset, e.g., a set of papers describing how the data was obtained"""
    literature: dict[CitationKey, Reference] = Field(default_factory=dict)
    """table of all literature referenced in this file"""


Schema.model_rebuild()
