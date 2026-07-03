"""part of the schema for identifying species and reactions"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Annotated, Any, Literal, Self, TypeAlias

from annotated_types import Gt, Le, MinLen
from pydantic import (
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    model_validator,
)

from ._base import RmmdBaseModel, RmmdFrozenBaseModel
from .identifiers import FixedHInChI
from .keys import (
    ConformationIndex,
    EntityKey,
    ReactionIndex,
    SpeciesName,
    ThermoIndex,
    TransportIndex,
)
from .kinetics import RateCoefficient

UNKOWN_GROUND_STATE = "unkown-electronic-ground-state"


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

    A molecular entity is defined by its constitution, connectivity, stereochemistry and electronic state. The former three are defined via a InChI-fixedH.
    Here, flexible conformational spatial rearrangements are by default not distinguished, i.e., a molecular entity can have multiple conformers.
    """

    defining_conformations: list[ConformationIndex] | Literal["all"] = "all"
    """While by default, all confomrations with the same stereochemistry and electronic state are considered part of the same molecular entitiy, this field can be used to restrict the set of conformations. In some cases,
    conformations have to belong to separate species to correctly model the kinetics of a system, but they have the same stereochemistry and electronic state. For example, different pre-reactive complexes where the fragements each have the same stereochemistry and electronic state, but different orientations relative to each other. In this case, the different pre-reactive complexes can be defined as different molecular entities with the same constitution, connectivity, stereo, and electronic state, but different defining_conformations.
    """

    inchi_fixedh: FixedHInChI
    """value of the identifier (InChI-fixedH) that defines the connectivity, charge and
    stereochemistry of the molecular entity."""

    conformations: list[ConformationIndex] = Field(default_factory=list)
    """list of conformations that have been identified for this molecular entity.

    Expecially, if `defining_conformations` is "all" and the molecular
    strucutre is flexible, this list is not guaranteed to be exhaustive as not
    all conformations may have been identified.
    """
    description: str | None = None
    """human-readable description of what this molecular entity represents"""

    description: str | None = None
    """human-readable description of what this molecular entity represents"""

    electronic_spin: _KnownElectronicSpin | Literal["unkown-electronic-ground-state"]
    """total electronic angular momentum of the molecule

    While the electronic state of a molecule is ideally always defined by an
    "electronic-spin" identifier, some user groups of RMMD that mainly work on the
    mechanism level may not be familiar with the concept of spin. To facilitate the use
    of RMMD for these users as well as the conversion of existing datasets that do not
    contain multiplicity information, we allow the electronic state to be partially
    undefined, that is, only declared as being the ground state without specifying the
    multiplicity.
    """

    # some helpers
    @property
    def constitution(self) -> Constitution:
        """element count, e.g. {'C': 1, 'H': 4}"""
        return _consitution_from_inchi(self.inchi_fixedh.value)

    @property
    def charge(self) -> int:
        """total charge of the molecule"""
        return _get_charge_from_inchi(self.inchi_fixedh.value)


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

    type: Literal["elementary", "stepwise", "unkown"] = "unkown"
    """type of the reaction"""

    description: str | None = None
    """human-readable description of the reaction"""

    reactants: Annotated[list[SpeciesName], MinLen(1)]
    products: Annotated[list[SpeciesName], MinLen(1)]
    solvent: SpeciesName | Mixture | None = None
    catalyst: SpeciesName | None = None

    steps: list[ReactionIndex] = Field(default_factory=list)
    """consecutive reaction steps

    Allows modelling step-wise reactions by defining their elementary steps as separate
    reactions and linking them via this field. Since an elementary reaction is also a
    reaction, this list contains references to other reactions.

    .. note::

        While RMMD allows composing reactions from multiple steps which can also be composed of steps, this is discouraged. Researchers are encouraged to validate that the reactions they list as `steps` of a step-wise reaction are indeed elementary reactions.
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

    @model_validator(mode="after")
    def _elementary_reaction_check(self) -> Reaction:
        """Check consistency between existence of steps and type."""

        if (self.steps or self.parallel_steps) and self.type == "elementary":
            raise ValueError(
                "Elementary reactions cannot have steps. If this reaction is indeed "
                "elementary, remove the steps. If it is not elementary, set type to "
                "'stepwise'."
            )

        elif (self.steps or self.parallel_steps) and self.type == "unkown":
            logging.getLogger(__name__).debug(
                "Reaction defines steps, but type is 'unkown'. Setting type to 'stepwise'."
            )
            self.type = "stepwise"
        return self


########################################################################################
# helpers for molecular entity
########################################################################################


# assumptions for fixedH inchi parsing
# - -fixedH flag was used
# - no reconnected layer
# - stereochemistry information is complete


def _get_charge_from_inchi(inchi: str) -> int:
    """extract charge from InChI main layer

    :param inchi: InChI string (asumed valid)"""
    charge = 0

    for part in inchi.split("/"):
        if part.startswith("p") or part.startswith("q"):
            fragment_charges = part[1:].split(";")

            for fragment_charge in fragment_charges:
                if fragment_charge != "":
                    charge += int(fragment_charge)

        # the remaining layers should not change the total charge, so we only
        # check the /p and /q sublayers of the main layer
        if part[0] in {"b", "t", "m", "s", "i", "f"}:
            break

    return charge


def _consitution_from_inchi(inchi_or_other: str | Any) -> dict[str, int]:
    """extract constitution from InChI string

    :param inchi_or_other: InChI string (asumed valid) or already parsed constitution (in this case, the input is returned as is)
    """

    if not isinstance(inchi_or_other, str):
        return inchi_or_other

    layers = inchi_or_other.split("/")

    main_layer = layers[1]
    p_layer = None

    for layer in layers[2:]:
        if layer.startswith("p"):
            p_layer = layer
            break

    constitution = defaultdict(int)

    # Parse main layer for elements and counts
    pattern = r"([A-Z][a-z]?)(\d*)"
    matches = re.findall(pattern, main_layer)

    for element, count_str in matches:
        count = int(count_str) if count_str else 1
        constitution[element] += count

    # Parse p layer if present (protonation layer)
    if p_layer:
        # p+3 -> 3 additional protons, p-1 -> 1 less proton

        sign = p_layer[1]
        count_str = int(p_layer[2:])

        if sign == "+":
            constitution["H"] += count_str
        elif sign == "-":
            constitution["H"] -= count_str
        else:
            raise ValueError(f"Invalid p layer in InChI: {p_layer}")

    return constitution


# TODO use "Composition" instead of "Constitution"?
Constitution = Annotated[
    dict[str, int],
    Field(
        examples=[{"C": 1, "H": 4}],
    ),
]
""""element count, e.g. {'C': 1, 'H': 4}"""


class _KnownElectronicSpin(RmmdFrozenBaseModel, frozen=True):
    """Identifier for the electronic spin state of a molecular entity."""

    # possible states (after validation)
    # multiplicity | n_unpaired | is_ground_state | hunds_rule_in_ground_state
    # int          | int        | True            | True
    # int          | int        | True            | False
    # int          | int        | False           | True
    # int          | int        | False           | False
    # int          | int        | "unkown"        | True
    # int          | int        | "unkown"        | False

    # TODO remove impossible states after validation -> move those to test cases that fail validation

    type: Literal["electronic-spin"] = "electronic-spin"

    # use 2S+1 (multiplcity) instead of S (spin quantum number), because multiplicity is always an integer which is easier to handle than half-integer S
    multiplicity: PositiveInt | None = None
    n_unpaired: NonNegativeInt | None = None

    # do not use bool | Literal["unknown"] because Python's implicit bool conversion
    # could lead to unexpected behavior of if statements problems when set to "unkown"
    state: Literal["ground-state", "excited", "unkown"] = "unkown"
    """whether this is the ground state or an excited state

    This field allows determining if two electronic states from different datasets are equal, even if one of them has an unkonw spin quantum number.
    """

    hunds_rule_in_ground_state: bool = True
    """whether the electronic state follows Hund's rule of maximum multiplicity.

    Allows dealing with absolute edge cases where Hund's rule does not apply
    (e.g., https://doi.org/10.1002/anie.200352990) and can usually be left at the
    default value (True).
    """

    @field_validator("state")
    def _warn_on_unkown_ground_state(
        cls, value: bool | Literal["unkown"]
    ) -> bool | Literal["unkown"]:
        if value == "unkown":
            logging.getLogger(__name__).warning(
                "Unkown ground state for molecular entity. If the electronic state is"
                + " known to be the ground state, setting `is_ground_state` to `True`"
                + " is highly recommended as it allows comparing electronic states"
                + " across datasets with unkown electronic ground states."
            )
        return value

    @property
    def _is_hunds_rule_applicable(self) -> bool:
        """whether Hund's rule of maximum multiplicity is applicable for this state"""
        return self.state == "ground-state" and self.hunds_rule_in_ground_state is True

    @model_validator(mode="after")
    def _check_spin_fields(self) -> Self:
        if (
            self.multiplicity is None or self.n_unpaired is None
        ) and not self._is_hunds_rule_applicable:
            raise ValueError(
                "'multiplicity' and 'n_unpaired' must be set, if not in ground state."
            )
        return self

    @model_validator(mode="after")
    def _apply_hunds_rule(self) -> Self:
        if not self._is_hunds_rule_applicable:
            # Hund's rule will not be applied
            return self

        if self.n_unpaired is not None and self.multiplicity is None:
            # since instance is frozen, we have to use object.__setattr__
            object.__setattr__(self, "multiplicity", self.n_unpaired + 1)
        elif self.multiplicity is not None and self.n_unpaired is None:
            object.__setattr__(self, "n_unpaired", self.multiplicity - 1)

        elif self.multiplicity is not None and self.n_unpaired is not None:
            if self.multiplicity != self.n_unpaired + 1:
                raise ValueError(
                    f"Multiplicity {self.multiplicity} does not match n_unpaired {self.n_unpaired} according to Hund's rule of maximum multiplicity."
                )
        return self
