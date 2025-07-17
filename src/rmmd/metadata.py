"""
Citation-related metadata
"""

from typing import Annotated
from pydantic import (
    AfterValidator,
    AnyUrl,
    BaseModel,
    Discriminator,
    Field,
    RootModel,
    Tag,
    UrlConstraints,
)
from .keys import CitationKey

# Note: In order to use CitationKeyOrDirectReference (below), any direct
# reference needs to be distinguishable from a citation key, i.e., it must not
# match the pattern of a citation key!

Doi = Annotated[
    str,
    Field(
        description="Digital Object Identifier (DOI)",
        pattern=r"^https:\/\/doi\.org\/10\.\d{4,}/.*",
    ),
]
"""Digital Object Identifier (DOI) for a publication or dataset.

DOIs should always be supplied as full URLs. This allows for easy resolution
and ensures consistency in how DOIs are represented."""

HandleNet = Annotated[
    str,
    Field(
        description="HandleNet identifier for a publication or dataset.",
        pattern=r"^https:\/\/hdl\.handle\.net\/(?:1(?:[^0].*|0[^.].*)|[^1].*)\/.*",
    ),
]
"""HandleNet identifier for a publication or dataset represented as URL.

While DOIs are technically a subset of HandleNet identifiers, they should use
the doi.org domain to keep consistency.
"""


def check_if_consistent_doi_or_handle(url: AnyUrl) -> AnyUrl:
    """Ensure that the URL is not an invalid (i.e. non-consistent)
    HandleNet identifier or DOI."""

    # try to catch some common "mistakes" to ensure consistency in how DOIs
    # and HandleNet identifiers are represented
    if url.host == "www.doi.org":
        raise ValueError("DOIs should follow the format https://doi.org/10.xxxx/... ")
    elif url.host == "doi.org" and url.scheme != "https":
        raise ValueError("DOIs should be provided as full URLs starting with https")
    elif url.host == "hdl.handle.net" and url.scheme != "https":
        raise ValueError(
            "HandleNet identifiers should be provided as full URLs "
            "starting with https://hdl.handle.net/..."
        )

    return url


class _HttpUrlHostRequired(AnyUrl):
    """HTTP URL with a required host."""

    _constraints = UrlConstraints(
        allowed_schemes=["http", "https"],
        host_required=True,
    )


HttpUrlReference = Annotated[
    _HttpUrlHostRequired, AfterValidator(check_if_consistent_doi_or_handle)
]
"""HTTP URL for a publication or dataset.

This is used for references that are not DOIs or HandleNet identifiers,
such as web pages or other online resources.
"""


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


class Citation(BaseModel):
    """Classic citation/reference using author, title, journal, etc."""

    title: Annotated[str, Field(min_length=1)]

    # TODO adapt from CFF, datacite, ...; do not reinvent the wheel
    authors: list[str]
    doi: Doi


Reference = Doi | HttpUrlReference | Citation
"""Reference to a publication or dataset."""


def _direct_reference_discriminator(v) -> str | None:
    """Discriminator function for direct references."""
    v = str(v)  # ensure v is a string (e.g., for AnyUrl)

    if v.startswith("https://doi.org"):
        return "Doi"
    elif v.startswith("https://hdl.handle.net/"):
        return "HandleNet"
    elif v.startswith("http://") or v.startswith("https://"):
        return "HttpUrlReference"
    elif v.startswith("./"):
        return "LocalFile"
    else:
        return None


DirectReference = Annotated[
    Annotated[Doi, Tag("Doi")]
    | Annotated[HandleNet, Tag("HandleNet")]
    | Annotated[HttpUrlReference, Tag("HttpUrlReference")]
    | Annotated[LocalFile, Tag("LocalFile")],
    Discriminator(
        _direct_reference_discriminator,
        custom_error_type="illegal_direct_reference",
        custom_error_message="Could not determine the type of direct "
        "reference. Valid direct references include DOIs,"
        " HandleNet identifiers, HTTP URLs, or relative"
        " file paths.",
    ),
]
"""Types of references that are strings and can be used directly in the
schema without adding a reference item to the literature table and using its citation key."""

CitationKeyOrDirectReference = DirectReference | CitationKey
"""String type that either identifies a reference directly or is a key to the
literature table in the schema."""


class _DirectReferenceTest(RootModel[list[DirectReference]]):
    """Used in a test case to define different valid and invalid direct
    references."""
