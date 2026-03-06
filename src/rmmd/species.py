"""part of the schema for identifying species and reactions"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import BaseModel, Field, model_validator
from rdkit.Chem import (
    MolBlockToInchi,
    MolFromInchi,
    MolFromSmiles,
    MolToMolBlock,
    MolToSmiles,
)

from .keys import ConformationIndex, EntityKey, SpeciesName, ThermoIndex, TransportIndex
from .kinetics import RateCoefficient
from .pes import ElectronicState, PesPath


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
    thermo: list[ThermoIndex] = Field(default_factory=list)
    """thermochemical properties for this species"""
    transport: list[TransportIndex] = Field(default_factory=list)
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
    defining_conformations: list[ConformationIndex] | Literal["all"] = "all"
    """While by default, all confomrations with the same stereochemistry and electronic state are considered part of the same molecular entitiy, this field can be used to restrict the set of conformations. In some cases,
    conformations have to belong to separate species to correctly model the kinetics of a system, but they have the same stereochemistry and electronic state. For example, different pre-reactive complexes where the fragements each have the same stereochemistry and electronic state, but different orientations relative to each other. In this case, the different pre-reactive complexes can be defined as different molecular entities with the same constitution, connectivity, stereo, and electronic state, but different defining_conformations.
    """
    conformations: list[ConformationIndex] = Field(default_factory=list)
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
    thermo: list[ThermoIndex] = Field(default_factory=list)
    """thermochemical properties for this reaction"""
    rate_constants: list[RateCoefficient] = Field(default_factory=list)
    """rate coefficients for this reaction"""
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


class _ValidationStrategyMixin(ABC):
    """Base class for string identifiers with a type field."""

    type: str
    value: str
    validation_strategy: Literal["quick", "full", "recalculate"] = "quick"

    @model_validator(mode="after")
    def validate_string_identifier(self) -> Self:
        """Validate string identifier value."""
        if self.validation_strategy == "quick":
            self.quick_validate()
        elif self.validation_strategy == "recalculate":
            self.value = self.recalculate()
        elif self.validation_strategy == "full":
            self.full_validate()
        return self

    def quick_validate(self) -> None:
        """Validate string identifier value (quick)."""
        pass

    @abstractmethod
    def recalculate(self) -> str:
        """Recalculate string identifier value (no validation)."""
        msg = f"Recalculation is not implemented for type {self.type}"
        raise NotImplementedError(msg)

    def full_validate(self) -> None:
        """Validate string identifier value (full)."""
        try:
            recalculated_value = self.recalculate()
        except NotImplementedError:
            msg = f"Full validation is not implemented for type {self.type}"
            raise NotImplementedError(msg)

        if not recalculated_value == self.value:
            msg = (
                f"Recalculated {self.type} does not match:\n"
                f"original:     {self.value}\n"
                f"recalculated: {recalculated_value}\n"
            )
            raise ValueError(msg)


class _StandardInChI(_StringIdentifierBase, _ValidationStrategyMixin):
    """Standard IUPAC International Chemical Identifier"""

    type: Literal["InChI"] = "InChI"

    def quick_validate(self) -> None:
        """Validate string identifier value (quick)."""
        if not self.value.startswith("InChI=1S/"):
            msg = f"{self.type} is missing expected prefix 'InChI=1S/': {self.value}"
            raise ValueError(msg)

    def recalculate(self) -> str:
        """Recalculate string identifier value (no validation)."""
        mol = MolFromInchi(self.value)
        mol_block = MolToMolBlock(mol)
        return MolBlockToInchi(mol_block)  # type: ignore


class _FixedHInChI(_StringIdentifierBase, _ValidationStrategyMixin):
    """IUPAC International Chemical Identifier generated with the fixed-H layer."""

    type: Literal["InChI-fixedH"] = "InChI-fixedH"

    def quick_validate(self) -> None:
        """Validate string identifier value (quick)."""
        if not self.value.startswith("InChI=1/"):
            msg = f"{self.type} is missing expected prefix 'InChI=1/': {self.value}"
            raise ValueError(msg)

    def recalculate(self) -> str:
        """Recalculate string identifier value (no validation)."""
        mol = MolFromInchi(self.value)
        mol_block = MolToMolBlock(mol)
        return MolBlockToInchi(mol_block, options="-FixedH")  # type: ignore


class _StandardInChIKey(_StringIdentifierBase):
    """Standard IUPAC International Chemical Identifier Key"""

    type: Literal["InChIKey"]
    value: Annotated[
        str,
        Field(
            pattern="^[A-Z]{14}-[A-Z]{8}SA-[A-Z]$",
        ),
    ]


class _SMILES(_StringIdentifierBase, _ValidationStrategyMixin):
    """Simplified Molecular Input Line Entry System"""

    type: Literal["SMILES"] = "SMILES"

    def recalculate(self) -> str:
        """Recalculate string identifier value (no validation)."""
        mol = MolFromSmiles(self.value)
        return MolToSmiles(mol)


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


class _StringIdentifierTest(BaseModel):
    """class for testing the Geometry and Geometries classes"""

    string_identifier_list: list[StringIdentifier]
