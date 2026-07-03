"""contains "local names" of species, reactions, ...

The use of local names/ids/keys is an implementation detail of the validation schema and realized differently in, e.g., a database. Here, we use names to avoid hierarchical structure and repetitions. This module is a separate from schema to avoid circular imports in other models that use the keys defined here.
"""

from __future__ import annotations
from typing import Annotated

from pydantic import Field


CitationKey = Annotated[
    str,
    Field(
        min_length=1,
        # Often, either citation keys or direct
        # references via a URL or a local path can
        # be used. Both are strings and need to be
        # distinguished. Hence, the pattern is
        # relatively strict.
        pattern="^[a-zA-Z0-9][a-zA-Z0-9-.]*$",
        examples=["arrhenius1889"],
    ),
]
"""key for a literature reference. Has to begin with an alphanumeric character.
"""

RegistryKey = Annotated[
    str,
    Field(
        min_length=1,
        # We need some limit, 80 seems reasonable
        max_length=80,
        # Allow a broad but controlled set of ASCII characters commonly used
        # in identifiers, filenames and SMILES. Must start with an
        # alphanumeric character to avoid complications such as keys starting with
        # special characters that may have special meaning in YAML or other
        # serialization formats.
        # Disallowing spaces will reduce complications with YAML files and unquoted
        # strings in various file formats. ":" and "#" will require quotation in YAML,
        # but SMILES may contain them
        pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9_\-\.\:\/@#%+\(\)\$=\[\]><]{0,79})$",
        examples=[
            "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
            "species-123",
            "CH4_iso(1)",
            "path/to/species",
            "C=C",
            "C$C",
        ],
    ),
]
"""keys for items in the registries of the root schema"""

SpeciesName = RegistryKey
"""name of a species in the dataset"""

EntityKey = RegistryKey
"""key for a canonical representation of a species in the dataset"""

##############################################################################
# Cross-reference key types (aliases of RegistryKey)
##############################################################################

CalcIndex = RegistryKey
"""key referencing a calculation in the calculations registry"""

ConformationIndex = RegistryKey
"""key referencing a conformation in the conformations registry"""

ThermoIndex = RegistryKey
"""key referencing a thermo item in the thermo registry"""

KineticsIndex = RegistryKey
"""key referencing a kinetics item in the rate_coefficients registry"""

TransportIndex = RegistryKey
"""key referencing a transport property in the transport registry"""

ReactionIndex = RegistryKey
"""key referencing a reaction in the reactions registry"""
