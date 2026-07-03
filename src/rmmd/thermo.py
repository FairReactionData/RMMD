"""Thermochemistry models that are simple equations, such as polynomials."""

from __future__ import annotations

from typing import Annotated, Literal

from annotated_types import MaxLen, MinLen
from pydantic import Discriminator, Tag, model_validator

from ._base import RmmdBaseModel
from .calc import CalculationBase, CalculationInputBase, CalculationOutputBase
from .keys import CalcIndex, CitationKey, ConformationIndex, SpeciesName, ThermoIndex
from .registry import HasKeyMixin


class _ThermoPropertyBase(HasKeyMixin):
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


class _ReferenceStateBase(RmmdBaseModel):
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


class _HasReferenceStateMixin(RmmdBaseModel):
    """ "absolute" thermochemical properties are given with respect to a reference state"""

    reference_state: ReferenceState | Literal["dataset default"] = "dataset default"
    """thermodynamic reference state, i.e., the state at which the enthalpy of formation and entropy of formation of an element is zero
    """


###############################################################################
# established empirical models (data = fitted coefficients)
###############################################################################


class _CoefficientsTRangesMixin(RmmdBaseModel):
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


EmpiricalThermo = Nasa7 | Shomate | ConstantCp | Nasa9


###############################################################################
# fitting provenance
###############################################################################


class FittedToLiterature(RmmdBaseModel):
    """literature sources that the coefficients of this model were fitted to"""

    sources: list[CitationKey]
    """literature sources that the coefficients of this model were fitted to"""


class FittedToThermoData(RmmdBaseModel):
    """thermodynamic data that the coefficients of this model were fitted to"""

    thermo: list[ThermoIndex]
    """thermodynamic data that the coefficients of this model were fitted to"""


class FittedToOtherCalculation(RmmdBaseModel):
    """calculation output that the coefficients of this model were fitted to"""

    output_of: list[CalcIndex]
    """calculation output that the coefficients of this model were fitted to"""


# annotated union for better error messages:
def _fitted_to_discriminator(value: dict | RmmdBaseModel) -> str | None:
    if isinstance(value, dict):
        if "sources" in value:
            return "literature"
        elif "thermo" in value:
            return "thermo data"
        elif "output_of" in value:
            return "calculation output"

    else:
        if hasattr(value, "sources"):
            return "literature"
        elif hasattr(value, "thermo"):
            return "thermo data"
        elif hasattr(value, "output_of"):
            return "calculation output"

    # Could not determine the type, return None to let Pydantic handle the error
    return None


_FittedToUnion = Annotated[
    Annotated[FittedToLiterature, Tag("literature")]
    | Annotated[FittedToThermoData, Tag("thermo")]
    | Annotated[FittedToOtherCalculation, Tag("calculation output")],
    Discriminator(_fitted_to_discriminator),
]


class ThermoParameterFittingInput(CalculationInputBase):
    """input data for a fitting calculation"""

    fitted_to: _FittedToUnion | None = None
    """data/model that the coefficients of this model were fitted to.

    If the model was fitted to data form this dataset, an integer (starting at
    0) to indicate the index of the data in the thermo list of this species.
    """


class ThermoParameterFittingOutput(CalculationOutputBase):
    """output data for a fitting calculation"""

    thermo: ThermoIndex
    """model parameters that were fitted to the data"""

    # TODO add fit quality metric


class ThermoParameterFitting(
    CalculationBase[ThermoParameterFittingInput, ThermoParameterFittingOutput]
):
    """calculation of thermochemical properties derived from fitting to data"""

    type: Literal["thermo param fit"] = "thermo param fit"


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
# schema for supplying thermochemical data derived from quantum chemistry calculations
#
# ThermoQmCalc can provide typical data used in addition to data from quantum chemistry
# calculations (e.g., frequency scaling factors) in a structure way. Due to the many
# different ways to compute thermochemical properties from quantum chemistry
# calculations, users may still have to restort to using the GeneralCalculation class.
###############################################################################


class _SingleRotorData(RmmdBaseModel):
    """thermochemical data for rotors"""

    electronic_energies: list[CalcIndex]

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


class _NDRotorData(RmmdBaseModel):
    """thermochemical data for N-dimensional rotors

    n may be 1 for a hindered rotor
    """

    rotors: Annotated[list[_SingleRotorData], MinLen(1)]


class ConformationThermoData(RmmdBaseModel):
    """Quantum chemistry-derived thermochemical properties for a single
    conformation
    """

    degeneracy: int = 1
    """degeneracy of the conformation, if an enantiomeric conformation"""

    ### data from QC calculations ###
    electronic_energy: CalcIndex
    """electronic energy used for the thermochemistry calculations and
    a reference to the calculation that yielded it
    """

    # TODO how should processing of frequencies be handled? excluding imaginary frequencies for TS, quasi harmonic treatment, frequency scaling, excluding external DOF, ...?
    frequencies: CalcIndex | None = None
    """frequencies used for thermochemical calculations in cm^-1 and
    a reference to the calculation that yielded it

    Here, the eigenvalues belonging to external degrees of freedom, the
    imaginary frequency for a TS, ... are excluded
    """
    geometry: CalcIndex | None = None
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


class ThermoQmCalcInput(CalculationInputBase):
    """data for thermochemical calculations derived from quantum
    chemistry calculations
    """

    conformations: dict[ConformationIndex, ConformationThermoData]
    """data for conformations that are explicitly modeled, e.g., via RRHO or
    by using their electronic energy for computing the conformer mixture
    composition.
    The degeneracy of enantiomeric conformations can be provided as an integer
    in the second element of the tuple.
    """
    internal_rotors: list[_NDRotorData] | None = None
    """data for internal rotors"""


class ThermoQmCalcOutput(CalculationOutputBase):
    """Output of a thermo-from-QM calculation."""

    thermo: ThermoIndex
    """Reference to the thermo entry in the dataset produced by this calculation."""


class ThermoQmCalc(CalculationBase[ThermoQmCalcInput, ThermoQmCalcOutput]):
    """calculation of thermochemical properties derived from quantum chemistry"""

    type: Literal["thermo-from QM"] = "thermo-from QM"
