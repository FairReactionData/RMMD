"""part of the schema for identifying species and reactions"""

from __future__ import annotations
from abc import ABC
from typing import Annotated, Literal, TypeAlias


from pydantic import BaseModel, Field

from .metadata import CitationKeyOrDirectReference
from .thermo import SpeciesThermo
from .pes import ElectronicState, PesReaction
from .keys import EntityKey, PointId, SpeciesName


class Species(BaseModel):
    """A chemical species."""

    name: str | None = None
    """human-readable name of the species. This is not a unique identifier,
    but can be used to identify the species in a human-readable way.
    """
    entities: list[EntityKey] = Field(min_length=1)
    """a species is an ensemble of molecular entities. If the molecular
    entities can be described using only canonical representations, there
    automatically is a canonical representation for the species.
    """
    thermo: list[SpeciesThermo] = Field(default_factory=list)
    """thermochemical properties for this species"""
    transport: list[TransportProperty] = Field(default_factory=list)
    """transport properties for this species"""


class CanonicalEntity(BaseModel):
    """identifiable and distinguishable entity"""

    # TODO find different name: according to the IUPAC goldbook, the meaning of "molecular entity" varies with context, e.g., in quantum chemistry context, the Point class fits the definition of "molecular entity" better than this class -> "CanonicalEntity"?

    # TODO canonical representation of each field; this is similar to the layers of an InChI
    constitution: Constitution
    connectivity: MolecularConnectivity
    isotopes: list[int] | Literal["natural-abundance"] | Literal["most-common"] = (
        "natural-abundance"
    )
    """number of neutrons for each atom"""
    stereo: Stereochemistry | None = None
    electronic_state: ElectronicState | None = None
    """usually the ground state is assumed"""
    points: list[PointId] | Literal["all"] = "all"
    """list of points on a PES that correspond to this molecular entity. If not
    "all", the representation is not canonical -> use carefully!"""

    # TODO introduce separate Molecular entity definiton? -> e.g. what about crystals, other materials

    # If we explicitly represent the different information layers, we need a
    # more concise form to refer to each entity. InChIKeys with H-layers is
    # one way to get a canonical representation although InChIs cannot
    # distinguish all species relevant in gas-phase kinetics contexts. The
    # representation of each layer does not even need to be canonical, as long
    # as we have a function that produces a canonical representation.
    # TODO better canoncial representation of each layer
    def inchi_key_h_layer(self) -> str:
        """returns the InChI key of the entity, including the fixed-H layer"""
        # TODO implement
        return "AAAAAAAAAAAAAA-AAAAAAAAAA-A"


class TransportProperty(BaseModel):
    """Transport property for species"""


class CoarseNode(BaseModel):
    """Node in a reaction network"""

    # can be extended, if necessary, subclasses for some roles can
    # add additional fields
    role: Literal["reactant", "product", "solvent", "catalyst"]
    species: SpeciesName


class Reaction(BaseModel):
    """A chemical reaction"""

    nodes: list[CoarseNode]
    definition: ReactionDefinition


class ReactionDefinition(BaseModel):
    """connects the coarse edge to detailed
    edges
    """

    references: list[CitationKeyOrDirectReference] | None = None
    """Literature reference where the detailed data was combined to a
    phenomenological reaction (rate). """
    pes_reaction: PesReaction


##############################################################################
# identifiers -> move to separate module?
##############################################################################

# TODO use "Composition" instead of "Constitution"?
Constitution = Annotated[
    dict[str, int],
    Field(
        examples=[{"C": 1, "H": 4}],
    ),
]
""""element count, e.g. {'C': 1, 'H': 4}"""


# TODO use existing standard (e.g. "non-standard" InChI with fixed-H layer) or define canonical numbering of atoms, ...?
class MolecularConnectivity(BaseModel):
    """Connectivity between atoms"""

    # TODO graph data structure + canonical form for easy comparison
    # TODO special values for formed and broken bonds (for transition states, etc.)


class Stereochemistry(BaseModel):
    """Definition of the Stereochemistry"""

    # TODO define via stereocenters


class StringIdentifier(BaseModel, ABC):
    type: str  # for easy identification of subtypes during validation
    value: str
    canonical_repr: str


class StandardInChI(StringIdentifier):
    """Standard IUPAC International Chemical Identifier

    Its value is the canonical_repr, since it is a canonical string
    representation."""

    type: Literal["SInChI"]


class SMILES(StringIdentifier):
    """..."""

    type: Literal["SMILES"]


SpeciesIdentifier: TypeAlias = Constitution | StandardInChI | SMILES
"""implementation detail: validation schemas do not support inheritance in the
classical sense. Instead, all subclasses have to be validated against."""
