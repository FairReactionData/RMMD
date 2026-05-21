"""Defining the Reaction Model Electronic Structure Schema

See this link for a few examples of what you can do:
https://docs.pydantic.dev/latest/concepts/json_schema/#generating-json-schema
"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from annotated_types import MinLen
from pydantic import (
    AfterValidator,
    Field,
    NonNegativeInt,
    model_validator,
)

from ._base import RmmdBaseModel, RmmdFrozenBaseModel
from .calc import CalculationBase, OutputOf
from .elements import ElementSymbol
from .keys import CalcIndex, ConformationIndex


class ElectronicState(RmmdBaseModel, frozen=True):
    """Definition of the electronic state"""

    charge: int
    """total charge"""
    spin: NonNegativeInt | Literal["unknown"]
    """2S - two times the electron spin quantum number"""

    description: str | None = None
    """human-readable description of the electronic state, e.g. "ground state"

    This field is required, if spin is unknown. This field can also be used to
    add additional information about the electronic state, e.g., the term
    symbol
    """

    @model_validator(mode="after")
    def require_description_for_unknown_spin(self):
        """require a description if the spin is unknown"""
        if self.spin == "unknown" and not self.description:
            raise ValueError("Description is required if the spin is unknown")
        return self


class ElectronicStateWitSpin(ElectronicState, frozen=True):
    """Electronic state with spin multiplicity

    This model should be used where the spin multiplicity is required, e.g., in
    quantum chemistry calculations.
    """

    spin: NonNegativeInt
    """2S - two times the electron spin quantum number"""

    def spin_multiplicity(self) -> int:
        """spin multiplicity, i.e. 2S+1"""
        return self.spin + 1


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


class QmIrcScan(CalculationBase[_QmInput, _QmIrcScanData]):
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


class Conformation(RmmdBaseModel):
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

    type: Literal["minimum", "saddle-point"] | None = None
    """type of the point on the PES"""

    calculations: list[CalcIndex] = Field(default_factory=list)
    """quantum chemistry calculations for this point, e.g.,  geometry optimizations,
    frequency calculations, single point energy calculations, ...
    """


# design considerations for the relations between conformations:
# - as similar/consistent as possible, e.g., each having a list of calculations, but
#   since conformers have different "roles" in different relations and there are
#   different numbers of possible conformations per role allowed, we do not add a common
#   base class for relations.
# - We do not use the `type: Literal["name of type"]` pattern to not clutter the
#   yaml file (EquivalenceRelation which has only a single attribute).
# - The relations are imutable and sorted to allow for easy comparisions in Python code


_ConformationIds: TypeAlias = Annotated[
    tuple[ConformationIndex, ...], AfterValidator(sorted), MinLen(1)
]
"""list of multiple conformations

Conformations may appear multiple times in the list, if their stoichiometric coefficient
is greater than one. When determining if two lists are equal, their order does not
matter, therefore, the list is automatically sorted to simplify comparison in Python
code.
"""

_ConformationsPair: TypeAlias = Annotated[
    tuple[_ConformationIds, _ConformationIds], AfterValidator(sorted)
]
"""pair of conformations used in multiple relations

When determining if two pairs are equal, their order does not matter, therefore, the
pair is automatically sorted to simplify comparison in Python code.
"""


class SaddlePointRelation(RmmdFrozenBaseModel, frozen=True):
    """relates a saddle point on the PES to the minima that it connects.

    Note, that `minimum1` and `minimum2` should point to minima and not simply IRC endpoints, i.e. the last geometries of an IRC scan. IRC endpoint geometries can be included as output of IRC calculations and linked to this relation.
    """

    saddle_point: ConformationIndex
    """saddle point, or "col", of the IRC path"""

    minima: _ConformationsPair
    """the two minima on the PES connected by the saddle point"""

    calculations: list[CalcIndex] = Field(default_factory=list)
    """quantum chemistry calculations for this IRC path, e.g., the IRC calculation(s)
    themselves.

    The transition state optimization should not be listed here but be listed at the conformation representing the transition state. If the normal modes of the transition state were used to confirm this relation, the calculation containing the frequencies can be listed here as well.
    """


class NoBarrierRelation(RmmdFrozenBaseModel, frozen=True):
    """relates multiple minima on a PES that are connected by a path without a barrier.

    This relation is typically used for two fragments which are minima on their own PES
    and -- when considered to be infinitely far apart -- on the combined PES to a
    minimum on the combined PES, e.g.,

    - relate a pre-reactive complexes to the optimized reactant fragments.
        Often, the association of the fragments is not relevant to the kinetics and the
        reaction is typically modeled by just considering the fragments. Using this
        relation, one can still include the data belonging to the complex in the dataset;
    - relate two radicals which recombine without a barrier to form some product.
    """

    minima: _ConformationsPair
    """the two minima on the PES connected by a path without a barrier"""

    calculations: list[CalcIndex] = Field(default_factory=list)
    """quantum chemistry calculations, i.e., the optimization of a structure containing
    both fragments which minimizes to a complex.
    """


class EquivalenceRelation(RmmdFrozenBaseModel, frozen=True):
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

    calculations: list[CalcIndex] = Field(default_factory=list)
    """can be used for linking that were used to determine the equivalence of the
    conformations, e.g., RMSD computation (not implemented as a calculation type yet)
    """


ConformationRelation: TypeAlias = (
    SaddlePointRelation | NoBarrierRelation | EquivalenceRelation
)
"""Relations between conformations, e.g., which conformations are considered to be"""
