# Full Schema
from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from ._base import RmmdBaseModel
from .calc import GeneralCalculation, NestedCalculation
from .keys import CitationKey
from .kinetics import RateCoefficient
from .metadata import Doi, LocalCffFile, Metadata, Reference
from .pes import Conformation, ConformationRelation, QmCalculation
from .registry import Registry
from .species import MolecularEntity, Reaction, Species, TransportProperty
from .thermo import (
    STATE_1_BAR_298_K,
    EmpiricalThermo,
    ReferenceState,
    TabularThermo,
    ThermoParameterFitting,
    ThermoQmCalc,
)

_ThermoItem: TypeAlias = Annotated[
    EmpiricalThermo | TabularThermo,
    Field(discriminator="type"),
]

_CalculationItem: TypeAlias = Annotated[
    QmCalculation
    | ThermoQmCalc
    | NestedCalculation
    | GeneralCalculation
    | ThermoParameterFitting,
    Field(discriminator="type"),
]

##############################################################################
# Registry subclasses
##############################################################################


class SpeciesRegistry(Registry[Species], prefix="species"): ...


class EntityRegistry(Registry[MolecularEntity], prefix="entity"): ...


class ReactionRegistry(Registry[Reaction], prefix="reaction"): ...


class ThermoRegistry(Registry[_ThermoItem], prefix="thermo"): ...


class TransportRegistry(Registry[TransportProperty], prefix="transport"): ...


class RateCoefficientsRegistry(
    Registry[RateCoefficient], prefix="rate-coefficient"
): ...


class ConformationRegistry(Registry[Conformation], prefix="conformation"): ...


class PesRelationRegistry(Registry[ConformationRelation], prefix="pes-relation"): ...


class CalculationRegistry(Registry[_CalculationItem], prefix="calc"): ...


##############################################################################
# Root schema
##############################################################################


class Schema(RmmdBaseModel, extra="forbid"):
    """The final schema, encapsulating all information"""

    ### mechanism view ###
    species: SpeciesRegistry = Field(default_factory=SpeciesRegistry)
    """chemical species in the dataset"""
    entities: EntityRegistry = Field(default_factory=EntityRegistry)
    """canonical representation of the species in the dataset. InChiKeys are generated including the fixed-H layer"""
    reactions: ReactionRegistry = Field(default_factory=ReactionRegistry)
    """reactions in the dataset"""
    default_reference_state: ReferenceState = Field(default=STATE_1_BAR_298_K)
    """default thermodynamic reference state for the dataset"""
    thermo: ThermoRegistry = Field(default_factory=ThermoRegistry)
    """thermodynamic models for species and reactions in the dataset,
    e.g., NASA polynomials"""
    transport: TransportRegistry = Field(default_factory=TransportRegistry)
    """transport properties for species in the dataset"""
    rate_coefficients: RateCoefficientsRegistry = Field(
        default_factory=RateCoefficientsRegistry
    )
    """kinetic models for reactions in the dataset, e.g., Arrhenius expressions or rate tables"""

    ### electronic structure view ###
    conformations: ConformationRegistry = Field(default_factory=ConformationRegistry)
    """conformations in the dataset"""
    pes_relations: PesRelationRegistry = Field(default_factory=PesRelationRegistry)
    """relations between conformations, e.g., which conformations are considered to be
    the same, which conformations are connected by an IRC path, ..."""
    calculations: CalculationRegistry = Field(default_factory=CalculationRegistry)
    """quantum chemistry calculations"""

    ### metadata ###
    schema_version: Literal["0.1.0b0"] = "0.1.0b0"
    """version of the schema used"""
    metadata: LocalCffFile | Metadata
    """dataset metadata

    Can be supplied directly in the RMMD file or by referencing another metadata file
    such as a CITATION.CFF
    """

    literature: dict[CitationKey, Doi | Reference] = Field(default_factory=dict)
    """table of all literature referenced in this file"""


Schema.model_rebuild()
