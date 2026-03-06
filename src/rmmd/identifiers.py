"""Identifiers for molecular entities and species."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import BaseModel, Field, model_validator
from rdkit.Chem import (
    MolBlockToInchi,
    MolFromInchi,
    MolFromSmiles,
    MolToMolBlock,
    MolToSmiles,
)


class _StringIdentifierBase(BaseModel, ABC):
    """Base class for string identifiers with a type field."""

    type: str
    value: str


class _ValidationStrategyMixin(ABC):
    """Base class for string identifiers with a type field."""

    type: str
    value: str
    validation_strategy: Literal["quick", "full", "recalculate"] = "quick"

    @model_validator(mode="after")
    def validate_string_identifier(self) -> Self:
        """Validate string identifier value."""
        if self.validation_strategy == "quick":
            self.quick_validate()
        elif self.validation_strategy == "recalculate":
            self.value = self.recalculate()
        elif self.validation_strategy == "full":
            self.full_validate()
        return self

    def quick_validate(self) -> None:
        """Validate string identifier value (quick)."""
        pass

    @abstractmethod
    def recalculate(self) -> str:
        """Recalculate string identifier value (no validation)."""
        msg = f"Recalculation is not implemented for type {self.type}"
        raise NotImplementedError(msg)

    def full_validate(self) -> None:
        """Validate string identifier value (full)."""
        try:
            recalculated_value = self.recalculate()
        except NotImplementedError:
            msg = f"Full validation is not implemented for type {self.type}"
            raise NotImplementedError(msg)

        if not recalculated_value == self.value:
            msg = (
                f"Recalculated {self.type} does not match:\n"
                f"original:     {self.value}\n"
                f"recalculated: {recalculated_value}\n"
            )
            raise ValueError(msg)


class _StandardInChI(_StringIdentifierBase, _ValidationStrategyMixin):
    """Standard IUPAC International Chemical Identifier"""

    type: Literal["InChI"] = "InChI"

    def quick_validate(self) -> None:
        """Validate string identifier value (quick)."""
        if not self.value.startswith("InChI=1S/"):
            msg = f"{self.type} is missing expected prefix 'InChI=1S/': {self.value}"
            raise ValueError(msg)

    def recalculate(self) -> str:
        """Recalculate string identifier value (no validation)."""
        mol = MolFromInchi(self.value)
        mol_block = MolToMolBlock(mol)
        return MolBlockToInchi(mol_block)  # type: ignore


class _FixedHInChI(_StringIdentifierBase, _ValidationStrategyMixin):
    """IUPAC International Chemical Identifier generated with the fixed-H layer."""

    type: Literal["InChI-fixedH"] = "InChI-fixedH"

    def quick_validate(self) -> None:
        """Validate string identifier value (quick)."""
        if not self.value.startswith("InChI=1/"):
            msg = f"{self.type} is missing expected prefix 'InChI=1/': {self.value}"
            raise ValueError(msg)

    def recalculate(self) -> str:
        """Recalculate string identifier value (no validation)."""
        mol = MolFromInchi(self.value)
        mol_block = MolToMolBlock(mol)
        return MolBlockToInchi(mol_block, options="-FixedH")  # type: ignore


class _StandardInChIKey(_StringIdentifierBase):
    """Standard IUPAC International Chemical Identifier Key"""

    type: Literal["InChIKey"]
    value: Annotated[
        str,
        Field(
            pattern="^[A-Z]{14}-[A-Z]{8}SA-[A-Z]$",
        ),
    ]


class _SMILES(_StringIdentifierBase, _ValidationStrategyMixin):
    """Simplified Molecular Input Line Entry System"""

    type: Literal["SMILES"] = "SMILES"

    def recalculate(self) -> str:
        """Recalculate string identifier value (no validation)."""
        mol = MolFromSmiles(self.value)
        return MolToSmiles(mol)


class _CustomStringIdentifier(_StringIdentifierBase):
    """Custom string identifier with a type field."""

    type: Literal["custom"]
    label: str


StringIdentifier: TypeAlias = Annotated[
    _StandardInChI
    | _SMILES
    | _CustomStringIdentifier
    | _FixedHInChI
    | _StandardInChIKey,
    Field(discriminator="type"),
]
"""string identifier for a molecular entity"""


class _StringIdentifierTest(BaseModel):
    """class for testing the Geometry and Geometries classes"""

    string_identifier_list: list[StringIdentifier]
