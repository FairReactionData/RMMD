from pathlib import Path

from rmmd import schema
from rmmd.test import assert_model_validation_errors
import yaml
import pytest

_HERE = Path(__file__).parent.resolve()
_EXAMPLES_DIR = _HERE.parent / "examples"


###############################################################################
# example collection
###############################################################################


def _list_all_example_files() -> list[Path]:
    example_files = []
    for path in _EXAMPLES_DIR.rglob("*"):
        if path.is_file():
            example_files.append(path)
    return example_files


_examples = {  # will be filled later
    "argvalues": [],  # test data + schema
    "ids": [],  # test names
}

_errors_during_setup: list[tuple[str, str]] = []
"""list of files that could not be loaded"""


def _load_examples():
    """fills the global variable _examples with the test data from the example
    files
    """
    global _examples

    example_files = _list_all_example_files()

    for file in example_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

        except (yaml.YAMLError, OSError) as err:
            _errors_during_setup.append((str(file), f"Could not read file: {err}"))
            continue

        _examples["argvalues"].append(data)
        _examples["ids"].append(str(file.relative_to(_EXAMPLES_DIR)))


_load_examples()

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


@pytest.mark.parametrize("data", **_examples)  # type: ignore
def test_examples(data: dict):
    """Test that invalid examples raise the expected validation errors"""
    assert_model_validation_errors(
        model=schema.Schema,
        data=data,
        expected_errors=[],  # no expected errors in the examples
    )
