from pathlib import Path

import yaml
import pytest
from pydantic import BaseModel

import importlib


HERE = Path(__file__).parent.resolve()
EXAMPLES_DIR = HERE.parent / "examples"


class ExampleMetadata(BaseModel):
    """specification of the metadata block of the examples"""
    failure: str|None
    description: str|None = None
    schema_part: str = "schema.Schema"  # complete schema by default
    relative_path: Path
    """path to the example file relative to the examples directory"""


###############################################################################
# example collection
###############################################################################

def _list_all_example_files():
    valid_example_files = []
    for path in EXAMPLES_DIR.rglob("*"):
        if path.is_file():
            valid_example_files.append(path)
    return valid_example_files

_valid_examples = {  # will be filled later
    "argvalues": [],    # test data + schema
    "ids": [],          # test names
}

_invalid_examples = {  # will be filled later
    "argvalues": [],    # test data + schema
    "ids": [],          # test names
}

def _import_module(name: str) -> type[BaseModel]:
    """Get a model by its name"""
    parts = name.split(".")
    class_name = parts[-1]
    module_name =  ".".join(["rmess"] + parts[:-1])

    module = importlib.import_module(module_name)
    model = getattr(module, class_name)

    assert issubclass(model, BaseModel)

    return model

def _load_examples():
    """fills the global variables _valid_examples and _invalid_examples
    with the test data from the example files
    """
    global _valid_examples, _invalid_examples

    example_files = _list_all_example_files()

    for file in example_files:
        with open(file, "rb") as f:
            content = yaml.safe_load_all(f)
            content = [block for block in content]  # convert generator to list

        metadata = ExampleMetadata(
                        **content[0],
                        relative_path=file.relative_to(EXAMPLES_DIR)
        )
        data = content[1]
        schema = _import_module(metadata.schema_part)

        id = f"{metadata.relative_path}"

        if metadata.failure is None:
            _valid_examples["argvalues"].append((data, schema))
            _valid_examples["ids"].append(id)
        else:
            _invalid_examples["argvalues"].append((data, schema,
                                                    metadata.failure))
            _invalid_examples["ids"].append(id)


_load_examples()


###############################################################################
# tests
###############################################################################

@pytest.mark.parametrize("data, schema", **_valid_examples) # type: ignore
def test_valid_examples(data: dict, schema: BaseModel):
    """Test that valid examples pass validation"""

    print(schema)
    schema.model_validate(data)

@pytest.mark.parametrize("data, schema, error", **_invalid_examples) # type: ignore
def test_invalid_examples(data: dict, schema: BaseModel, error: str):
    """Test that invalid examples raise the expected validation errors"""

    with pytest.raises(ValueError, match=error):
        schema.model_validate(data)