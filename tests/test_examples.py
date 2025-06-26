from pathlib import Path
import re

import yaml
import pytest
from pydantic import BaseModel, Field, ValidationError

import importlib


HERE = Path(__file__).parent.resolve()
EXAMPLES_DIR = HERE.parent / "examples"


class ExampleMetadata(BaseModel):
    """specification of the metadata block of the examples"""

    model_config = {"extra": "forbid"}

    failures: list[tuple[str, str]] = Field(default_factory=list)
    """each item is an expected validation error, given as tuple of a string representing the location of the error and a message."""
    description: str|None = None
    schema_part: str = "schema.Schema"  # complete schema by default
    relative_path: Path
    """path to the example file relative to the examples directory"""


###############################################################################
# example collection
###############################################################################

def _list_all_example_files():
    example_files = []
    for path in EXAMPLES_DIR.rglob("*"):
        if path.is_file():
            example_files.append(path)
    return example_files


_examples = {           # will be filled later
    "argvalues": [],    # test data + schema
    "ids": [],          # test names
}

_errors_during_setup: list[tuple[str, str]] = []
"""list of files that could not be loaded"""

def _import_model(name: str) -> type[BaseModel]:
    """Get a model by its name"""
    parts = name.split(".")
    class_name = parts[-1]
    module_name =  ".".join(["rmmd"] + parts[:-1])

    module = importlib.import_module(module_name)
    model = getattr(module, class_name)

    assert issubclass(model, BaseModel)

    return model

def _load_examples():
    """fills the global variable _examples with the test data from the example
    files
    """
    global _examples

    example_files = _list_all_example_files()

    for file in example_files:
        try:
            with open(file, "rb") as f:
                content = yaml.safe_load_all(f)
                # convert generator to list
                content = [block for block in content]

        except (yaml.YAMLError, OSError) as err:
            _errors_during_setup.append(
                (file, f"Could not read file: {err}")
            )
            continue

        match len(content):
            case 0:
                _errors_during_setup.append(
                    (file, "File is empty or only contains comments. "
                           "Expected two blocks: metadata and data."))
                continue
            case 1:
                _errors_during_setup.append(
                    (file, "File contains only one block, expected two: "
                           "metadata and data."))
                continue
            case 2:
                pass
            case _:
                _errors_during_setup.append(
                    (file, "File contains more than two blocks, expected two: "
                           "metadata and data."))

        try:
            metadata = ExampleMetadata(
                            **content[0],
                            relative_path=file.relative_to(EXAMPLES_DIR)
            )
        except ValidationError as err:
            _errors_during_setup.append(
                (file, f"Metadata block is invalid: {err}")
            )
            continue
        data = content[1]

        try:
            model = _import_model(metadata.schema_part)
        except (ImportError, AttributeError) as err:
            _errors_during_setup.append(
                (file, f"Could not import model {metadata.schema_part}: {err}")
            )
            continue

        id = f"{metadata.relative_path}"

        _examples["argvalues"].append((data, model, metadata.failures))
        _examples["ids"].append(id)


_load_examples()


###############################################################################
# tests
###############################################################################

def test_test_setup():
    """Test that the setup was successful and all examples were loaded"""

    if _errors_during_setup:
        msg = "\n".join(
            [f"Error loading {file}: {error}"
             for file, error in _errors_during_setup]
        )
        raise RuntimeError(f"Errors during setup:\n{msg}")

def _err_loc_str(loc: tuple[str|int, ...]) -> str:
    """Convert a location tuple to a string"""
    return ".".join(str(e) for e in loc)

@pytest.mark.parametrize("data, schema, expected_errors",
                        **_examples) # type: ignore
def test_examples(data: dict, schema: BaseModel,
                  expected_errors: list[tuple[str, str]]):
    """Test that invalid examples raise the expected validation errors"""
    msg = ""
    # encountered ids will be removed from this set:
    unencountered_expected_errids = {i for i in range(len(expected_errors))}

    try:
        schema.model_validate(data)
    except ValidationError as val_err:
        actual_errors = [(_err_loc_str(err["loc"]), err["msg"])
                         for err in val_err.errors()]
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
                msg += f"    {loc}: {errmsg}\n"

    if unencountered_expected_errids:
        msg += "Expected error(s) missing:\n"
        for i in unencountered_expected_errids:
            loc, errpattern = expected_errors[i]
            msg += f"    {loc}: {errpattern}\n"

    if msg:
        pytest.fail(msg)
