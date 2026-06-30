"""Defining the Reaction Model Electronic Structure Schema

See this link for a few examples of what you can do:
https://docs.pydantic.dev/latest/concepts/json_schema/#generating-json-schema
"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from annotated_types import MinLen
from pydantic import (
    AfterValidator,
    Discriminator,
    Field,
    NonNegativeInt,
    Tag,
    model_validator,
)

from ._base import RmmdBaseModel, RmmdFrozenBaseModel
from .calc import CalculationBase, OutputOf
from .elements import ElementSymbol
from .identifiers import StringIdentifier
from .keys import CalcIndex, ConformationIndex
from .registry import HasKeyMixin


class ElectronicState(RmmdFrozenBaseModel, frozen=True):
    """Definition of the electronic state"""

    charge: int
    """total charge"""
    multiplicity: NonNegativeInt
    """2S+1 - two times the electron spin quantum number + 1"""

    description: str | None = None
    """human-readable description of the electronic state, e.g. "ground state"

    This field is required, if spin is unknown. This field can also be used to
    add additional information about the electronic state, e.g., the term
    symbol
    """


LevelOfTheory = Annotated[
    str,
    Field(  # in v1.0 just a string
        description="Level of theory used for the quantum chemistry calculation.",
        examples=["B3LYP-G-D3BJ/6-31G(d)", "DLPNO-CCSD(T)/cc-pVnZ-CBS", "GFN2-xTB"],
        pattern=r"^\S+[\/\S+]?$",
    ),
]

###############################################################################
# Quantum chemistry calculations & their metadata
###############################################################################


class Geometry(RmmdBaseModel):
    """molecular structure/geometry"""

    atoms: list[ElementSymbol]
    """list of atoms in the molecule, in the same order as the coordinates"""
    coordinates: list[list[float]]
    """list of coordinates of the atoms in the molecule, in the same order as
    the atoms [Ångström]"""

    @model_validator(mode="after")
    def check_n_atoms(self):
        """check that the number of atoms matches the number of coordinates"""
        if len(self.atoms) != len(self.coordinates):
            raise ValueError("Number of atoms and coordinates must match")
        return self

    @model_validator(mode="after")
    def check_geometry_dimensions(self):
        """check that all atoms have 3 cartesian coordinates"""
        for coord in self.coordinates:
            if len(coord) != 3:
                raise ValueError("Each atom must have 3 cartesian coordinates")
        return self


class Geometries(RmmdBaseModel):
    """list of geometries with the same order of atoms"""

    atoms: list[ElementSymbol]
    """list of atoms in the molecule, in the same order as the coordinates"""
    coordinates: list[list[list[float]]]
    """list of coordinates of the atoms in the molecule, in the same order as
    the atoms [Ångström]"""

    @model_validator(mode="after")
    def check_n_atoms(self):
        """check that the number of atoms matches the number of coordinates"""
        for coords in self.coordinates:
            if len(self.atoms) != len(coords):
                raise ValueError("Number of atoms and coordinates must match")
        return self

    @model_validator(mode="after")
    def check_geometry_dimensions(self):
        """check that all atoms have 3 cartesian coordinates"""
        for coords in self.coordinates:
            for coord in coords:
                if len(coord) != 3:
                    raise ValueError("Each atom must have 3 cartesian coordinates")
        return self


_DistanceDef: TypeAlias = tuple[NonNegativeInt, NonNegativeInt]
"""definition of a distance internal coordinate, i.e., a bond length, by the indices of
the two atoms involved
"""
_AngleDef: TypeAlias = tuple[NonNegativeInt, NonNegativeInt, NonNegativeInt]
"""definition of an angle internal coordinate, i.e., a bond angle, by the indices of
the three atoms involved
"""
_DihedralDef: TypeAlias = tuple[
    NonNegativeInt, NonNegativeInt, NonNegativeInt, NonNegativeInt
]
"""definition of a dihedral angle internal coordinate by the indices of the four atoms
involved
"""


class _QmInput(RmmdBaseModel):
    """input data for a quantum chemistry calculation"""

    level_of_theory: LevelOfTheory
    """level of theory used"""
    electronic_state: ElectronicState
    """electronic state for which the calculation was performed"""
    geometry: Geometry | None = None
    """geometry of the molecule for which the calculation was performed"""


class _QmOptInput(_QmInput):
    """input data for a geometry optimization calculation"""

    constraints: list[_DistanceDef | _AngleDef | _DihedralDef] = Field(
        default_factory=list
    )
    """constraints on the internal coordinates during the optimization"""

    initial_geometry: Geometry | OutputOf | None = None
    """initial geometry for the optimization."""


class _QmOptData(RmmdBaseModel):
    """Data from a geometry optimization calculation"""

    geometry: Geometry
    """geometry of the optimized structure"""
    total_electronic_energy: float
    """total electronic energy in Hartree"""
    gradient: list[tuple[float, float, float]] | None = None
    """gradient of the energy w.r.t. the coordinates [Hartree/Å]"""


class QmOptimization(CalculationBase[_QmOptInput, _QmOptData]):
    """geometry optimization"""

    type: Literal["qm-optimization", "qm-ts"] = "qm-optimization"
    """type of the calculation"""


class _QmScanInput(_QmInput):
    """input data for a PES scan"""

    scan_coordinates: list[_DistanceDef | _AngleDef | _DihedralDef]
    """definition of the internal coordinates that are scanned"""
    scan_type: Literal["frozen", "relaxed"]
    """whether all other atoms (except those involved in the scan coordinates and the
    constraints) are optimized at each step of the scan ("relaxed") or not ("frozen")
    """
    constraints: list[_DistanceDef | _AngleDef | _DihedralDef] = Field(
        default_factory=list
    )
    """constraints on the internal coordinates during a relaxed scan"""


class _QmScanData(RmmdBaseModel):
    """data from a dihedral angle scan"""

    geometries: Geometries
    """geometries of the scan"""
    total_electronic_energies: list[float]
    """total electronic energy in Hartree"""

    # TODO add steps, boundary, etc.


class QmScan(CalculationBase[_QmScanInput, _QmScanData]):
    """dihedral angle scan"""

    type: Literal["qm-scan"] = "qm-scan"
    """type of the calculation"""


class _QmFreqData(RmmdBaseModel):
    """Data from a frequency calculation"""

    frequencies: list[float]
    """frequencies in cm^-1"""
    total_electronic_energy: float
    """total electronic energy in Hartree"""
    rot_symmetry_nr: int | None = None
    """rotational symmetry number"""
    # TODO: use Å or Bohr radii?
    hessian: list[list[float]] | None = None
    """Hessian matrix in atomic units, i.e. second derivatives of the energy
    w.r.t. the coordinates [Hartree/Å]"""


class QmFreqCalc(CalculationBase[_QmInput, _QmFreqData]):
    """frequency calculation"""

    type: Literal["qm-frequency"] = "qm-frequency"


class _QmOptFreqData(_QmOptData, _QmFreqData):
    """Data from a geometry optimization calculation with frequencies"""


class QmOptFreqCalc(CalculationBase[_QmInput, _QmOptFreqData]):
    """geometry optimization with frequencies"""

    type: Literal["qm-optimization+frequency", "qm-ts+frequency"] = (
        "qm-optimization+frequency"
    )


class _QmEnergyData(RmmdBaseModel):
    """Data from a single-point energy calculation"""

    total_electronic_energy: float
    """total electronic energy in Hartree"""


class QmEnergyCalc(CalculationBase[_QmInput, _QmEnergyData]):
    """single-point energy calculation"""

    type: Literal["qm-energy"] = "qm-energy"


class QmIrcScanInput(_QmInput):
    """input data for an intrinsic reaction coordinate scan"""

    scan_type: Literal["forward", "reverse", "both"]
    """direction of the scan, i.e., whether the scan was performed in the forward
    direction (from the transition state to the reactants), reverse direction (from the
    transition state to the products), or both directions. It is a bit arbitrary and the
    names are different between different quantum chemistry software packages, but the
    main purpose of this field is to distinguish different scans.
    """
    ts: OutputOf | None = None
    """reference to the transition state optimization"""


class _QmIrcScanData(RmmdBaseModel):
    """Data from an intrinsic reaction coordinate scan in a single direction"""

    points: Geometries
    """geometries along the IRC path (inlcuding the transition state)"""
    total_electronic_energies: list[float]
    """list of total electronic energies in Hartree for each point in the IRC path"""

    @model_validator(mode="after")
    def check_n_points(self):
        """check that the number of points matches the number of energies"""
        if len(self.points.coordinates) != len(self.total_electronic_energies):
            raise ValueError("Number of points and energies must match")
        return self


class QmIrcScan(CalculationBase[QmIrcScanInput, _QmIrcScanData]):
    """intrinsic reaction coordinate scan"""

    type: Literal["qm-irc"] = "qm-irc"


QmCalculation = Annotated[
    QmOptimization | QmScan | QmFreqCalc | QmOptFreqCalc | QmEnergyCalc | QmIrcScan,
    Field(discriminator="type"),
]
"""There are two ways to supply quantum chemistry data, either directly by
providing the geometries, frequencies, ..., or as a reference to a public
dataset hosted elsewhere. This allows RMMD to focus on data relevant to gas
kinetics and mechanism modeling, while users can still publish the full quantum
chemistry data "FAIRly" on a specialized platforms with a more detailed
computational chemistry schema. Including such a schema in RMMD would
unnecessarily complicate the RMMD schema. When supplying the data directly,
one may still reference a public dataset, but this is not required.
"""


###############################################################################
# physical meaning of calculations
###############################################################################


class Conformation(HasKeyMixin):
    """ "The spatial arrangement of the atoms affording distinction between
    stereoisomers which can be interconverted by rotations about formally
    single bonds." - IUPAC Goldbook, https://doi.org/10.1351/goldbook.C01258

    This class is supposed to represent such a spatial arragemnet that is an
    exact stationary point on the potential energy surface (PES) of its
    molecular  entity (using the Born-Oppenheimer approximation). These spatial
    arragements are approximated by minimum or saddle point optimizations with
    a particular quantum chemistry method. They do not correspond to a single concrete
    set of internal coordinates, but rather a label for a stationary point. Concrete
    coordinates can be added as the output of quantum chemistry optimization
    calculations.
    """

    description: str | None = None
    """human-readable description of the point"""

    type: Literal["minimum", "saddle-point"]
    """type of the point on the PES"""

    calculations: list[CalcIndex] = Field(default_factory=list)
    """quantum chemistry calculations for this point, e.g.,  geometry optimizations,
    frequency calculations, single point energy calculations, ...
    """

    identifiers: list[StringIdentifier] = Field(
        default_factory=list,
    )
    """string identifiers for the conformation, e.g., InChI, SMILES, ...

    At least "InChI-fixedH" has to be provided.

    .. examples::

        - `{"type": "InChI", "value": "InChI=1S/CH4/h1H4"}`
        - `{"type": "custom", "label": "AMChI",
        "value": "AMChI=1/C5H9/c1-3-5-4-2/h3-5H,1-2H3/b5-3+,5-4+"}`

    .. note::

        The "custom" type is used for identifiers that do not fit into the
        standard types. Programs that use the standard identifiers (InChI,
        SMILES) will read fields with type "InChI" or "SMILES". So, while it is
        possible to supply an InChI via a custom identifier, it is stronlgy
        discouraged.
    """


# design considerations for the relations between conformations:
# - as similar/consistent as possible, e.g., each having a list of calculations, but
#   since conformers have different "roles" in different relations and there are
#   different numbers of possible conformations per role allowed, we do not add a common
#   base class for relations.
# - We do not use the `type: Literal["name of type"]`-pattern to not clutter the
#   yaml file (cf. EquivalenceRelation which has only a single attribute).
# - The relations are imutable and sorted to allow for easy comparisions in Python code


_ConformationIds: TypeAlias = Annotated[
    tuple[ConformationIndex, ...],
    # use lambda to convert list returned by sorted into tuple
    AfterValidator(lambda x: tuple(sorted(x))),
    MinLen(1),
]
"""list of multiple conformations

Conformations may appear multiple times in the list, if their stoichiometric coefficient
is greater than one. When determining if two lists are equal, their order does not
matter, therefore, the list is automatically sorted to simplify comparison in Python
code.
"""


def _sort_conformations_pair(
    value: tuple[_ConformationIds, _ConformationIds],
) -> tuple[_ConformationIds, _ConformationIds]:
    # first entry of a tuple has higher priority when comparing -> sort by length first
    # and then lexicographically
    if (len(value[0]), value[0]) > (len(value[1]), value[1]):
        return value[1], value[0]

    return value


_ConformationsPair: TypeAlias = Annotated[
    tuple[_ConformationIds, _ConformationIds],
    # sort by length first, so that all bimolecular-unimolecular pairs are sorted in the
    # same way
    AfterValidator(_sort_conformations_pair),
]
"""pair of conformations used in multiple relations

When determining if two pairs are equal, their order does not matter, therefore, the
pair is automatically sorted to simplify comparison in Python code.
"""


# private base class to avoid confusion with Relation TypeAlias below
class _RelationBase(HasKeyMixin, RmmdFrozenBaseModel, frozen=True):
    calculations: list[CalcIndex] = Field(default_factory=list)
    """calculations used to confirm this relation.

    For a transition state, include an IRC calculation that confirms that a saddle point connects two minima can be listed here. The transition state optimization should not be listed here but be listed at the conformation representing the transition state. If the normal modes of the transition state were used to confirm this relation, the calculation containing the frequencies can be listed here as well.

    For a barrierless path, include the optimization of the complex or the scan that shows there to be no barrier for a recombination.

    For an equivalence relation, include the calculations that were used to determine the equivalence of the conformations, e.g., RMSD computation (not implemented as a calculation type yet).
    """


# public to allow isinstance(relation, PathRelation) checks and "path-only" type hints
class PathRelation(_RelationBase, frozen=True):
    """relations presenting a path on the PES"""

    end_points: _ConformationsPair
    """the two endpoints of the path on the PES"""

    saddle_point: ConformationIndex | Literal["barrierless"]
    """the saddle point, or "col", of the path."""


class SaddlePointRelation(PathRelation, frozen=True):
    """relates a saddle point on the PES to the minima that it connects.

    Note, that `minimum1` and `minimum2` should point to minima and not simply IRC endpoints, i.e. the last geometries of an IRC scan. IRC endpoint geometries can be included as output of IRC calculations and linked to this relation.
    """

    saddle_point: ConformationIndex
    """saddle point, or "col", of the path"""


class NoBarrierRelation(PathRelation, frozen=True):
    """relates multiple minima on a PES that are connected by a path without a barrier.

    This relation is typically used for two fragments, which are minima on their own PES
    and -- when considered to be infinitely far apart -- a stationary point on the
    combined PES, to a minimum on the combined PES, e.g.,

    - relate a pre-reactive complexes to the optimized reactant fragments.
        Often, the association of the fragments is not relevant to the kinetics and the
        reaction is typically modeled by just considering the fragments. Using this
        relation, one can still include the data belonging to the complex in the
        dataset;
    - relate two radicals which recombine without a barrier to form some product.
    """

    saddle_point: Literal["barrierless"] = "barrierless"
    """no saddle point on the PES, i.e., the path is barrierless"""


class EquivalenceSet(_RelationBase, frozen=True):
    """Relation linking conformations that are considered to be the same conformation.

    While multiple calculations such as different geometry optimizations at different
    levels of theory can be linked to a single conformation, not doing so can be useful.
    Typically, researchers will first have a set of concrete optimized coordinates and
    then determine which of those can be considered the same conformation, e.g., by
    comparing their energies and geometries. First, you could assign each optimized
    geometry to a separate conformation and potentially link a single point energy or
    frequency calculation to these geoemtries through teh conformation. Then, you can
    compare the conformations and use this relation to link conformations which should
    be the same.
    Additionaly, there are multiple ways to do this comparison and different thresholds,
    can be applied, e.g., for the RMSD or rotational constant. This would lead to
    different assignments of the optimized geometries to conformations. Assigning each
    optimized geometry to a separate conformation first and declaring them to be equal
    using this relation allows one to remain flexible.
    """

    equivalent: set[ConformationIndex]
    """indeces of conformations that are considered to be the same"""


def _relation_discriminator(value: _RelationBase | dict) -> str | None:
    """discriminator for the different relation types for faster determinatino of the relation type and smaller error messages"""

    if isinstance(value, dict):
        if "saddle_point" in value:
            if value["saddle_point"] == "barrierless":
                return "barrierless"
            else:
                return "saddle-point"
        elif "equivalent" in value:
            return "equivalence"

    if isinstance(value, EquivalenceSet):
        return "equivalence"
    elif isinstance(value, NoBarrierRelation):
        return "barrierless"
    elif isinstance(value, SaddlePointRelation):
        return "saddle-point"

    raise ValueError(
        "Could not determine type of relation. Expected at least one of the following "
        "keys: 'saddle_point' or 'equivalent'."
    )


# TODO Add internal conversion and intersystem crossing relations

ConformationRelation: TypeAlias = Annotated[
    Annotated[SaddlePointRelation, Tag("saddle-point")]
    | Annotated[NoBarrierRelation, Tag("barrierless")]
    | Annotated[EquivalenceSet, Tag("equivalence")],
    Discriminator(_relation_discriminator),
]
"""Relations between conformations, e.g., which conformations are considered to be"""
