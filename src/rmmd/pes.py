"""Defining the Reaction Model Electronic Structure Schema

See this link for a few examples of what you can do:
https://docs.pydantic.dev/latest/concepts/json_schema/#generating-json-schema
"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import (
    BaseModel,
    Field,
    NonNegativeInt,
    PositiveInt,
    model_validator,
)

from .elements import ElementSymbol
from .metadata import CitationKeyOrDirectReference
from .keys import ConformationId, EntityKey, QcCalculationId


class ElectronicState(BaseModel):
    """Definition of the electronic state"""

    charge: int
    """total charge"""
    spin: NonNegativeInt | Literal["unkown"]
    """2S - two times the electron spin quantum number"""

    description: str | None = None
    """human-readable description of the electronic state, e.g. "ground state"

    This field is required, if spin is unkown. This field can also be used to
    add additional information about the electronic state, e.g., the term
    symbol
    """

    @model_validator(mode="after")
    def require_description_for_unkown_spin(self):
        """require a description if the spin is unkown"""
        if self.spin == "unkown" and not self.description:
            raise ValueError("Description is required if the spin is unkown")
        return self


class ElectronicStateWitSpin(ElectronicState):
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


class Software(BaseModel):
    """computer software used to perform a calculation"""

    name: str
    version: str


class _QmCalculationDataBase(BaseModel):
    """base class for quantum chemistry calculations"""

    level_of_theory: LevelOfTheory
    """level of theory used"""
    electronic_state: ElectronicState
    """..."""
    software: Software | None = None
    """..."""

    references: list[CitationKeyOrDirectReference] | None = None
    """literature describing the calculation"""
    source: list[CitationKeyOrDirectReference] | None = None
    """source or location of the full QM data.

    Ideally the full data is hosted in a specialized repository, e.g., NOMAD,
    ioChem-BD, ... The identifier of the source should not point to a whole
    dataset of calculations, but to a single calculation or file in the
    dataset."""


class QmCalculationReference(BaseModel):
    """reference to a quantum chemistry calculation in a public dataset"""

    type: Literal["reference"] = "reference"
    # for references this metadata is optional as we assume that the referenced
    # dataset already contains the metadata
    level_of_theory: LevelOfTheory | None = None
    """level of theory used"""
    electronic_state: ElectronicState | None = None
    """electronic state of the calculation"""
    software: Software | None = None
    """..."""

    references: list[CitationKeyOrDirectReference] | None = None
    """literature describing the calculation"""
    source: list[CitationKeyOrDirectReference]
    """source or location of the QM calculation's data.

    Ideally the full data is hosted in a specialized repository, e.g., NOMAD,
    ioChem-BD, ... The identifier of the source should not point to a whole
    dataset of calculations, but to a single calculation or file in the
    dataset."""


class QmMultiCalculationData(BaseModel):
    """Data from multi step calculations, e.g. Gaussian jobs with several --Link1-- steps, an ORCA compound job, or an IRC scan in both directions"""

    type: Literal["nested"] = "nested"
    """type of the calculation"""
    # no need to use calculation id as the inner calculations are part of this
    # calculation and should be referenced by this calculation's id
    calculations: list[QmCalculationData]
    """list of calculations that are part of this nested calculation"""

    software: Software | None = None
    """..."""

    references: list[CitationKeyOrDirectReference] | None = None
    """literature describing the calculation"""
    source: list[CitationKeyOrDirectReference] | None = None
    """source or location of the full QM data.

    Ideally the full data is hosted in a specialized repository, e.g., NOMAD,
    ioChem-BD, ... The identifier of the source should not point to a whole
    dataset of calculations, but to a single calculation or file in the
    dataset."""


class Geometry(BaseModel):
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


class Geometries(BaseModel):
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


class QmOptData(_QmCalculationDataBase):
    """Data from a geometry optimization calculation"""

    type: Literal["opt", "ts"] = "opt"
    """type of the calculation"""
    geometry: Geometry
    """geometry of the optimized structure"""
    total_electronic_energy: float
    """total electronic energy in Hartree"""
    gradient: list[tuple[float, float, float]] | None = None
    """gradient of the energy w.r.t. the coordinates [Hartree/Å]"""


class QmFreqData(_QmCalculationDataBase):
    """Data from a frequency calculation"""

    type: Literal["freq"] = "freq"
    """type of the calculation"""
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


# TODO remove and use MultiCalculationData with opt and freq calculations instead?
class QmOptFreqData(_QmCalculationDataBase):
    """Data from a geometry optimization calculation with frequencies"""

    type: Literal["opt&freq", "ts&freq"] = "opt&freq"
    """type of the calculation"""

    frequencies: list[float]
    """frequencies in cm^-1"""
    geometry: Geometry
    """geometry of the optimized structure"""
    total_electronic_energy: float
    """total electronic energy in Hartree"""
    gradient: list[tuple[float, float, float]] | None = None
    """gradient of the energy w.r.t. the coordinates [Hartree/Å]"""
    rot_symmetry_nr: int | None = None
    """rotational symmetry number"""
    hessian: list[list[float]] | None = None
    """Hessian matrix in atomic units, i.e. second derivatives of the energy
    w.r.t. the coordinates [Hartree/Å]"""

    # TODO add field, e.g. similar to how cclib, QCarchive, ... (focus on most important fields such as geometry, total electronic energy, frequencies, ...)


class QmSpeData(_QmCalculationDataBase):
    """Data from a single-point energy calculation"""

    type: Literal["spe"] = "spe"
    """type of the calculation"""
    total_electronic_energy: float
    """total electronic energy in Hartree"""


class QmIrcData(_QmCalculationDataBase):
    """Data from an intrinsic reaction coordinate scan in a single direction"""

    type: Literal["irc"] = "irc"
    """type of the calculation"""
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


QmCalculationData = Annotated[
    QmOptData
    | QmFreqData
    | QmOptFreqData
    | QmIrcData
    | QmSpeData
    | QmMultiCalculationData,
    Field(discriminator="type"),
]
"""Data from a quantum chemistry calculation."""

QmCalculation = Annotated[
    QmCalculationData | QmCalculationReference, Field(discriminator="type")
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


class Conformation(BaseModel):
    """ "The spatial arrangement of the atoms affording distinction between
    stereoisomers which can be interconverted by rotations about formally
    single bonds." - IUPAC Goldbook, https://doi.org/10.1351/goldbook.C01258

    This class is supposed to represent such a spatial arragemnet that is an
    exact stationary point on the potential energy surface (PES) of its
    molecular  entity (using the Born-Oppenheimer approximation). These spatial
    arragements are approximated by minimum or saddle point optimizations with
    a particular quantum chemistry method.
    """

    description: str | None = None
    """human-readable description of the point"""

    calculations: list[QcCalculationId] = Field(default_factory=list)
    """quantum chemistry calculations for this point"""


ConformationalEnsemble = Annotated[
    list[tuple[ConformationId, PositiveInt]], Field(min_length=1)
]
"""ensemble of conformations

Used when multiple points interconvert fast w.r.t. the timescale of interest,
e.g.; conformers, ...
Each point has a degeneracy which can be provided explicitly as number or
implicitly by introducing additional members each with degeneracy one.
For example, the conformer ensemble of butane could be represented as [(0, 1),
(1, 1), (2, 1)] or [(0, 1), (1, 2)]. Where 0 is the point representing the
trans conformer and 1 and 2 are points representing the two mirror images of
the gauche conformer.
"""

PointSequence = Annotated[list[ConformationId], Field(min_length=1)]
"""path connecting stationary points on a potential energy surface, e.g., a
IRC path, frozen scane, ...
"""

Well: TypeAlias = set[EntityKey]
"""n-molecular well - set of molecular entities which are minima on a PES
"""

TransitionState: TypeAlias = EntityKey
"""a transition state

represented by a molecular entity whose connectivity is a condensed reaction
graph
"""


class PesPath(BaseModel):
    """An Edge/"ReactionStep" in a detailed PES network"""

    stages: tuple[Well, Well]
    """product and reactant wells"""
    transition_state: TransitionState
    """transition state"""
