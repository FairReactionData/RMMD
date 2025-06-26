"""contains "local names" of species, reactions, ...

The use of local names/ids/keys is an implementation detail of the validation schema and realized differently in, e.g., a database. Here, we use names to avoid hierarchical structure and repetitions. This module is a separate module to avoid circular imports.
"""
from pydantic import Field, RootModel, model_validator


from typing import Annotated

CitationKey = Annotated[str, Field(min_length=1,
                                   # Often, either citation keys or direct
                                   # references via a URL or a local path can
                                   # be used. Both are strings and need to be
                                   # distinguished. Hence, the pattern is
                                   # relatively strict.
                                   pattern="^[a-zA-Z0-9][a-zA-Z0-9-.]*$",
                                   examples=["arrhenius1889"],
                                   )]
"""key for a literature reference. Has to begin with an alphanumeric character.
"""

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

class QcCalculationId(RootModel[int|tuple[int, int]]):
    """index of calculation in the list of calculations.

    Since multiple calculation jobs can be performed in a single run for many
    quantum chemistry softwares, the id can be either a single integer
    or a tuple of two integers."""

    @model_validator(mode='before')
    def convert_from_string(cls, value: str) -> tuple[int, int]|int:
        """A string "x.y" is converted to a tuple (x, y) or just x if y is not
        present."""
        if isinstance(value, str):
            parts = value.split('.')

            for part in parts:
                if not part.isdigit():
                    raise ValueError("All parts must be integers")

            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
            elif len(parts) == 1:
                return int(parts[0])
            else:
                raise ValueError("Invalid format, expected 'X.Y' or 'X'")
        return value

PointId = int
"""index of point in the list of points"""


