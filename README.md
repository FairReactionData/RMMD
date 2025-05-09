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

Please check the [contribution guidelines](CONTRIBUTING.md) for more details
