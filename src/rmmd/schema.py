"""Defining the Reaction Model Electronic Structure Schema

See this link for a few examples of what you can do:
https://docs.pydantic.dev/latest/concepts/json_schema/#generating-json-schema
"""

import json
from typing import Literal

from pydantic import BaseModel


# Species
class Calculation(BaseModel):
    """An individual point/calculation"""

    # AVC question: Our SQL schema separates Point (geometry) from Calculation (input)
    #              Is this worth doing here as well?
    symbols: list[str]
    coordinates: list[tuple[float, float, float]]
    charge: int
    multiplicity: int
    frequencies: list[float]
    electronic_energy: float
    gibbs_energy: float


class Conformer(BaseModel):
    calculations: list[Calculation]  # see comment above about Point and Calculation


class Species(BaseModel):
    conformers: list[Conformer]


class LumpedSpecies(BaseModel):
    """Describes the contribution of each species to the lump.

    Example:
        (C2H5OH, 0.2)
        (C3H7OH, 0.4)
        (C4H9OH, 0.4)
    """

    species_fractions: list[tuple[Species, float]]


# Detail network elements
#   Each detailed network will connect specific points at a specific level of theory
class DetailNode(BaseModel):
    """A Node/"NetworkStage" in a detailed PES network"""

    calculations: list[Calculation]


class DetailEdge(BaseModel):
    """An Edge/"ReactionStep" in a detailed PES network"""

    start_node: DetailNode
    end_node: DetailNode
    ts_node: DetailNode


# Coarse network elements
#   Each coarse network will connect species (or lumped species) comprising multiple
#   conformers
class CoarseNode(BaseModel):
    """A Node/"NetworkStage" in a lumped reaction network"""

    plural_species: list[LumpedSpecies]


class CoarseEdge(BaseModel):
    """An Edge/"ReactionStep" in a detailed PES network"""

    start_node: DetailNode
    end_node: DetailNode
    ts_node: DetailNode


# Full Schema
class Schema(BaseModel):
    """The final schema, encapsulating all information"""

    schema_version: Literal["1.0.0b0"]
    """value of this field is used to determine which version of the schema to
    validate against
    """


if __name__ == "__main__":
    schema = Schema.model_json_schema()  # (1)!
    print(json.dumps(schema, indent=2))  # (2)!
