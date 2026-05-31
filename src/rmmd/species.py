"""part of the schema for identifying species and reactions"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Annotated, Any, Literal, Self

from pydantic import (
    Field,
    NonNegativeInt,
    PositiveInt,
    ValidationError,
    field_validator,
    model_validator,
)

from ._base import RmmdBaseModel, RmmdFrozenBaseModel
from .identifiers import StringIdentifier, FixedHInChI
from .keys import ConformationIndex, EntityKey, SpeciesName, ThermoIndex, TransportIndex
from .kinetics import RateCoefficient
from .pes import PesPath


class Species(RmmdBaseModel):
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


class MolecularEntity(RmmdBaseModel):
    """A distinct molecule, ion, radical, complex, ... with a specific rigid stereochemistry and electronic state.

    Here, flexible conformational spatial rearrangements are by default not distinguished, i.e., a molecular entity can have multiple conformers.
    """

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
    )
    """string identifiers for the molecular entity, e.g., InChI, SMILES, ...

    At least "InChI-fixedH" has to be provided.

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

    @field_validator("identifiers")
    def _check_required_inchi_fixedh(
        cls, identifiers: list[StringIdentifier]
    ) -> list[StringIdentifier]:
        """check that at a fixedH InChI is available"""

        identifiers_dict = {identifier.type: identifier for identifier in identifiers}

        if "InChI-fixedH" in identifiers_dict:
            return identifiers

        # try to generate a fixed-H InChI from the InChI
        elif "InChI-fixedH" not in identifiers_dict and "InChI" in identifiers_dict:
            fixedh_inchi = identifiers_dict["InChI"].value.replace(
                "InChI=1S/", "InChI=1/"
            )
            try:
                fixedh_inchi = FixedHInChI(
                    value=fixedh_inchi,
                    # recalculates the fixedH inChI from the InChI and checks if
                    # they are equal
                    validation_strategy="full",
                )
                identifiers.append(fixedh_inchi)
                return identifiers

            except ValidationError as err:
                raise ValueError(
                    "The provided InChI does not match the generated fixedH InChI."
                    + " If a molecular entity contains tautomeric hydrogens, the "
                    + "fixedH InChI must be provided explicitly."
                ) from err

        # required fixedH InChI is missing and cannot be generated
        else:
            raise ValueError("A fixedH InChI must be provided.")

    # some helpers
    @property
    def constitution(self) -> Constitution:
        """element count, e.g. {'C': 1, 'H': 4}"""

        inchi_fixedh = next(
            (
                identifier.value
                for identifier in self.identifiers
                if identifier.type == "InChI-fixedH"
            ),
            None,
        )

        return _consitution_from_inchi(inchi_fixedh)

    @property
    def charge(self) -> int:
        """total charge of the molecule"""

        inchi_fixedh = next(
            (
                identifier.value
                for identifier in self.identifiers
                if identifier.type == "InChI-fixedH"
            ),
            "",
        )

        return _get_charge_from_inchi(inchi_fixedh)


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


class SpeciesRole(RmmdBaseModel):
    """Node in a reaction network"""

    # can be extended, if necessary, subclasses for some roles can
    # add additional fields
    role: Literal["reactant", "product", "solvent", "catalyst"]
    species: SpeciesName


class Reaction(RmmdBaseModel):
    """A chemical reaction"""

    species: list[SpeciesRole]
    thermo: list[ThermoIndex] = Field(default_factory=list)
    """thermochemical properties for this reaction"""
    rate_constants: list[RateCoefficient] = Field(default_factory=list)
    """rate coefficients for this reaction"""
    pes_paths: list[PesPath] = Field(default_factory=list)


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
    # multiplicity | n_unpaired | is_ground_state | hunds_rule_in_ground_state
    # int          | int        | True            | True
    # int          | int        | True            | False
    # int          | int        | False           | True
    # int          | int        | False           | False
    # int          | int        | "unkown"        | True
    # int          | int        | "unkown"        | False
    # int          | None       | True            | True
    # int          | None       | True            | False
    # int          | None       | False           | True
    # int          | None       | False           | False
    # int          | None       | "unkown"        | True
    # int          | None       | "unkown"        | False
    # None         | int        | True            | True
    # None         | int        | True            | False
    # None         | int        | False           | True
    # None         | int        | False           | False
    # None         | int        | "unkown"        | True
    # None         | int        | "unkown"        | False
    # None         | None       | True            | True
    # None         | None       | True            | False
    # None         | None       | False           | True
    # None         | None       | False           | False
    # None         | None       | "unkown"        | True
    # None         | None       | "unkown"        | False

    # TODO remove impossible states after validation -> move those to test cases that fail validation
    # TODO decide on equality behavior for each combination of possible cases -> make test cases for that

    type: Literal["electronic-spin"] = "electronic-spin"

    # use 2S+1 (multiplcity) instead of S (spin quantum number), because multiplicity is always an integer which is easier to handle than half-integer S
    multiplicity: PositiveInt | None = None
    n_unpaired: NonNegativeInt | None = None

    is_ground_state: bool | Literal["unkown"] = "unkown"
    """whether this is the ground state or an excited state

    This field allows determining if two electronic states from different datasets are equal, even if one of them has an unkonw spin quantum number.
    """

    hunds_rule_in_ground_state: bool = True
    """whether the electronic state follows Hund's rule of maximum multiplicity.

    Allows dealing with absolute edge cases where Hund's rule does not apply
    (e.g., https://doi.org/10.1002/anie.200352990) and can usually be left at the
    default value (True).
    """

    @field_validator("is_ground_state")
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
        return self.is_ground_state is True and self.hunds_rule_in_ground_state is True

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
        if not self.hunds_rule_in_ground_state or self.is_ground_state is not True:
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
                    f"Multiplicity {self.multiplicity} does not match n_unpaired {self.n_unpaired} according to Hund's rule."
                )
        return self
