"""contains "local names" of species, reactions, ...

The use of local names/ids/keys is an implementation detail of the validation schema and realized differently in, e.g., a database. Here, we use names to avoid hierarchical structure and repetitions. This module is a separate module to avoid circular imports.
"""
from pydantic import Field


from typing import Annotated


CitationKey = Annotated[str, Field(min_length=1,
                                   pattern="^[a-zA-Z0-9-.]+$",
                                   examples=["arrhenius1889"],
                                   )]
"""key for a literature reference"""

SpeciesName = Annotated[str, Field(min_length=1,
                                   max_length=16,  # from CHEMKIN II
                                   pattern="^[a-zA-Z][a-zA-Z0-9-+*()]*$",
                                   examples=["CH4"],
                                   )]
"""name of a species in the dataset"""

EntityKey = Annotated[str, Field(min_length=27, max_length=27,
                                   pattern="^[A-Z]{14}-[A-Z]{10}-[A-Z]$",
                                   )]
"""key for a canonical representation of a species in the dataset, currently: InChIKey with fixed-H layer"""

QcCalculationId = int
"""index of calculation in the list of calculations"""
PointId = int
"""index of point in the list of points"""