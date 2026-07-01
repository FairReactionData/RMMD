"""
Citation-related metadata
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Self, TypeAlias

from annotated_types import MinLen
from pydantic import (
    AnyUrl,
    Discriminator,
    Field,
    Tag,
    UrlConstraints,
    model_validator,
)

from ._base import RmmdBaseModel
from .keys import CitationKey
from .cff.cff_1_2_0 import Doi as CffDoi
from .cff.cff_1_2_0 import Entity, License, Person, Reference

Doi: TypeAlias = CffDoi
"""Digital Object Identifier (DOI) for a publication or dataset.

DOIs should always be supplied in the form prefix/suffix to ensure consistency in how
DOIs are represented.
"""


# The pydantic CFF Url is just AnyUrl (althought in the JSON schema, only http(s) and
# (s)ftp are allowed. Here, we also require a host allowing us to check for DOIs which
# should not be supplied as URLs. Relevant b/c there is a union of Url and Doi below
class UrlNoDoiOrg(AnyUrl):
    """http or https URL, but not allowing www.doi.org or doi.org URLs."""

    _constraints = UrlConstraints(
        # URL schemes allowed by CFF 1.2.0
        allowed_schemes=["http", "https", "ftp", "sftp"],
        max_length=2083,
        # host required, other constraints same as pydantic.HttpUrl
        host_required=True,
    )

    @model_validator(mode="after")
    def check_if_consistent_doi_or_handle(self) -> Self:
        """Ensure that the URL is not an invalid (i.e. non-consistent)
        HandleNet identifier or DOI."""

        # try to catch some common "mistakes" to ensure consistency in how DOIs
        # and HandleNet identifiers are represented
        # We use the citation file format representation of DOIs
        if self.host in ("www.doi.org", "doi.org"):
            raise ValueError(
                "DOIs be provided as prefix/suffix not as www.doi.org URLs"
            )

        return self


LocalFile = Annotated[
    str,
    Field(
        examples=["./data/caffeine.xyz"],
        pattern=r"^\.\/.*",
    ),
]
"""Reference to a local file in the same dataset as the RMMD file.
The reference is given as a Posix-style path relative to the RMMD file,
starting with './'."""

LocalCffFile = Annotated[
    LocalFile,
    Field(
        examples=["./CITATION.cff"],
        pattern=r"^\.\/(.*\/)?CITATION\.cff$",
    ),
]
"""Reference to a local CITATION.cff file in the same dataset as the RMMD file.

The reference is given as a Posix-style path relative to the RMMD file,
starting with './' and ending with 'CITATION.cff'.
"""


class Metadata(RmmdBaseModel):
    """Metadata for the dataset, e.g., authors, title, description, etc.

    This structure is very close to a CITATION.CFF file to allow for easy conversion.
    """

    license: License
    """license of this dataset"""
    authors: list[Person | Entity] = Field(default_factory=list)
    """authors of the dataset"""
    title: Annotated[str, MinLen(1)]
    """name of the dataset"""
    description: Annotated[str, MinLen(1)] | None = None
    """description or abstract of the dataset, e.g., how it was obtained, what it contains, ..."""
    keywords: list[str] = Field(default_factory=list)
    """keywords for the dataset"""
    version: Annotated[str, MinLen(1)] | None = None
    """version of the dataset"""
    date_released: date | None = None
    """date when the dataset was released"""
    identifiers: list[str] | None = None
    """identifiers for the dataset, e.g., DOI."""
    preferred_citation: Reference | None = None
    """how this dataset should be cited"""
    references: list[CitationKeyOrDirectReference] | None = None
    """literature describing this dataset, typically the paper(s) associated with the
    dataset.
    """


def _direct_reference_discriminator(v) -> str | None:
    """Discriminator function for direct references."""
    v = str(v)  # ensure v is a string (e.g., for AnyUrl)

    if v.startswith("10.") and "/" in v:  # a citation key cannot contain /
        return "Doi"
    elif (
        v.startswith("http://")
        or v.startswith("https://")
        or v.startswith("ftp://")
        or v.startswith("sftp://")
    ):
        return "HttpUrlHostRequired"
    elif v.startswith("./"):
        return "LocalFile"
    else:
        return "CitationKey"


CitationKeyOrDirectReference = Annotated[
    Annotated[Doi, Tag("Doi")]
    | Annotated[UrlNoDoiOrg, Tag("HttpUrlHostRequired")]
    | Annotated[LocalFile, Tag("LocalFile")]
    | Annotated[CitationKey, Tag("CitationKey")],
    Discriminator(
        _direct_reference_discriminator,
        custom_error_type="illegal_direct_reference",
        custom_error_message="Could not determine the type of direct "
        "reference. Valid direct references include DOIs,"
        " HTTP URLs, relative file paths, or citation keys.",
    ),
]
"""String that either identifies a resource directly (e.g. a URL string) or is a key to
the literature table in the schema.
"""
