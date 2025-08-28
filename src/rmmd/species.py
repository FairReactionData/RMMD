"""part of the schema for identifying species and reactions"""

from __future__ import annotations
from abc import ABC
from typing import Annotated, Literal, TypeAlias


from pydantic import BaseModel, Field

from .thermo import SpeciesThermo
from .pes import ElectronicState, PesPath
from .keys import EntityKey, ConformationId, SpeciesName


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


class MolecularEntity(BaseModel):
    """A distinct molecule, ion, radical, complex, ... with a specific rigid stereochemistry and electronic state.

    Here, flexible conformational spatial rearrangements are by default not distinguished, i.e., a molecular entity can have multiple conformers.
    """

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
    defining_conformations: list[ConformationId] | Literal["all"] = "all"
    """While by default, all confomrations with the same stereochemistry and electronic state are considered part of the same molecular entitiy, this field can be used to restrict the set of conformations. In some cases,
    conformations have to belong to separate species to correctly model the kinetics of a system, but they have the same stereochemistry and electronic state. For example, different pre-reactive complexes where the fragements each have the same stereochemistry and electronic state, but different orientations relative to each other. In this case, the different pre-reactive complexes can be defined as different molecular entities with the same constitution, connectivity, stereo, and electronic state, but different defining_conformations.
    """
    conformations: list[ConformationId] = Field(default_factory=list)
    """list of conformations that have been identified for this molecular entity.

    Expecially, if `defining_conformations` is "all" and the molecular
    strucutre is flexible, this list is not guaranteed to be exhaustive as not
    all conformations may have been identified.
    """

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


class SpeciesRole(BaseModel):
    """Node in a reaction network"""

    # can be extended, if necessary, subclasses for some roles can
    # add additional fields
    role: Literal["reactant", "product", "solvent", "catalyst"]
    species: SpeciesName


class Reaction(BaseModel):
    """A chemical reaction"""

    species: list[SpeciesRole]
    pes_paths: list[PesPath] = Field(default_factory=list)


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
