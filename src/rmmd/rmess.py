"""Defining the Reaction Model Electronic Structure Schema

See this link for a few examples of what you can do:
https://docs.pydantic.dev/latest/concepts/json_schema/#generating-json-schema
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, PositiveInt, computed_field

from rmmd.metadata import LocalFile
from rmmd.keys import CitationKey, PointId, QcCalculationId


class ElectronicState(BaseModel):
    """Definition of the electronic state"""

    # TODO what is the minimum required information? What may we need to add in the future?
    #       for a computational chemist, charge and spin multiplicity
    #       for a mechanism modeler, whether the state is excited or not
    #       other ideas: term symbol, number of unpaired electrons, ...
    #
    #       -> we may have to use different electronic state definitions for different purposes :(

    charge: int
    """total charge"""
    spin: int
    """total electron spin quantum number"""

    @computed_field
    def spin_multiplicity(self) -> int:
        """spin multiplicity, i.e. 2S+1"""
        return 2*self.spin+1

###############################################################################
# Quantum chemistry calculations & their metadata
###############################################################################
class Software(BaseModel):
    """computer software used to perform a calculation"""

    name: str
    version: str

class _QcCalculationBase(BaseModel):
    """base class for quantum chemistry calculations"""

    level_of_theory: str # in v1.0 just a string
    """level of theory used"""
    electronic_state: ElectronicState
    """..."""
    software: Software|None = None
    """..."""

    references: list[CitationKey]|None = None
    """literature describing the calculation"""
    source: list[CitationKey|LocalFile]|None = None
    """source of the data"""

class QcCalculationData(_QcCalculationBase):
    """Data from a quantum chemistry calculation."""

    # TODO add field, e.g. similar to how cclib, QCarchive, ... (focus on most important fields such as geometry, total electronic energy, frequencies, ...)

class QcCalculationReference(_QcCalculationBase):
    """referecne to a quantum chemistry calculation in a public dataset"""

    source: list[CitationKey]    # non-optional
    """references to the data itself"""

QcCalculation = Annotated[QcCalculationData|QcCalculationReference,
                          Field()]
"""quantum chemistry calculation"""


###############################################################################
# physical meaning of calculations
###############################################################################

class BoPesDomain(BaseModel):
    """Domain of a Born-Oppenheimer potential energy surface"""

    constitution: "Constitution"
    electronic_state: ElectronicState

    # solvent: ... # maybe add this later

class Point(BaseModel):
    """Point on a potential energy surface.

    Usually, this is a stationary point, i.e. a set of internal coordinates whose gradient w.r.t. the electronic Schrödinger equation using the Born-Oppenheimer approximation is exactly zero. In general, such coordinates can only be approximated by quantum chemical calculations as the exact solution to the Schrödinger equation is usually unfeasible/impossible. This class represents such a theoretical point and is used to group different calculation results as belonging to the same point.
    """

    domain: BoPesDomain

    description: str|None = None
    """human-readable description of the point"""

    calculations: list[QcCalculationId] = Field(default_factory=list)
    """quantum chemistry calculations for this point"""
    # TODO: really only allow one PointThermo per Point?
    thermo: "PointThermo|None" = None
    """thermochemical properties for this point, if it alone is considered"""


PointEnsemble = Annotated[list[tuple[PointId, PositiveInt]],
                          Field(min_length=1)]
"""ensemble of stationary points on a potential energy surface.

Used when multiple points interconvert fast w.r.t. the timescale of interest,
e.g.; conformers, ...
Each point has a degeneracy which can be provided explicitly as number or
implicitly by introducing additional members each with degeneracy one.
For example, the conformer ensemble of butane could be represented as [(0, 1),
(1, 1), (2, 1)] or [(0, 1), (1, 2)]. Where 0 is the point representing the
trans conformer and 1 and 2 are points representing the two mirror images of
the gauche conformer.
"""

PointSequence = Annotated[list[PointId], Field(min_length=1)]
"""path connecting stationary points on a potential energy surface, e.g., a
IRC path, frozen scane, ...
"""

class _PesStageBase(BaseModel):
    """A stage in a detailed PES network"""

    type: str

class UnimolecularWell(_PesStageBase):
    """A well in a detailed PES network"""

    type: Literal['unimolecular well'] = 'unimolecular well'
    point: PointId|PointEnsemble
    """stationary point(s) of the well"""

class NMolecularWell(_PesStageBase):
    """A bi- or higher molecular well in a detailed PES network.

    Individual molecular entities are considered to be infinitely far apart."""

    type: Literal['n-molecular well'] = 'n-molecular well'
    points: list[PointId|PointEnsemble]
    """points that when combined form the well. Technically, these are points on different lower-dimensional PES domains (i.e. fewer atoms)."""

    @computed_field
    def n(self) -> int:
        return len(self.points)

    # TODO how to interpret bimolecular wells that are not VdW complexes? technically, they are a single point on the same PES domain as the TS with the two molecular entities being modeled as infinitely far apart; alternative view: two points on different PES domains with a special relation between them

class VdWComplex(_PesStageBase):
    """A van der Waals complex in a detailed PES network.

    Individual molecular entities are considered to be infinitely far apart."""

    type: Literal['van der Waals complex'] = 'van der Waals complex'
    point: PointId|PointEnsemble

class NthOrderSaddlePoint(_PesStageBase):
    """A saddle point of order n (>1) in a detailed PES network, e.g. a
    second-order saddle point connecting two TS conformers.
    Use type = transition state for first oder saddle points."""

    type: Literal['nth-order saddle point'] = 'nth-order saddle point'
    order: int
    """order of the saddle point"""
    point: PointId|PointEnsemble
    """stationary point(s) of the saddle point"""

class TransitionState(NthOrderSaddlePoint):
    """A transition state in a detailed PES network"""

    order: Literal[1] = 1
    type: Literal['transition state'] = 'transition state'
    point: PointId|PointEnsemble
    """stationary point(s) of the transition state"""


Well = Annotated[UnimolecularWell|NMolecularWell|VdWComplex,
                     Field(discriminator='type')]
SaddlePoint = Annotated[NthOrderSaddlePoint|TransitionState,
                         Field(discriminator='type')]

class PesReaction(BaseModel):
    """An Edge/"ReactionStep" in a detailed PES network"""

    stages: tuple[Well, Well]
    """product and reactant wells"""
    saddle_point: SaddlePoint
    """transition state"""
    irc_scan_forward: PointSequence|None = None
    """path connecting the stages"""
    irc_scan_backward: PointSequence|None = None
    """path connecting the stages"""

# avoid circular imports by importing here and using forward references above
from rmmd.thermo import PointThermo  # noqa: E402
from rmmd.species import Constitution  # noqa: E402
