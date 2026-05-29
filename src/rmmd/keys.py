"""contains "local names" of species, reactions, ...

The use of local names/ids/keys is an implementation detail of the validation schema and realized differently in, e.g., a database. Here, we use names to avoid hierarchical structure and repetitions. This module is a separate from schema to avoid circular imports in other models that use the keys defined here.
"""

from __future__ import annotations
from typing import Annotated, Literal

from pydantic import Field, NonNegativeInt, model_serializer, model_validator

from ._base import RmmdFrozenBaseModel


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

SpeciesName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=16,  # from CHEMKIN II
        pattern="^[a-zA-Z][a-zA-Z0-9-+*()=]*$",
        examples=["CH4"],
    ),
]
"""name of a species in the dataset"""

EntityKey = Annotated[
    str,
    Field(
        min_length=27,
        max_length=27,
        pattern="^[A-Z]{14}-[A-Z]{10}-[A-Z]$",
    ),
]
"""key for a canonical representation of a species in the dataset, currently: InChIKey with fixed-H layer"""


class _ListIndex(RmmdFrozenBaseModel, frozen=True):
    """base class for indices referencing items in lists of the root schema"""

    schema_field: str
    """name of the field in the root schema that this index references"""
    value: NonNegativeInt
    """index of the item in the list that this index references"""

    # By implementing __index__, we can use instances of this class as indices in lists
    def __index__(self) -> int:
        return self.value

    @model_validator(mode="before")
    @classmethod
    def convert_from_str(cls, data: dict | _ListIndex | str) -> dict | _ListIndex:
        """for better readbility and clarity, indices are represented as strings in the format "<schema_field>:<integer>", e.g., "calculations:0". This validator converts such strings to the internal representation."""
        if isinstance(data, str):
            if ":" not in data:
                raise ValueError(
                    f"Invalid {cls.model_fields['schema_field'].default} index: expected string in the format '<schema_field>:<integer>', got '{data}'"
                )

            t, v = data.split(":", maxsplit=1)
            schema_field = cls.model_fields["schema_field"].default
            if t != schema_field:
                raise ValueError(
                    f"Invalid {schema_field} index: expected string starting with "
                    ""
                    f"'{schema_field}:', got '{data}'"
                )
            try:
                v = int(v)
            except ValueError:
                raise ValueError(
                    f"Invalid {schema_field} index: expected '{schema_field}:"
                    f"<integer>', got '{data}'"
                )

            return {"value": v, "schema_field": schema_field}
        return data

    @model_serializer(mode="plain")
    def serialize_model(self) -> str:
        return f"{self.schema_field}:{self.value}"

    def __hash__(self) -> int:
        return hash((self.schema_field, self.value))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _ListIndex):
            return NotImplemented
        return (self.schema_field, self.value) == (other.schema_field, other.value)

    # to allow sorting of indeces, e.g., when comparing lists of indices
    def __lt__(self, other: object) -> bool:
        if not isinstance(other, _ListIndex):
            return NotImplemented
        if self.schema_field != other.schema_field:
            raise ValueError(
                f"Cannot compare indices of different schema fields: "
                f"{self.schema_field} and {other.schema_field}"
            )
        return self.value < other.value


class CalcIndex(_ListIndex, frozen=True):
    """index referencing a calculation in the root schema"""

    schema_field: Literal["calculations"] = "calculations"


class ConformationIndex(_ListIndex, frozen=True):
    """index referencing a conformation in the root schema"""

    schema_field: Literal["conformations"] = "conformations"


class ThermoIndex(_ListIndex, frozen=True):
    """index referencing a thermo calculation in the root schema"""

    schema_field: Literal["thermo"] = "thermo"


class KineticsIndex(_ListIndex, frozen=True):
    """index referencing a kinetics calculation in the root schema"""

    schema_field: Literal["kinetics"] = "kinetics"


class TransportIndex(_ListIndex, frozen=True):
    """index referencing a transport property in the root schema"""

    schema_field: Literal["transport"] = "transport"


class ReactionIndex(_ListIndex, frozen=True):
    """index referencing a reaction in the root schema"""

    schema_field: Literal["reactions"] = "reactions"
