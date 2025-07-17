from pathlib import Path
from typing import Any


from rmmd.test import ExpectedError, assert_model_validation_errors
import yaml
import pytest
from pydantic import BaseModel, Field, ValidationError

import importlib

_HERE = Path(__file__).parent.resolve()
"""directory of this file"""
_TEST_CASE_DIR = _HERE / "rmmd"


class ExampleMetadata(BaseModel):
    """specification of the metadata block of the test cases"""

    model_config = {"extra": "forbid"}

    failures: list[ExpectedError] = Field(default_factory=list)
    """each item is an expected validation error, given as tuple of a string representing the location of the error and a message."""
    description: str | None = None
    schema_part: str = "schema.Schema"  # complete schema by default
    relative_path: Path
    """path to the example file relative to the test case directory"""


###############################################################################
# test case collection
###############################################################################


def _list_test_files():
    example_files = []
    for path in _TEST_CASE_DIR.rglob("test_*.yaml"):
        if path.is_file():
            example_files.append(path)
    return example_files


_test_cases = {  # will be filled later
    "argvalues": [],  # test data + schema
    "ids": [],  # test names
}

_errors_during_setup: list[tuple[str, str]] = []
"""list of files that could not be loaded"""


def _import_model(name: str) -> type[BaseModel]:
    """Get a model by its name"""
    parts = name.split(".")
    class_name = parts[-1]
    module_name = ".".join(["rmmd"] + parts[:-1])

    module = importlib.import_module(module_name)
    model = getattr(module, class_name)

    assert issubclass(model, BaseModel)

    return model


def _load_test_cases():
    """fills the global variable _test_cases with the test data from the files
    in the _TEST_CASE_DIR directory
    """
    global _test_cases

    example_files = _list_test_files()

    for file in example_files:
        try:
            with open(file, "rb") as f:
                content = yaml.safe_load_all(f)
                # convert generator to list
                content = [block for block in content]

        except (yaml.YAMLError, OSError) as err:
            _errors_during_setup.append((file, f"Could not read file: {err}"))
            continue

        match len(content):
            case 0:
                _errors_during_setup.append(
                    (
                        file,
                        "File is empty or only contains comments. "
                        "Expected two blocks: metadata and data.",
                    )
                )
                continue
            case 1:
                _errors_during_setup.append(
                    (
                        file,
                        "File contains only one block, expected two: "
                        "metadata and data.",
                    )
                )
                continue
            case 2:
                pass
            case _:
                _errors_during_setup.append(
                    (
                        file,
                        "File contains more than two blocks, expected two: "
                        "metadata and data.",
                    )
                )

        try:
            metadata = ExampleMetadata(
                **content[0], relative_path=file.relative_to(_TEST_CASE_DIR)
            )
        except ValidationError as err:
            _errors_during_setup.append((file, f"Metadata block is invalid: {err}"))
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

        _test_cases["argvalues"].append((data, model, metadata.failures))
        _test_cases["ids"].append(id)


_load_test_cases()

###############################################################################
# tests
###############################################################################


def test_test_setup():
    """Test that the setup was successful and all examples were loaded"""

    if _errors_during_setup:
        msg = "\n".join(
            [f"Error loading {file}: {error}" for file, error in _errors_during_setup]
        )
        raise RuntimeError(f"Errors during setup:\n{msg}")


@pytest.mark.parametrize("data, schema, expected_errors", **_test_cases)  # type: ignore
def test_model_validation(data: Any, schema: type[BaseModel], expected_errors):
    """Test that invalid examples raise the expected validation errors"""
    assert_model_validation_errors(
        model=schema,
        data=data,
        expected_errors=expected_errors,
    )
