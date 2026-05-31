"""part of the schema for identifying species and reactions"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Annotated, Any, Literal, Self

from pydantic import (
    Field,
    ModelWrapValidatorHandler,
    ValidationError,
    computed_field,
    model_validator,
)

from ._base import RmmdBaseModel
from .identifiers import StringIdentifier, _FixedHInChI
from .keys import ConformationIndex, EntityKey, SpeciesName, ThermoIndex, TransportIndex
from .kinetics import RateCoefficient
from .pes import ElectronicState, PesPath


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

    # TODO canonical representation of each field; this is similar to the layers of an InChI
    constitution: Constitution
    connectivity: MolecularConnectivity
    isotopes: (
        IsotopeInformation | Literal["natural-abundance"] | Literal["most-common"]
    ) = "natural-abundance"
    """number of neutrons for each atom"""
    stereo: Stereochemistry | Literal["unknown"]
    electronic_state: ElectronicState
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

    @computed_field
    @property
    def has_canonical_repr(self) -> bool:
        """whether the molecular entity can be canonically represented.

        If false, the molecular entity cannot be considered equal to another molecular
        entity, even if all fields are the same.

        True, if the electronic state is fully defined and the molecular entity is not
        defined as a subset of all conformations with the same connectivity,
        stereochemistry, etc.
        """

        return (
            self.stereo != "unknown"
            and self.electronic_state.spin != "unknown"
            and self.defining_conformations == "all"
        )

    @model_validator(mode="wrap")
    @classmethod
    def _create_from_fixed_h_inchi(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self]
    ):
        """If the molecular entity is not fully defined, but a fixed-H InChI is given,
        the molecular entity will be created from that InChI.
        """
        try:
            return handler(data)  # try to create the entity from the given data

        except ValidationError as mol_entity_val_err:
            fixed_h_inchi = None  # noqa: F841

            # if only a fixed-H InChI is present, the molecular entity can be created
            # from the InChI
            if isinstance(data, dict) and "identifiers" in data:
                for identifier in data["identifiers"]:
                    if (
                        isinstance(identifier, dict)
                        and identifier.get("type", None) == "InChI-fixedH"
                    ):
                        try:
                            fixed_h_inchi = _FixedHInChI(**identifier)
                        except ValidationError:
                            raise mol_entity_val_err

                        break

            if fixed_h_inchi is None:
                raise mol_entity_val_err

            if "/r" in fixed_h_inchi.value:
                msg = (
                    "Generation of MolEntities from InChI-fixedH with reconnecred "
                    + "layer'/r' is currently not supported"
                )
                raise NotImplementedError(msg)

            isotope_info = IsotopeInformation.from_fixed_h_inchi(fixed_h_inchi.value)
            if isotope_info.mi == "" and isotope_info.fi == "":
                isotope_info = "natural-abundance"

            # TODO do not override existing fields in the dict, but check if they are
            #      consistent with the InChI and raise an error if not

            return cls(
                constitution=_consitution_from_inchi(fixed_h_inchi.value),
                connectivity=MolecularConnectivity.from_fixed_h_inchi(
                    fixed_h_inchi.value
                ),
                stereo=Stereochemistry.from_fixed_h_inchi(fixed_h_inchi.value),
                isotopes=isotope_info,
                electronic_state=ElectronicState(
                    spin="unknown", charge=_get_charge_from_inchi(fixed_h_inchi.value)
                ),
            )

    # TODO add other strategies to create a molecular entity (e.g. from a QM optimization output)

    # TODO introduce separate Molecular entity definiton? -> e.g. what about crystals, other materials
    # TODO TS mol entitiy -> stereochemistries & connectivities of the two wells + TS connectivity
    #

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


class MolecularConnectivity(RmmdBaseModel):
    """Connectivity between atoms"""

    m: tuple[
        Annotated[str, Field(pattern=r"^(\/c.*|)$")],
        Annotated[str, Field(pattern=r"^(\/h.*|)$")],
        Annotated[str, Field(pattern=r"^(\/p.*|)$")],  # empty string allowed
    ]
    """main layer /c, /h and /p sublayer of Inchi"""
    f: tuple[
        Annotated[str, Field(pattern=r"^(\/f.*|)$")],
        Annotated[str, Field(pattern=r"^(\/h.*|)$")],
        Annotated[str, Field(pattern=r"^(\/o.*|)$")],
    ]
    """/f, /h /o sublayers of fixed H layer"""

    @classmethod
    def from_fixed_h_inchi(cls, fixed_h_inchi: str) -> MolecularConnectivity:
        """create MolecularConnectivity from a fixed-H InChI string

        :param fixed_h_inchi: fixed-H InChI string (asumed valid)"""

        layers = ["/" + part for part in fixed_h_inchi.split("/")]

        # main layer
        m_c = m_h = m_p = f_f = f_h = f_o = ""
        inside_f_layer = False
        for layer in layers:
            if layer.startswith("/c"):
                m_c = layer

            # /h can occur in multiple layers
            elif layer.startswith("/h") and not inside_f_layer:
                m_h = layer

            elif layer.startswith("/p"):
                m_p = layer

            elif layer.startswith("/f"):
                inside_f_layer = True
                f_f = layer

            elif layer.startswith("/h") and inside_f_layer:
                f_h = layer

            elif layer.startswith("/o"):
                f_o = layer

        return cls(m=(m_c, m_h, m_p), f=(f_f, f_h, f_o))

    # TODO special values for formed and broken bonds (for transition states, etc.)


class Stereochemistry(RmmdBaseModel):
    """Definition of the Stereochemistry.

    .. note::

        empty stereochemistry layer do not mean unknown stereochemistry, but no
        stereochemical information is necessary.
    """

    m: Annotated[str, Field(pattern=r"^(\/b.*)?(\/t.*)?(\/m.*)?(\/s.*)?$")]
    """/b, /t, /m and /s sublayers of Inchi main layer"""
    f: Annotated[str, Field(pattern=r"^(\/b.*)?(\/t.*)?(\/m.*)?(\/s.*)?$")]
    """/b, /t, /m and /s sublayers of Inchi fixed-H layer"""
    fi: Annotated[str, Field(pattern=r"^(\/b.*)?(\/t.*)?(\/m.*)?(\/s.*)?$")]
    """/b, /t, /m and /s sublayers of Inchi fixed-H layer with isotopic information"""
    o: Annotated[str, Field(pattern=r"^(\/o.*)?$")]
    """/o sublayer of Inchi fixed-H layer with fixedH layer

    separate because it can be at the end of the F or the FI layer
    """

    @classmethod
    def from_fixed_h_inchi(cls, fixed_h_inchi: str) -> Stereochemistry:
        """create Stereochemistry from a fixed-H InChI string

        :param fixed_h_inchi: fixed-H InChI string (asumed valid)"""

        layers = ["/" + part for part in fixed_h_inchi.split("/")]

        m = f = fi = o = ""
        inside_f_layer = False
        inside_fi_layer = False
        for layer in layers:
            if (
                layer.startswith("/b")
                or layer.startswith("/t")
                or layer.startswith("/m")
                or layer.startswith("/s")
                and not inside_f_layer
                and not inside_fi_layer
            ):
                m = m + layer

            if layer.startswith("/f"):
                inside_f_layer = True

            elif (
                layer.startswith("/b")
                or layer.startswith("/t")
                or layer.startswith("/m")
                or layer.startswith("/s")
                and inside_f_layer
                and not inside_fi_layer
            ):
                f = f + layer

            if layer.startswith("/i"):
                inside_fi_layer = True
                inside_f_layer = False

            elif (
                layer.startswith("/b")
                or layer.startswith("/t")
                or layer.startswith("/m")
                or layer.startswith("/s")
                and inside_fi_layer
            ):
                fi = fi + layer

            elif layer.startswith("/o"):
                o = layer

        return cls(m=m, f=f, fi=fi, o=o)


class IsotopeInformation(RmmdBaseModel):
    """Isotopic information for a molecular entity"""

    mi: Annotated[str, Field(pattern=r"^(\/i.*)?$")]
    """MI sublayer"""
    fi: Annotated[str, Field(pattern=r"^(\/i.*)?$")]
    """FI sublayer"""

    @classmethod
    def from_fixed_h_inchi(cls, fixed_h_inchi: str) -> IsotopeInformation:
        """create IsotopeInformation from a fixed-H InChI string

        :param fixed_h_inchi: fixed-H InChI string (asumed valid)"""

        layers = ["/" + part for part in fixed_h_inchi.split("/")]

        mi = fi = ""

        inside_mi_layer = False
        inside_f_layer = False
        inside_fi_layer = False
        for layer in layers:
            if layer.startswith("/i"):
                if inside_f_layer:
                    inside_fi_layer = True
                else:
                    inside_mi_layer = True

            if layer.startswith("/f"):
                inside_mi_layer = False  # main /i layer ended by /f layer
                inside_f_layer = True

            if inside_mi_layer:
                mi += layer

            if inside_fi_layer:
                fi += layer

        return cls(mi=mi, fi=fi)
