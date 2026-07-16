# Contributing Guidelines

Thank you for taking the time to contribute to this project.

## Tell Us About Your Data, Report Bugs & Request Features

If you encounter any issues or have suggestions for new features, please create an issue:

- Clearly describe the bug or feature request.
- Check if the issue has already been reported or requested before submitting a new one.

## Code Contribution & Review Process

Issues marked as `help-wanted` are open for contribution.
Please let us know, if you are interessted in working on an issue so that we can coordinate the work.

> [!NOTE]
> Details regarding decision-making and review processes are still to be determined. We encourage open discussions around design choices.


## Linting & Formatting

Linting and formatting is done with [ruff](https://docs.astral.sh/ruff/) using [pre-commit](https://pre-commit.com/) hooks.
This will auto-format your code to adhere to a consistent standard, so that you do not
have to think much about things like whitespace and line length.
If you have the `dev` dependencies installed, you can run these pre-commit hooks as follows.
```
pre-commit run --all-files
```
If you are using the Pixi environment, you can also do `pixi run -e dev lint` (or just `pixi run lint` inside the dev environment).

Since the format check also auto-formats your code, you should see a green check mark
for the format if you run it a second time.

These hooks are also run with GitHub Actions, so make sure they pass locally before submitting a PR.

## Testing & Examples

We are using [pytest](https://docs.pytest.org/en/7.4.x/) to test the schema and API.
Simply run `pytest` in the root directory to run all tests.
Tests are also run automatically on GitHub Actions for each pull request.

There are three ways to add tests:

1. Create an `examples/` file: All files in the `examples/` directory are automatically tested against the schema. You can add new examples to this directory to test your changes.
2. Add a yaml file to `tests/rmmd`: In contrast to files in the `examples/` directory, these files can be used to test specific parts of the schema and allow testing of expected validation errors for invalid files. Each yaml file in this directory must include a metadata block at the beginning that describes the test and specifies, if and how validation should fail.
3. Add a [pytest `test_*.py` file](https://docs.pytest.org/en/stable/getting-started.html#create-your-first-test) in `tests/rmmd`: These files can be used to write more complex tests that require Python code, i.e., if you want to test parts of the Python API.


> [!TIP]
> It may be easier to start with test/example files first to understand how the schema will be used before writing the Pydantic model.

## Conventions

### General Guidelines

- Use [Sphinx-style](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html) docstrings for all public methods and classes.
- Other specific standards for this project will be spelled out in this document.
- Otherwise, please rely on the `pre-commit` formatting and linting hooks described
above. The [Ruff](https://docs.astral.sh/ruff/) format imposed by these hooks is broadly
consistent with the [PEP8 Style Guide](https://peps.python.org/pep-0008/), which may be
worth consulting if you are new to Python.

### Units

*These rules will change with #37*

The schema models both molecular and macroscopic quantities, so be cautious about units:
- Document units in square brackets within the docstring of a field.
- **Molecular quantities** should use these units:

    | Quantity    | Unit        |
    |-------------|-------------|
    | length      | Ångström    |
    | temperature  | Kelvin      |
    | mass        | a.m.u.     |
    | energy      | Hartree     |
    | time        | femtosecond  |
    | charge      | electron charge (proton: +1) |

> [!NOTE]
> While these units are commonly used in quantum chemistry software inputs/outputs, they do not form a consistent system of units!

- Modules dealing with **macroscopic thermodynamics** (thermochemistry, etc.) should adhere strictly to **SI units**.

### Naming Conventions

- Field names for (literature) references: References for related literature that describes the data (e.g., associated papers) should be called `references` whereas references that give the source for some data should be called `sources`. Both have type `list[CitationKey]`
- Base model names intended not for direct use should start with an underscore and end with `Base`, e.g., `_ThermoPropertyBase`.
- ...

## Design Principles

Here are some guiding principles for design:

- Prefer using `Literal["unknown"]` and `Literal["not-needed"]` over `None` to minimize ambiguity.
- Steer clear of hierarchical structures for models that may be related in a many to many realtion to other models. Instead:
    1. Define a key for identifying a specific instance of the model in a dataset (e.g., `SpeciesName = Annotated[str, Field(pattern="^[a-zA-Z][a-zA-Z0-9-+*()]*$")]`).
    2. The base schema should get a dictionary of all such objects (e.g., `species: dict[SpeciesName, Species]`)
    3. Whenever another object is connected to your object use the key instead of the object itself (e.g., `reactants: list[SpeciesName]` not ~~`reactants: list[Species]`~~)
- When a model X only has a single one-to-one or one-to-many realtionship to another model Y, they may be nested hierarchically, i.e., a field of Y has type X (without using keys).
- Favor the [annotated pattern](https://docs.pydantic.dev/latest/concepts/fields/#the-annotated-pattern) over `f: <type> = pydantic.Field(...)`.
- Add comments on your design decisions — describe **why** something was done **rather than** just **what** was done.
- Define units precisely for numerical values; avoid leaving unit choice up to users/data suppliers (e.g., do not add a unit field next to a value field).
