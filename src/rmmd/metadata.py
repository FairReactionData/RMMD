"""
Citation-related metadata
"""

from typing import Annotated
from pydantic import AnyHttpUrl, BaseModel, Field


Doi = Annotated[str, Field(description="Digital Object Identifier (DOI)",
                           pattern=r"^10.\d{4,9}/.*",
                           )]
HttpUrl = AnyHttpUrl

LocalFile = Annotated[str, Field(description="Reference to a file in the same dataset as the RMMD file. The reference is given as Posix style path relative to the RMMD file starting with './'.",
                                examples=["./data/caffeine.xyz"],
                                pattern=r"^\.\/.*",
                                )]

class Citation(BaseModel):

    title: Annotated[str, Field(min_length=1)]

    # TODO adapt from CFF, datacite, ...; do not reinvent the wheel
    authors: list[str]
    doi: Doi

Reference = Doi|HttpUrl|Citation
