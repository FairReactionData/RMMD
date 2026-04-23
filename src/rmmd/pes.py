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
from .calc import CalculationBase
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

    calculations: list[CalcIndex] = Field(default_factory=list)
    """quantum chemistry calculations for this point"""


ConformationIds: TypeAlias = Annotated[
    tuple[ConformationIndex, ...], AfterValidator(sorted), MinLen(1)
]
"""list of multiple conformations

Conformations may appear multiple times in the list, if their stoichiometric coefficient
is greater than one. When determining if two lists are equal, their order does not
matter, therefore, the list is automatically sorted to simplify comparison in Python
code.
"""


class IRCRelation(RmmdFrozenBaseModel, frozen=True):
    stationary_point: ConformationIndex
    """stationary point, col, or "transition state" of the IRC path"""

    irc_endpoints: tuple[ConformationIds, ConformationIds]
    """IRC endpoints, i.e., the conformations at the end of the IRC path in both directions. If there is a pre-reactive complex, it is recommended, to include that as a separate conformation, use it as endpoint, and link it to the optimized fragment of the reactant/product using the OptimizedFragmentRelation.
    """


class OptimizedFragmentRelation(RmmdFrozenBaseModel, frozen=True):
    """Relation linking a conformation to an optimized fragment of it.

    Can be applied to pre-reactive complexes to link the complex with the optimized
    reactant and product fragments. Often, the association of the fragments is not
    relevant to the kinetics and the reaction is typically modeled by just considering
    the fragments. Using this relation, one can still include the data belonging to the
    complex in the dataset.
    """

    parent: ConformationIndex
    """index of the parent conformation, e.g., the complex"""
    fragments: ConformationIds
    """index of the optimized fragment conformation"""


class EqualityRelation(RmmdFrozenBaseModel, frozen=True):
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

    equal: set[ConformationIndex]
    """indeces of conformations that are considered to be the same"""


ConformationRelation: TypeAlias = (
    IRCRelation | OptimizedFragmentRelation | EqualityRelation
)
"""Relations between conformations, e.g., which conformations are considered to be"""
