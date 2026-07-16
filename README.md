# Reaction Model MetaData (RMMD)

... is a YAML-based file format and schema (i.e. a standardized data structure) designed to help researchers add meaningful and detailed metadata to their reaction models.
An RMMD file can contain thermochemistry, transport and rate constant model parameters similar to a CHEMKIN file, but also molecular geometries and frequencies from quantum chemistry calculations.
Additionally, RMMD files contain [data provenance](https://en.wikipedia.org/wiki/Data_lineage#Data_provenance) as well as general metadata about the dataset (author, title, license, ...).
RMMD should help researchers to publish their reaction model data in a [FAIR](https://doi.org/10.1038/sdata.2016.18) way.

## Challenges With Common Publication Practices

In the past decades, researchers have produced a lot of reaction models[^rm-def] but often without relevant metadata.
The emergence of automated tools for reaction model generation (e.g, RMG, Kinbot, ChemTraYzer, ...) has lead to the production and publication of even more data.
The models are usually provided as SI to papers or uploaded to public repositories as Chemkin or Cantera YAML files.
However, the principal goal of these file formats was not the publication of data in a FAIR way (findable, accessible, interoperable and reusable) but rather to be used as input files for simulation codes.
In practice this means that there are a bunch of problems other researchers can run into when trying to build upon this data:

- No canonical IDs: Species and reactions are usually identified by names such as "CHFCHCF3", which are not always sufficient to identify the intended chemical species, sometimes not even by reading the associated publication.
- Missing provenance: As it is not uncommon to use parametrization from other mechanisms, it is not always clear, where a specific parameters originally came from, what method was used or how they were changed over different publications.
- Findability: Even if someone already determined accurate parameters for a species or reaction you are interested in, it can be hard to find that data and the associated publication, e.g., when a mechanism includes data on a reaction intermediate whose IUPAC name is not mentioned in the publication.
- Many more: missing data usage license, different thermodynamic reference states, unpublished associated data, ...

[^rm-def]: Here, a reaction model is considered the set of reactions, species and model parameters for kinetics, material transport and thermochemistry typically distributed in a single file.

### A Metadata Schema as Part of the Solution

Some FAIR principles can be implemented fairly <!-- ;) --> easily, e.g., by adding a data usage license to one's model and uploading the model to a platform that provides DOIs.

The above named problems, however, require the model creator to add additional information that is specific to the domain of reaction-modeling or chemistry (["rich" metadata](https://www.go-fair.org/fair-principles/r1-metadata-richly-described-plurality-accurate-relevant-attributes/)), e.g., a canonical species identifier .
For this rich metadata to be really useful to others, it needs to be machine readable which requires a standardized way of supplying this kind of data.
This is where a metadata schema like RMMD comes into play.
Since we could not find a suitable schema, e.g., on [https://fairsharing.org/](https://fairsharing.org/) or in the [Metadata Standards Catalog](https://rdamsc.bath.ac.uk/) we started developing a new one.

## Current Status & Contributing

Since RMMD has not yet been officially released and is under development, the schema is still subject to breaking changes.
The version number `0.1.0b0` is used for different versions of the schema during early development.[^note-0.0.1]
With the release of the first version, each new release will get a new version number.
Then you can rely on the `schema_version` field in each RMMD file to indicate the exact schema used.

[^note-0.0.1]: Version 0.0.1 that you may find online was an early prototype by some of the authors of this repository. It was superseded by this version of RMMD and is not compatible with it.

**So, what can I currently do with RMMD?**

You can become a contributor!
The challenge in designing RMMD is to make it fit the needs of the community. Therefore, we need the perspective of different researchers and their use cases.
Let us know what kind of data you want to share FAIRly or try to create an RMMD file for your own data and let us know what you think about the schema.
The easiest way to do this is to create an issue in this repository and describe your use case or the problems you ran into.

You can also contribute to the development. Check out issues labeled with `good first issue` or `help wanted` and see if you can help us out.
Please check out the [contribution guidelines](CONTRIBUTING.md) for more details.


### Understanding the Schema

When trying to understand the schema, it may be helpful to check out the [example files](examples/) and compare them to the models in [src/rmmd/](src/rmmd/).

The "entry point" of the schema is the `Schema` model in  [schema.py](src/rmmd/schema.py).
It defines the root of an RMMD file and specifies collections ("registries") of different models such as `Species` or `MolecularEntity`.
Hence, a valid RMMD file contains collections of model instances at the root level.
These instances are referenced elsewhere by the id of the respective instance in the collections. In the case of a `MolecularEntity` its `EntityKey` is used to reference a specific entity. For example, the `Species` model defined in [species.py](src/rmmd/species.py) uses a list of `EntityKey`s to define a species as an ensemble of `MoleularEntity`s.

## Installing The Development Version

Clone this repository and install RMMD in a python environment.
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

