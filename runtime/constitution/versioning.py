from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, order=True)
class SemanticVersion:
    major: int; minor: int; patch: int
    @classmethod
    def parse(cls, value: str) -> "SemanticVersion":
        parts = value.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts): raise ValueError(f"invalid semantic version: {value}")
        return cls(*(int(p) for p in parts))
    def __str__(self) -> str: return f"{self.major}.{self.minor}.{self.patch}"

@dataclass(frozen=True)
class ConstitutionalVersions:
    schema: SemanticVersion; ontology: SemanticVersion; projection: SemanticVersion; authority: SemanticVersion; migration: SemanticVersion
