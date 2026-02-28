"""Thermochemistry models that are simple equations, such as polynomials."""

from __future__ import annotations

from typing import Annotated, Literal

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, model_validator

from .calc import CalculationBase
from .keys import (
    CalcIdx,
    CitationKey,
    ConformationIdx,
    SpeciesName,
    ThermoIdx,
)


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

    fitted_to: list[CitationKey] | ThermoIdx | CalcIdx | None = None
    """data/model that the coefficients of this model were fitted to.

    If the model was fitted to data form this dataset, an integer (starting at
    0) to indicate the index of the data in the thermo list of this species.
    """


class _CoefficientsTRangesMixin(BaseModel):
    T_ranges: list[tuple[float, float]]
    coefficients: list[list[float]]

    @model_validator(mode="after")
    def check_T_ranges_and_coefficients(self):
        """check that the number of temperature ranges matches the number of coefficient sets"""
        if len(self.T_ranges) != len(self.coefficients):
            raise ValueError(
                "Number of temperature ranges must match the number of coefficient sets"
            )
        return self


class Nasa7(
    _ThermoPropertyBase,
    _FittedToMixin,
    _HasReferenceStateMixin,
    _CoefficientsTRangesMixin,
):
    """NASA polynomial with 7 coefficients."""

    type: Literal["NASA7"] = "NASA7"
    T_ranges: list[tuple[float, float]]
    """Temperature ranges for the polynomial, in K"""
    coefficients: list[Annotated[list[float], MinLen(7), MaxLen(7)]]
    """coefficients for the polynomial in the form: [a1, a2, a3, a4, a5, a6, a7] for each temperature range
    """


class Nasa9(
    _ThermoPropertyBase,
    _FittedToMixin,
    _HasReferenceStateMixin,
    _CoefficientsTRangesMixin,
):
    """NASA polynomial with 9 coefficients."""

    type: Literal["NASA9"] = "NASA9"
    T_ranges: list[tuple[float, float]]
    """Temperature ranges for the polynomial, in K"""
    coefficients: list[Annotated[list[float], MinLen(9), MaxLen(9)]]
    """coefficients for the polynomial in the form: [a1, a2, a3, a4, a5, a6, a7, a8, a9] for each temperature range
    """


class Shomate(
    _ThermoPropertyBase,
    _FittedToMixin,
    _HasReferenceStateMixin,
    _CoefficientsTRangesMixin,
):
    """Shomate polynomial with 7 coefficients."""

    type: Literal["Shomate"] = "Shomate"
    T_ranges: list[tuple[float, float]]
    """Temperature ranges for the polynomial, in K"""
    coefficients: list[Annotated[list[float], MinLen(7), MaxLen(7)]]
    """coefficients for the polynomial in the form: [a1, a2, a3, a4, a5, a6, a7] for each temperature range
    """


class ConstantCp(_ThermoPropertyBase, _HasReferenceStateMixin):
    """Constant heat capacity model."""

    type: Literal["constant-cp"] = "constant-cp"

    T_range: tuple[float, float]
    """Temperature range in K over which the model is valid"""

    H0: float
    """enthalpy at reference temperature in J/mol"""
    S0: float
    """entropy at reference temperature in J/(mol K)"""
    Cp: float
    """constant heat capacity in J/(mol K)"""


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


class QmThermoCalcInput(BaseModel):
    """data for thermochemical calculations derived from quantum
    chemistry calculations
    """

    conformations: dict[ConformationIdx, ConformationThermoData]
    """data for conformations that are explicitly modeled, e.g., via RRHO or
    by using their electronic energy for computing the conformer mixture
    composition.
    The degeneracy of enantiomeric conformations can be provided as an integer
    in the second element of the tuple.
    """
    internal_rotors: list[_NDRotorData] | None = None
    """data for internal rotors"""


class _SingleRotorData(BaseModel):
    """thermochemical data for rotors"""

    electronic_energies: list[CalcIdx]

    moving_group: list[int]
    """(zero-based) indices of the atoms belonging to the moving group/top
    of the rotor
    """
    axis: tuple[int, int]
    """(zero-based) indices of the two atoms defining the axis of rotation
    """
    sigma: int
    """symmetry number for the rotor"""

    # TODO pivot points?


class _NDRotorData(BaseModel):
    """thermochemical data for N-dimensional rotors

    n may be 1 for a hindered rotor
    """

    rotos: Annotated[list[_SingleRotorData], MinLen(1)]


class ConformationThermoData(BaseModel):
    """Quantum chemistry-derived thermochemical properties for a single
    conformation
    """

    degeneracy: int = 1
    """degeneracy of the conformation, if an enantiomeric conformation"""

    ### data from QC calculations ###
    electronic_energy: CalcIdx
    """electronic energy used for the thermochemistry calculations and
    a reference to the calculation that yielded it
    """

    # TODO how should processing of frequencies be handled? excluding imaginary frequencies for TS, quasi harmonic treatment, frequency scaling, excluding external DOF, ...?
    frequencies: CalcIdx | None = None
    """frequencies used for thermochemical calculations in cm^-1 and
    a reference to the calculation that yielded it

    Here, the eigenvalues belonging to external degrees of freedom, the
    imaginary frequency for a TS, ... are excluded
    """
    geometry: CalcIdx | None = None
    """geometry used for thermochemical calculations and a reference to the
    calculation that yielded it
    """

    ### data not (necessarily) from QC software output ###
    frequency_scaling: float | None = None
    """factor used to scale frequencies"""
    rot_symmetry_nr: int | None = None
    """rotational symmetry number"""
    quasi_harmonic_approx: str | None = None
    """short string describing the quasi-harmonic approximation, e.g.,
    "Truhlar", "Grimme", ...
    More details should be provided in the paper referenced via source
    """


class ThermoQmCalc(CalculationBase[QmThermoCalcInput, ThermoIdx]):
    """calculation of thermochemical properties derived from quantum chemistry"""

    type: Literal["thermo from QM"] = "thermo from QM"
