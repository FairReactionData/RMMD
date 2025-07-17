"""Module containing helper functions for testing."""


import re
from typing import Any
from pydantic import BaseModel, ValidationError
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

def assert_model_validation_errors(
        model: type[BaseModel],
        data: Any,
        expected_errors: list[tuple[tuple[str | int, ...], str]]):
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
        actual_errors = [
            (err["loc"], err["msg"]) for err in val_err.errors()
        ]
        # ids of actual errors that were not expected
        unexpected_actual_errids = {i for i in range(len(actual_errors))}

        for i_expected, (loc, msg_pattern) in enumerate(expected_errors):
            for i_actual, actual_err in enumerate(actual_errors):
                if loc == actual_err[0]:
                    if re.match(msg_pattern, actual_err[1]):
                        # expected error was encountered
                        unencountered_expected_errids.discard(i_expected)
                        unexpected_actual_errids.discard(i_actual)

        if unexpected_actual_errids:
            msg += "Unexpected error(s):\n"
            for i in unexpected_actual_errids:
                loc, errmsg = actual_errors[i]
                if loc:
                    msg += f"    {_err_loc_str(loc)}: {errmsg}\n"
                else:
                    msg += f"    {errmsg}\n"

    if unencountered_expected_errids:
        msg += "Expected error(s) missing:\n"
        for i in unencountered_expected_errids:
            loc, errpattern = expected_errors[i]
            if loc:
                msg += f"    {_err_loc_str(loc)}: {errpattern}\n"
            else:
                msg += f"    {errpattern}\n"

    if msg:
        pytest.fail(msg)