"""Thermochemistry models that are simple equations, such as polynomials."""

from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, Field

from .pes import PointEnsemble, Software
from .keys import CitationKey, QcCalculationId


class _ThermoPropertyBase(BaseModel):
    """Base class for thermochemical properties"""

    type: str
    """unique identifier for the type of thermochemical property"""

    references: list[CitationKey] | None = None
    """Related literature describing how the data was obtained. Can be used in addition to the references list of the main dataset/schema."""
    source: list[CitationKey] | None = None
    """where the data was obtained from"""


###############################################################################
# established empirical models (data = fitted coefficients)
###############################################################################
class _FittedToMixin(BaseModel):
    """inherit from this class to get fields related to fitting provenance"""

    fitted_to: list[CitationKey] | int | None = None
    """data/model that the coefficients of this model were fitted to.

    If the model was fitted to data form this dataset, an integer (starting at
    0) to indicate the index of the data in the thermo list of this species.
    """


class Nasa7(_ThermoPropertyBase, _FittedToMixin):
    """NASA polynomial with 7 coefficients."""

    type: Literal["NASA7"] = "NASA7"
    T_ranges: list[tuple[float, float]]
    """Temperature ranges for the polynomial, in K"""
    coefficients: list[list[float]]
    """coefficients for the polynomial in the form: [a1, a2, a3, a4, a5, a6, a7] for each temperature range
    """


class Shomate(_ThermoPropertyBase, _FittedToMixin):
    """Shomate polynomial with 7 coefficients."""

    type: Literal["Shomate"] = "Shomate"
    T_ranges: list[tuple[float, float]]
    """Temperature ranges for the polynomial, in K"""
    coefficients: list[list[float]]
    """coefficients for the polynomial in the form: [a1, a2, a3, a4, a5, a6, a7] for each temperature range
    """


# TODO add more thermochemistry models (e.g. all that Cantera supports)

###############################################################################
# raw thermochemical data
###############################################################################


class ThermoTable(_ThermoPropertyBase):
    """thermochemical dataset for a specific species"""

    type: Literal["tabular thermo data"] = "tabular thermo data"
    T: list[float]
    """Temperature points in K"""
    p: list[float] | float
    """Pressure points in Pa"""
    Cp: list[float] | None = None
    """heat capacity in J/(mol K)"""
    H: list[float] | None = None
    """enthalpy in J/mol"""
    S: list[float] | None = None
    """entropy in J/(mol K)"""
    G: list[float] | None = None
    """Gibbs free energy in J/mol"""

    # TODO add field for describing the reference states, e.g. standard formation enthalpies in gas phase, etc.


###############################################################################
# quantum chemistry models
###############################################################################


class Rrho(_ThermoPropertyBase):
    """Rigid-Rotor harmonic oscillator"""

    type: Literal["RRHO"] = "RRHO"

    frequencies: QcCalculationId  # link to QcCalculation?
    frequency_scaling: float  # TODO value + type + source
    quasi_harmonic_approx: str | None = None
    spe: QcCalculationId
    rot_symmetry_nr: int  # TODO source + value
    """rotational symmetry number"""
    software: Software | None = None
    """software used to perform the calculation"""


# TODO how to deal with the different approaches of getting thermochemistry from QM (e.g. even for RRHO you can apply different quasi-harmonic approximations to the parititon function or just to the entropy, there are different ways to apply frequency scaling, ... - not to mention 1DHR)
#   maybe collect different ways of how thermochemistry is obtained from collaboration then think about schema!


class BoltzmannWeightedEnsemble(_ThermoPropertyBase):
    """ensemble of multiple stationary points modelled as RRHO each"""

    type: Literal["Boltzmann weighted ensemble"] = "Boltzmann weighted ensemble"
    members: PointEnsemble
    """members of the ensemble, each with its degeneracy"""
    energy_expression: Literal["G", "H", "electronic energy", "ZPE"]
    """energy expression used in the Boltzmann coefficient to calculate the weigths of ensemble members."""


###############################################################################
# general
###############################################################################

SpeciesThermo = Annotated[
    Nasa7 | Shomate | ThermoTable | BoltzmannWeightedEnsemble,
    Field(discriminator="type"),
]
"""Thermochemical data for a specific species. Use this in type hints

All thermoproperties need to have a type field.
"""

PointThermo = Rrho
"""Thermochemical data for a specific point on a potential energy surface."""
