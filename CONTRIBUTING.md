- welcome note/table of content
    - this projects benefits from different perspectives...
    - we welcome contributions
    - still in start phase
- report bugs/request features
    - rules?
- code contribution/review process
    - how to know which work packages are open for contribution? -> ...
    - decision process for design: tbd
    - review process: tbd
    - what to consider:
        - see below
- testing/examples
    - all parts of the schema should be tested
    - we use example yaml files to test the schema -> in examples/ directory, these (along with docstrings) also serve as documentaiton in the early stage of development
    - add (to) tests/example for all new models/classes in the schema
        - tip: it may even be easier to start with the test/example files then write the pydantic model to think about how the schema is used first
    - for each example file add a metadata block to the beginning with a description of the test and if and how the validation should fail (see examples/minimal.yaml)
- conventions
    - Adhere to the [PEP8 Style Guide](https://peps.python.org/pep-0008/), if not otherwise in this document.
    - Use [Sphinx-style](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html) docstrings
    - units:
        - schema models molecular and macroscopic quntities -> be carful about units!
        - put units into docstrings in square brackets
        - - **Molecular quantities** should use the following unit:

            | Quantitiy | Unit |
            |---        |---   |
            | length    | Ångström |
            | temperature | Kelvin |
            | mass      | a.m.u. |
            | energy    | Hartree |
            | time      | femtosecond |
            | charge    | electron charge (proton: +1) |

            While these units are commonly used, e.g., in the input and output of quantum chemistry software, they do not constitute a consistent system of units!

        - Modules dealing with **macroscopic thermodynamics** (thermochemistry, ...) should use **SI units**
    - naming
        - related literature references vs. a reference to the dataset/..., e.g. "references"/"related_references" vs "data_references" vs "source"
        - models/classes meant as base models and not to be used directly should start with an underscore and end on `Base` , e.g., `_ThermoPropertyBase`
- design principles
    - try to avoid None/optional values? -> instead use `Literal["unkown"]` and `Literal["not-needed"]`
    - avoid hierarchical structure -> reason + how to do this consistently

        - use keys
    - prefer the [annotated pattern](https://docs.pydantic.dev/latest/concepts/fields/#the-annotated-pattern) over `f: <type> = pydantic.Field(...)`
    - comment design decisions; describe why you did something instead of what you did
    - units: Try to define the units for numerical values exactly and avoid leaving the choice of units to the user (e.g., do not add a unit field next to a value field so that the user/data supplier decided what the unit is) - also see units in conventions section (link)