"""Tracking data provenance through calculations

Module contains models to define calculations with specific input and output data.
Calculations are RMMD's main mechanism to track the provenance of model data from
ab-initio quantum chemistry calculations to parameters of empirical models for
thermodynamic and kinetic properties.
The mechanism is similar to the Metadata4Ing ontology [1] in the context of which
calculations would be a specialization of "processing step".


[1] Lanza, G., Iglezakis, D., Fuhrmans, M., Jordan, M., Farnbacher, B., Sosa Rodriguez,
    A. A., Leimer, S., Hachinger, S., Arndt, S., Terzijska, D., Wellmann, A.,
    Theissen-Lipp, J., & Munke, J. (2025). Metadata4Ing: An ontology for describing the
    generation of research data within a scientific activity. Zenodo.
    https://doi.org/10.5281/zenodo.17856129
"""

from __future__ import annotations

from typing import Annotated, Generic, Literal, TypeVar

from annotated_types import MinLen
from pydantic import Discriminator, Tag

from ._base import RmmdBaseModel
from .keys import CalcIndex, KineticsIndex, ThermoIndex, TransportIndex
from .metadata import CitationKeyOrDirectReference, UrlNoDoiOrg
from .registry import HasKeyMixin

##############################################################################
# Base classes for calculation input and output
##############################################################################


class CalculationInputBase(RmmdBaseModel):
    """Base class for the input of a calculation.

    All specific input types should inherit from this class. The ``sources``
    field can be used to reference the location of the input data (e.g., an
    input file in the dataset) without or in addition to providing structured
    data in the subclass fields.
    """

    sources: Annotated[list[CitationKeyOrDirectReference], MinLen(1)] | None = None
    """Location of the input data, e.g., a file in the current dataset or a
    reference to a published dataset."""


class CalculationOutputBase(RmmdBaseModel):
    """Base class for the output of a calculation.

    All specific output types should inherit from this class. The ``sources``
    field can be used to reference the location of the output data (e.g., an
    output file in the dataset) without or in addition to providing structured
    data in the subclass fields.
    """

    sources: Annotated[list[CitationKeyOrDirectReference], MinLen(1)] | None = None
    """Location of the output data, e.g., a file in the current dataset or a
    reference to a published dataset."""


# users are not forced to supply structure data and can just link input and output files
class CalculationInputSourcesRequired(RmmdBaseModel):
    """Calculation input defined only by referencing other resources, e.g., input files."""

    sources: Annotated[list[CitationKeyOrDirectReference], MinLen(1)]


class CalculationOutputSourcesRequired(RmmdBaseModel):
    """Calculation output defined only by referencing other resources, e.g., log files."""

    sources: list[CitationKeyOrDirectReference]


# use callable discriminator for better error messages
def _calc_io_discriminator(v: object) -> str | None:
    """Discriminator for calculation input/output data.

    Selects the structured model (the general ``InputT``/``OutputT``) when any
    structured field is provided, or the sources-only model when nothing but
    ``sources`` is given. Returns ``None`` for an empty dict or when all fields
    are ``None``, which makes the ``Discriminator`` raise the custom error
    requiring ``sources`` to be provided.
    """
    if isinstance(v, dict):
        set_fields = {key for key, value in v.items() if value is not None}
    else:
        set_fields = {
            field
            for field in getattr(type(v), "model_fields", ())
            if getattr(v, field, None) is not None
        }
    if not set_fields:
        return None
    if set_fields == {"sources"}:
        return "sources_only"
    return "structured"


InputT = TypeVar("InputT", bound=CalculationInputBase)
OutputT = TypeVar("OutputT", bound=CalculationOutputBase)


class CalculationBase(HasKeyMixin, Generic[InputT, OutputT]):
    """Base class for a calculation."""

    type: str
    """type of the calculation"""

    software: Software
    """software used for the calculation"""

    description: str | None = None
    """description of the calculation, e.g., the method used"""

    references: list[CitationKeyOrDirectReference] | None = None
    """literature describing the calculation

    .. note::

        This field should not be confused with the reference to the data/files
        produced by this calculation, which should be given in
        ``output.sources``.

    Can be used in addition to the references for the whole dataset, e.g., to
    reference a specific paper describing the method used for this calculation.
    """

    input: (
        Annotated[
            Annotated[InputT, Tag("structured")]
            | Annotated[CalculationInputSourcesRequired, Tag("sources_only")],
            Discriminator(
                _calc_io_discriminator,
                custom_error_type="missing_calculation_input",
                custom_error_message=(
                    "'sources' must be provided if no other input data is given."
                ),
            ),
        ]
        | None
    ) = None
    """input data/parameters for the calculation

    Structured input data specific to the calculation type (recommended), or, if
    structured data is not available, the input can be given as a reference to
    another resource containing the data (e.g. a file in this dataset) by providing
    ``input.sources``.
    """

    output: (
        Annotated[
            Annotated[OutputT, Tag("structured")]
            | Annotated[CalculationOutputSourcesRequired, Tag("sources_only")],
            Discriminator(
                _calc_io_discriminator,
                custom_error_type="missing_calculation_output",
                custom_error_message=(
                    "'sources' must be provided if no other output data is given."
                ),
            ),
        ]
        | None
    ) = None
    """output data for the calculation

    Structured output data specific to the calculation type (recommended), or, if
    unavailable, a reference to the raw output data provided via ``output.sources``.
    """


################################################################################
# misc
################################################################################


class Software(RmmdBaseModel):
    """computer software used to perform a calculation"""

    name: Annotated[str, MinLen(1)]
    """name of the software"""
    version: Annotated[str, MinLen(1)]
    """version number or Git hash of the software used for the calculation"""
    repository: UrlNoDoiOrg | None = None
    """URL to the software repository, e.g., GitHub or GitLab"""


class OutputOf(RmmdBaseModel):
    """helper class to declare that a calculation's output is the input for another"""

    output_of: CalcIndex
    """index of the calculation that produces the output of this calculation"""


################################################################################
# useful calculation types
################################################################################


class NestedCalculation(CalculationBase[CalculationInputBase, CalculationOutputBase]):
    """Sometimes, it is more convenient to reference multiple calculations together,
    e.g., when they were performed in a single run of a quantum chemistry
    software and share a single output file. In that case, this class can
    be used to reference multiple calculations together.
    """

    type: Literal["nested"] = "nested"
    """type of the calculation"""

    calculations: Annotated[list[CalcIndex], MinLen(2)]
    """list of calculation ids that are referenced together in this nested
    calculation
    """


class GeneralCalculationInput(CalculationInputBase):
    """Input of a general calculation.

    Allows using different RMMD-representable data as calculation input.
    """

    thermo: Annotated[list[ThermoIndex], MinLen(1)] | None = None
    """thermodynamic model/data used as input for the calculation"""

    transport: Annotated[list[TransportIndex], MinLen(1)] | None = None
    """transport model/data used as input for the calculation"""

    rate_coefficients: Annotated[list[KineticsIndex], MinLen(1)] | None = None
    """kinetic model/data used as input for the calculation"""

    output_of: Annotated[list[CalcIndex], MinLen(1)] | None = None
    """calculation(s) that produced the input data for this calculation"""


class GeneralCalculationOutput(CalculationOutputBase):
    """Output of a general calculation.

    Allows using different RMMD-representable data as calculation output.
    """

    thermo: Annotated[list[ThermoIndex], MinLen(1)] | None = None
    """thermodynamic model/data produced by the calculation"""

    transport: Annotated[list[TransportIndex], MinLen(1)] | None = None
    """transport model/data produced by the calculation"""

    rate_coefficients: Annotated[list[KineticsIndex], MinLen(1)] | None = None
    """kinetic model/data produced by the calculation"""


class GeneralCalculation(
    CalculationBase[GeneralCalculationInput, GeneralCalculationOutput]
):
    """General calculation, if no suitable specific calculation class is available.

    While a specific calculation is preferred to provide machine-actionable, structured
    data, the "general" calculation type can be used to add provenance information for
    data that is not yet represented in RMMD.
    Input and output can be different RMMD-representable data types, e.g.,
    thermodynamic, transport, or kinetic data, as well as literature references.
    """

    type: Literal["general"] = "general"
    """type of the calculation"""
