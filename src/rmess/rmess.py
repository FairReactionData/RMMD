"""Defining the Reaction Model Electronic Structure Schema

See this link for a few examples of what you can do:
https://docs.pydantic.dev/latest/concepts/json_schema/#generating-json-schema
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, computed_field

from .keys import CitationKey, PointId, QcCalculationId


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

    point: PointId
    """point in the dataset to which this calculation belongs"""

    references: list[CitationKey]|None = None
    """literature describing the calculation"""
    source: list[CitationKey]|None = None
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

    constitution: Any
    electronic_state: Any

    # solvent: ... # maybe add this later

class Point(BaseModel):
    """Point on a potential energy surface.

    Usually, this is a stationary point, i.e. a set of internal coordinates whose gradient w.r.t. the electronic Schrödinger equation using the Born-Oppenheimer approximation is exactly zero. In general, such coordinates can only be approximated by quantum chemical calculations as the exact solution to the Schrödinger equation is usually unfeasible/impossible. This class represents such a theoretical point and is used to group different calculation results as belonging to the same point.
    """

    domain: BoPesDomain

    calculations: list[QcCalculationId] = Field(default_factory=list)
    """quantum chemistry calculations for this point"""


PointEnsemble = Annotated[list[PointId], Field(min_length=1)]
"""ensemble of stationary points on a potential energy surface

Used when multiple points interconvert fast w.r.t. the timescale of interest,
e.g.; conformers, ..."""

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

