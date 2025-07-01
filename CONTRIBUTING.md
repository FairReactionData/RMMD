# Contributing Guidelines

Thank you for taking the time to contribute to this project.

## Reporting Bugs & Requesting Features

If you encounter any issues or have suggestions for new features, please create an issue:

- Clearly describe the bug or feature request.
- Check if the issue has already been reported or requested before submitting a new one.

## Code Contribution & Review Process

To know which work packages are open for contribution, please refer to our issue tracker. Contributions can be discussed and prioritized within our team.

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

Testing is crucial for maintaining quality across all parts of the schema. We utilize example YAML files located in the `examples/` directory to test the schema. You simply need to run pytest to test the example files. These example files also serve as documentation during this early stage of development.
So, when adding new models/classes, please add corresponding tests/examples.

> [!TIP]
> It may be easier to start with test/example files first to understand how the schema will be used before writing the Pydantic model.

For each example file, include a metadata block at the beginning that describes the test and specifies, if and how validation should fail.
Expected validation errors are provided as a list of pairs of strings called failures:

``` yaml
--- # test setup
description: "Here, one can describe the test"
failures:   # expected failures can be provided as a tuple of a location in the
            # data and a regular expression that matches the expected error
            # message
  - ["species.CH4.entities", "List should have at least 1 item after validation, not 0"]
--- # begin of the actual example
schema_version: 0.1.0b0
license: MIT
species:
  CH4:
    name: CH4
    entities: []  # empty list is not allowed  (see expected error above)
```

## Conventions

### General Guidelines

- Use [Sphinx-style](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html) docstrings for all public methods and classes.
- Other specific standards for this project will be spelled out in this document.
- Otherwise, please rely on the `pre-commit` formatting and linting hooks described
above. The [Ruff](https://docs.astral.sh/ruff/) format imposed by these hooks is broadly
consistent with the [PEP8 Style Guide](https://peps.python.org/pep-0008/), which may be
worth consulting if you are new to Python.

### Units

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

- Field names for (literature) references: References for related literature that describes the data (e.g., associated papers) should be called `references` whereas references that give the source for some data should be called `source`. Both have type `list[CitationKey]`
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
