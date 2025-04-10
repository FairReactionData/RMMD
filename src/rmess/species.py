"""part of the schema for identifying species and reactions"""

from __future__ import annotations
from abc import ABC
from typing import Literal, TypeAlias


from pydantic import BaseModel
from rmess.thermo import ThermoProperty

from .rmess import ElectronicState, PesReaction, Point

from .keys import CitationKey


class Species(BaseModel):
    """A chemical species."""

    entities: list[MolecularEntity]
    """a species is an ensemble of molecular entities. If the molecular
    entities can be described using only canonical representations, there
    automatically is a canonical representation for the species.
    """
    thermo: list[ThermoProperty]
    """thermochemical properties for this species"""
    transport: list[TransportProperty]
    """transport properties for this species"""

class MolecularEntity(BaseModel):
    """identifiable and distinguishable entity

    """
    # TODO find different name: according to the IUPAC goldbook, the meaning of "molecular entity" varies with context, e.g., in quantum chemistry context, the Point class fits the definition of "molecular entity" better than this class -> "CanonicalEntity"?

    # TODO canonical representation of each field; this is similar to the layers of an InChI
    constitution: Constitution
    connectivity: MolecularConnectivity
    isotope: Isotopes|None = None
    stereo: Stereochemistry|None = None
    electronic_state: ElectronicState|None = None
    """usually the ground state is assumed"""
    points: list[Point]|Literal['all'] = 'all'

    # TODO introduce separate Molecular entity definiton? -> e.g. what about crystals, other materials

class TransportProperty(BaseModel):
    """Transport property for species"""

class CoarseNode(BaseModel):
    """Node in a reaction network"""

    # can be extended, if necessary, subclasses for some roles can
    # add additional fields
    role: Literal['reactant', 'product', 'solvent', 'catalyst']
    species: Species

class Reaction(BaseModel):
    """A chemical reaction"""

    nodes: list[CoarseNode]
    definition: ReactionDefinition

class ReactionDefinition(BaseModel):
    """connects the coarse edge to detailed
    edges
    """

    references: list[CitationKey]|None = None
    """Literature reference where the detailed data was combined to a
    phenomenological reaction (rate). """
    pes_reaction: PesReaction



##############################################################################
# identifiers -> move to separate module?
##############################################################################

# TODO how to serialize molecular entities?
class Constitution(BaseModel):
    """Molecular constitution"""

    element_count: dict[str, int]
    """example {"C": 1, "H": 4}"""

class Isotopes(BaseModel):
    """Isotope information for each atom"""

    n_neutrons: list[int]
    """number of neutrons for each atom"""

class MolecularConnectivity(BaseModel):
    """Connectivity between atoms"""

    # TODO graph data structure + canonical form for easy comparison
    # TODO special values for formed and broken bonds (for transition states, etc.)

class Stereochemistry(BaseModel):
    """Definition of the Stereochemistry"""

    # TODO define via stereocenters

class StringIdentifier(BaseModel, ABC):

    type: str   # for easy identification of subtypes during validation
    value: str
    canonical_repr: str

class StandardInChI(StringIdentifier):
    """Standard IUPAC International Chemical Identifier

    Its value is the canonical_repr, since it is a canonical string
    representation."""

    type: Literal['SInChI']


class SMILES(StringIdentifier):
    """..."""

    type: Literal['SMILES']


SpeciesIdentifier: TypeAlias = Constitution|StandardInChI|SMILES
"""implementation detail: validation schemas do not support inheritance in the
classical sense. Instead, all subclasses have to be validated against."""

