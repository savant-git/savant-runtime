"""Project existing Savant edifices into functional lineage."""

from .authority import (
    ingest_authority_document,
    ingest_authority_roots,
)

from .canon import (
    ingest_canon_system,
)

from .filesystem import (
    ingest_filesystem,
)

__all__ = [
    "ingest_authority_document",
    "ingest_authority_roots",
    "ingest_canon_system",
    "ingest_filesystem",
]
