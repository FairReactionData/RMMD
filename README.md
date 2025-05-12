# Reaction Model Metadata (RMMD)

A repository for drafting a schema for reaction model electronic structure data.

## Installing dependencies

If you have a preferred method of creating python environments, you can use the
`pyproject.toml` file to do so.
Otherwise, an easy way to create and activate a virtual environment is through
[Pixi](https://pixi.sh/latest/):
1. Install Pixi: `curl -fsSL https://pixi.sh/install.sh | bash`
2. Create virtual environment: `pixi install` (in this directory)
3. Activate virtual environment: `pixi shell` (in this directory)

## Validating a file

After installation run `rmmd validate my_file.yaml` to validate a file against
the RMMD schema.

## Contributing

Please check the [contribution guidelines](CONTRIBUTING.md) for more details.

### Understanding the Schema

When trying to understand the schema, it may be helpful to check out the [example files](examples/) and compare them to the models in [src/rmmd/](src/rmmd/).

The "entry point" of the schema is the `Schema` model in  [schema.py](src/rmmd/schema.py). It defines the root of an RMMD file and specifies collections of different models such as `Species` or `CanonicalEntity`.
Hence, a valid RMMD file contains collections of model instances at the root level.
These instances are referenced elsewhere by the id of the respective instance in the collections. In the case of a `CanonicalEntity` its `EntityKey` is used to reference a specific entity. For example, the `Species` model defined in [species.py](src/rmmd/species.py) uses a list of `EntityKey`s to define a species as an ensemble of `CanonicalEntity`s.