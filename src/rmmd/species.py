"""part of the schema for identifying species and reactions"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from annotated_types import Gt, Le, MinLen
from pydantic import Field

from ._base import RmmdBaseModel
from .identifiers import StringIdentifier
from .keys import (
    ConformationIndex,
    EntityKey,
    ReactionIndex,
    SpeciesName,
    ThermoIndex,
    TransportIndex,
)
from .kinetics import RateCoefficient
from .pes import ElectronicState


class Species(RmmdBaseModel):
    """A chemical species."""

    names: list[str] = Field(default_factory=list)
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


class MolecularEntity(RmmdBaseModel):
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
    description: str | None = None
    """human-readable description of what this molecular entity represents"""

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


class TransportProperty(RmmdBaseModel):
    """Transport property for species"""

    shape: Literal["atom", "linear", "nonlinear"]
    """whether the molecule is point-like ("atom"), linear, or non-linear."""
    dipole_moment: float | None = None
    """dipole moment in Debye"""
    polarizability: float | None = None
    """polarizability in cubic angstroms"""
    quadrupole_polarizability: float = 0.0
    """quadrupole polarizability in angstrom^5"""
    lj_sigma: float
    """Lennard-Jones collision diameter in angstroms"""
    lj_eps_over_kb: float
    """Lennard-Jones well-depth (epsilon) divided by Boltzmann constant in K for
    transport property calculations
    """
    rotational_relaxation: float = 0.0
    """rotational relaxation collision number"""
    acentric_factor: float = 0.0
    """Pitzer's acentric factor"""
    dispersion_coefficient: float = 0.0
    """dispersion coefficient normalized by e^2 in angstroms^5"""


Mixture: TypeAlias = list[tuple[SpeciesName, Annotated[float, Gt(0.0), Le(1.0)]]]
"""a mixture of species with their respective mole fractions."""


class Reaction(RmmdBaseModel):
    """A chemical reaction.

    High-level description/identification of a reaction (with a direction).
    """

    description: str | None = None
    """human-readable description of the reaction"""

    reactants: Annotated[list[SpeciesName], MinLen(1)]
    products: Annotated[list[SpeciesName], MinLen(1)]
    solvent: SpeciesName | Mixture | None = None
    catalyst: SpeciesName | None = None

    transition_state: SpeciesName | None = None
    """for an elementary reaction, the transition state can be provided.
    """
    steps: list[ReactionIndex] = Field(default_factory=list)
    """consecutive reaction steps

    allows modelling step-wise reactions by defining their elementary steps as separate
    reactions and linking them vis this field.
    """
    parallel_steps: list[ReactionIndex] = Field(default_factory=list)
    """parallel reaction steps

    allows "lumping" of multiple parallel reactions with the same reactants and products
    """

    thermo: list[ThermoIndex] = Field(default_factory=list)
    """thermochemical properties for this reaction"""
    rate_constants: list[RateCoefficient] = Field(default_factory=list)
    """rate coefficients for this reaction"""

    def __str__(self) -> str:
        """String representation of the reaction."""
        reactants_str = " + ".join(self.reactants)
        products_str = " + ".join(self.products)
        return f"{reactants_str} -> {products_str}"

    def reverse(self) -> Reaction:
        """Return the reverse reaction.

        The reverse reaction does not include thermo, rate constants and steps."""
        return Reaction(
            reactants=self.products,
            products=self.reactants,
            solvent=self.solvent,
            catalyst=self.catalyst,
        )


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
class MolecularConnectivity(RmmdBaseModel):
    """Connectivity between atoms"""

    # TODO graph data structure + canonical form for easy comparison
    # TODO special values for formed and broken bonds (for transition states, etc.)


class Stereochemistry(RmmdBaseModel):
    """Definition of the Stereochemistry"""

    # TODO define via stereocenters
