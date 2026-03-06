"""Thermochemistry models that are simple equations, such as polynomials."""

from __future__ import annotations

from typing import Annotated, Literal
from annotated_types import MinLen
from pydantic import BaseModel, Field, model_validator
from .pes import ConformationalEnsemble, Software
from .keys import CitationKey, CalcIndex, SpeciesName, ThermoIndex


class _ThermoPropertyBase(BaseModel):
    """Base class for thermochemical properties"""

    type: str
    """unique identifier for the type of thermochemical property"""

    references: list[CitationKey] | None = None
    """Related literature describing how the data was obtained. Can be used in addition to the references list of the main dataset/schema."""
    sources: list[CitationKey] | None = None
    """where the data was obtained from"""


###############################################################################
# thermodynamic reference state
###############################################################################


class _ReferenceStateBase(BaseModel):
    """base class for reference states"""

    T: float
    """reference temperature in K
    """
    p: float
    """reference pressure in Pa"""
    element_reference: Literal[
        "most stable form",  # TODO deal with cases like phosphorus
        "quantum chemistry",
    ] = "most stable form"
    """reference state for elements

    - "most stable form": elements are in their most stable form at the given T and p
    - "quantum chemistry": state where all electrons and nuclei are infinitely separated/non-interacting at 0 K.
    """
    description: str | None = None
    """additional description of the reference state, e.g., level of theory
    used for quantum chemistry ideal gas
    """


class ReferenceStatePure(_ReferenceStateBase):
    """thermodynamic reference state for pure substances"""

    p: float
    """reference pressure in Pa"""


class ReferenceStateSolute(_ReferenceStateBase):
    """thermodynamic reference state for substances in a solvent"""

    concentration: float
    """reference concentration in mol/L"""
    solvent: SpeciesName
    """name of the solvent"""


STATE_1_BAR_298_K = ReferenceStatePure(
    T=298.15,
    p=1e5,
    element_reference="most stable form",
)
"""standard pressure (1 bar) and 298.15 K reference state
"""


ReferenceState = ReferenceStatePure | ReferenceStateSolute
"""union data type for themodynamic reference state"""


class _HasReferenceStateMixin(BaseModel):
    """ "absolute" thermochemical properties are given with respect to a reference state"""

    reference_state: ReferenceState | Literal["dataset default"] = "dataset default"
    """thermodynamic reference state, i.e., the state at which the enthalpy of formation and entropy of formation of an element is zero
    """


###############################################################################
# established empirical models (data = fitted coefficients)
###############################################################################


class _FittedToMixin(BaseModel):
    """inherit from this class to get fields related to fitting provenance"""

    fitted_to: list[CitationKey] | ThermoIndex | CalcIndex | None = None
    """data/model that the coefficients of this model were fitted to.

    If the model was fitted to data form this dataset, an integer (starting at
    0) to indicate the index of the data in the thermo list of this species.
    """


class Nasa7(_ThermoPropertyBase, _FittedToMixin, _HasReferenceStateMixin):
    """NASA polynomial with 7 coefficients."""

    type: Literal["NASA7"] = "NASA7"
    T_ranges: list[tuple[float, float]]
    """Temperature ranges for the polynomial, in K"""
    coefficients: list[list[float]]
    """coefficients for the polynomial in the form: [a1, a2, a3, a4, a5, a6, a7] for each temperature range
    """


class Shomate(_ThermoPropertyBase, _FittedToMixin, _HasReferenceStateMixin):
    """Shomate polynomial with 7 coefficients."""

    type: Literal["Shomate"] = "Shomate"
    T_ranges: list[tuple[float, float]]
    """Temperature ranges for the polynomial, in K"""
    coefficients: list[list[float]]
    """coefficients for the polynomial in the form: [a1, a2, a3, a4, a5, a6, a7] for each temperature range
    """


# TODO add more thermochemistry models (e.g. all that Cantera supports)

EmpiricalThermo = Nasa7 | Shomate


###############################################################################
# raw thermochemical data
###############################################################################


class _ThermoTableBase(_ThermoPropertyBase):
    """base class for thermochemical tables"""

    T: Annotated[list[float], MinLen(1)]
    """Temperature points in K"""
    p: Annotated[list[float], MinLen(1)]
    """Pressure points in Pa"""

    H: list[list[float]] | None = None
    """enthalpy in J/mol

    n x m array of enthalpies, where n is the number of
    pressure points and m is the number of temperature points.
    """
    S: list[list[float]] | None = None
    """entropy in J/(mol K)

    n x m array of entropies, where n is the number of
    pressure points and m is the number of temperature points."""
    G: list[list[float]] | None = None
    """Gibbs free energy in J/mol

    n x m array of Gibbs free energies, where n is the number of
    pressure points and m is the number of temperature points.
    """

    @model_validator(mode="after")
    def check_dimensions(self):
        """check that the dimensions of the data are consistent"""
        n_p = len(self.p)
        n_T = len(self.T)

        for prop_name in ["Cp", "H", "S", "G"]:
            prop = getattr(self, prop_name, None)
            if prop is not None:
                if len(prop) != n_p:
                    raise ValueError(
                        f"Number of rows in {prop_name} must be equal to the"
                        "number of pressure points"
                    )
                for row in prop:
                    if len(row) != n_T:
                        raise ValueError(
                            f"Number of columns in {prop_name} must be equal "
                            "to the number of temperature points"
                        )

        return self


class ThermoTable(_ThermoTableBase, _HasReferenceStateMixin):
    """thermochemical dataset for a specific species in "absolute" terms, i.e.,
    relative to a common reference state"""

    type: Literal["absolute tabular thermo"] = "absolute tabular thermo"


class ThermoTableNoRef(_ThermoTableBase):
    """Thermodynamic properties without a reference state, e.g., difference in thermodynamic properties for two well-defined states such a reaction enthalpies."""

    type: Literal["tabular thermo"] = "tabular thermo"

    Cp: list[list[float]] | None = None
    """heat capacity in J/(mol K)

    n x m array of isobaric heat capacities, where n is the number of
    pressure points and m is the number of temperature points.
    """


TabularThermo = ThermoTable | ThermoTableNoRef

###############################################################################
# quantum chemistry models
###############################################################################


class Rrho(_ThermoPropertyBase):
    """Rigid-Rotor harmonic oscillator"""

    type: Literal["RRHO"] = "RRHO"

    frequencies: CalcIndex  # link to QcCalculation?
    frequency_scaling: float  # TODO value + type + source
    quasi_harmonic_approx: str | None = None
    spe: CalcIndex
    rot_symmetry_nr: int  # TODO source + value
    """rotational symmetry number"""
    software: Software | None = None
    """software used to perform the calculation"""


# TODO how to deal with the different approaches of getting thermochemistry from QM (e.g. even for RRHO you can apply different quasi-harmonic approximations to the parititon function or just to the entropy, there are different ways to apply frequency scaling, ... - not to mention 1DHR)
#   maybe collect different ways of how thermochemistry is obtained from collaboration then think about schema!


class BoltzmannWeightedEnsemble(_ThermoPropertyBase):
    """ensemble of multiple stationary points modelled as RRHO each"""

    type: Literal["Boltzmann weighted ensemble"] = "Boltzmann weighted ensemble"
    members: ConformationalEnsemble
    """members of the ensemble, each with its degeneracy"""
    energy_expression: Literal["G", "H", "electronic energy", "ZPE"]
    """energy expression used in the Boltzmann coefficient to calculate the weigths of ensemble members."""


###############################################################################
# general
###############################################################################

ReactionThermo = Annotated[
    ThermoTableNoRef,
    Field(discriminator="type"),
]
"""Thermochemical data for a specific reaction.
"""

SpeciesThermo = Annotated[
    Nasa7 | Shomate | ThermoTable | BoltzmannWeightedEnsemble | ThermoTableNoRef,
    Field(discriminator="type"),
]
"""Thermochemical data for a specific species. Use this in type hints

All thermoproperties need to have a type field.
"""
