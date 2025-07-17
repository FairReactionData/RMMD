"""Module containing helper functions for testing."""

import re
from typing import Any, Self
from pydantic import BaseModel, ValidationError, model_validator
from pydantic_core import ErrorDetails
import pytest


def _err_loc_str(loc: tuple[str | int, ...]) -> str:
    """Convert a location tuple to a string"""
    loc_str = loc[0] if isinstance(loc[0], str) else f"[{loc[0]}]"

    for loc_entry in loc[1:]:
        if isinstance(loc_entry, int):
            loc_str += f"[{loc_entry}]"
        else:
            loc_str += f".{loc_entry}"

    return loc_str


class ExpectedError(BaseModel):
    """Expected validation error for a model validation test."""

    loc: tuple[str | int, ...]
    """Location of the error in the data structure."""
    msg: str | None = None
    """Expected error message.

    Either msg or msg_pattern must be provided."""
    msg_pattern: str | None = None
    """regex pattern to match against the error message.

    Either msg or msg_pattern must be provided."""

    @model_validator(mode="after")
    def check_either_msg_or_pattern_existing(self) -> Self:
        """Ensure that either msg or msg_pattern is provided."""
        if self.msg is None != self.msg_pattern is None:
            raise ValueError(
                "Either 'msg' or 'msg_pattern' must be provided, but not both."
            )
        return self

    class Config:
        """Pydantic configuration."""

        extra = "forbid"  # forbid additional fields
        frozen = True  # make instances immutable

    def is_equivalent_to_error(self, error: ErrorDetails) -> bool:
        """Check if this expected error is equivalent to the given error."""
        if self.loc != tuple(error["loc"]):
            return False

        if self.msg and self.msg != error["msg"]:
            return False

        if self.msg_pattern and not re.match(self.msg_pattern, error["msg"]):
            return False

        return True


def assert_model_validation_errors(
    model: type[BaseModel], data: Any, expected_errors: list[ExpectedError]
):
    """Assert that the model validation raises the expected errors.

    :param model: The Pydantic model to validate against.
    :param data: The data to validate.
    :param expected_errors: A list of tuples where each tuple contains a
                            location (as a tuple of strings or integers) and a
                            regex pattern for the expected error message.
    """
    msg = ""
    # encountered ids will be removed from this set:
    unencountered_expected_errids = {i for i in range(len(expected_errors))}

    try:
        model.model_validate(data)
    except ValidationError as val_err:
        actual_errors = val_err.errors()
        # ids of actual errors that were not expected
        unexpected_actual_errids = {i for i in range(len(actual_errors))}

        for i_expected, expected_err in enumerate(expected_errors):
            for i_actual, actual_err in enumerate(actual_errors):
                if expected_err.is_equivalent_to_error(actual_err):
                    # expected error was encountered
                    unencountered_expected_errids.discard(i_expected)
                    unexpected_actual_errids.discard(i_actual)

        if unexpected_actual_errids:
            msg += "Unexpected error(s):\n"
            for i in unexpected_actual_errids:
                actual_err = actual_errors[i]
                loc = actual_err["loc"]
                errmsg = actual_err["msg"]

                if loc:
                    msg += f"    {_err_loc_str(loc)}: {errmsg}\n"
                else:
                    msg += f"    {errmsg}\n"

    if unencountered_expected_errids:
        msg += "Expected error(s) missing:\n"
        for i in unencountered_expected_errids:
            expected_err = expected_errors[i]
            loc = expected_err.loc
            errpattern = expected_err.msg_pattern or expected_err.msg

            if loc:
                msg += f"    {_err_loc_str(loc)}: {errpattern}\n"
            else:
                msg += f"    {errpattern}\n"

    if msg:
        pytest.fail(msg)
