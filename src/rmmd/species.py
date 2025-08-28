"""part of the schema for identifying species and reactions"""

from __future__ import annotations
from abc import ABC
from typing import Annotated, Literal, TypeAlias


from pydantic import BaseModel, Field, field_validator

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

    identifiers: list[StringIdentifier] = Field(
        default_factory=list,
        description="list of string identifiers for the molecular entity",
    )
    """string identifiers for the molecular entity, e.g., InChI, SMILES, ...

    .. examples::

        - `{"type": "InChI", "value": "InChI=1S/CH4/h1H4"}`
        - `{"type": "custom", "label": "AMChI",
        "value": "AMChI=1/C5H9/c1-3-5-4-2/h3-5H,1-2H3/b5-3+,5-4+"}`

    .. note::

        The "custom" type is used for identifiers that do not fit into the
        standard types. Programs who use the starndard identifiers (InChI,
        SMILES) will read fields with type "InChI" or "SMILES". So, while it is
        possible to supply an InChI via a custom identifier, it is stronlgy
        discouraged.
    """

    # TODO introduce separate Molecular entity definiton? -> e.g. what about crystals, other materials

    # If we explicitly represent the different information layers, we need a
    # more concise form to refer to each entity. InChIKeys with H-layers is
    # one way to get a canonical representation although InChIs cannot
    # distinguish all species relevant in gas-phase kinetics contexts. The
    # representation of each layer does not even need to be canonical, as long
    # as we have a function that produces a canonical representation.
    # TODO better canoncial representation of each layer


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


class _StringIdentifierBase(BaseModel, ABC):
    """Base class for string identifiers with a type field."""

    type: str
    value: str


class _StandardInChI(_StringIdentifierBase):
    """Standard IUPAC International Chemical Identifier"""

    type: Literal["InChI"]

    @field_validator("value", mode="after")
    @classmethod
    def validate_standard_inchi(cls, value: str) -> str:
        """Simple validation of the InChI string. Does not rigourously check
        validity, but at least if it is a standard InChI."""
        if not value.startswith("InChI=1S/"):
            raise ValueError("Not a standard InChI.")

        return value


class _FixedHInChI(_StringIdentifierBase):
    """IUPAC International Chemical Identifier generated with the fixed-H layer."""

    type: Literal["InChI-fixedH"]

    @field_validator("value", mode="after")
    @classmethod
    def validate_non_standard_inchi(cls, value: str) -> str:
        """Simple validation of the InChI string. Does not rigourously check
        validity, but at least if it is a standard InChI."""
        if not value.startswith("InChI=S/"):
            raise ValueError("Standard InChIs not allowed for this field.")

        return value


class _StandardInChIKey(_StringIdentifierBase):
    """Standard IUPAC International Chemical Identifier Key"""

    type: Literal["InChIKey"]
    value: Annotated[
        str,
        Field(
            pattern="^[A-Z]{14}-[A-Z]{8}SA-[A-Z]$",
        ),
    ]


class _SMILES(_StringIdentifierBase):
    """..."""

    type: Literal["SMILES"]


class _CustomStringIdentifier(_StringIdentifierBase):
    """Custom string identifier with a type field."""

    type: Literal["custom"]
    label: str


StringIdentifier: TypeAlias = Annotated[
    _StandardInChI
    | _SMILES
    | _CustomStringIdentifier
    | _FixedHInChI
    | _StandardInChIKey,
    Field(discriminator="type"),
]
"""string identifier for a molecular entity"""
