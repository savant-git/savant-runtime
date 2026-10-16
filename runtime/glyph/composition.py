from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping, Sequence


SCHEMA = "savant://glyph/composition/1"


def _digest(parts: Iterable[str]) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class Glyph:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) != 1:
            raise ValueError(
                "a glyph must contain exactly one unicode code point"
            )

    @property
    def id(self) -> str:
        return f"glyph:{ord(self.value):x}"

    @property
    def digest(self) -> str:
        return _digest(
            (
                SCHEMA,
                "glyph",
                self.id,
                self.value,
            )
        )


@dataclass(frozen=True, slots=True)
class GlyphInstance:
    glyph_id: str
    ordinal: int

    def __post_init__(self) -> None:
        if not self.glyph_id:
            raise ValueError("glyph_id is required")
        if self.ordinal < 0:
            raise ValueError(
                "ordinal must be greater than or equal to zero"
            )

    @property
    def id(self) -> str:
        return (
            "glyph-instance:"
            + _digest(
                (
                    self.glyph_id,
                    str(self.ordinal),
                )
            )
        )


@dataclass(frozen=True, slots=True)
class CompositionInstance:
    target_id: str
    ordinal: int

    def __post_init__(self) -> None:
        if not self.target_id:
            raise ValueError("target_id is required")
        if self.ordinal < 0:
            raise ValueError(
                "ordinal must be greater than or equal to zero"
            )

    @property
    def id(self) -> str:
        return (
            "composition-instance:"
            + _digest(
                (
                    self.target_id,
                    str(self.ordinal),
                )
            )
        )


@dataclass(frozen=True, slots=True)
class TypedSegue:
    segue_type: str
    source_id: str
    target_id: str
    authority: str = "none"

    def __post_init__(self) -> None:
        if not self.segue_type:
            raise ValueError("segue_type is required")
        if not self.source_id:
            raise ValueError("source_id is required")
        if not self.target_id:
            raise ValueError("target_id is required")

    @property
    def id(self) -> str:
        return (
            "segue:"
            + _digest(
                (
                    self.segue_type,
                    self.source_id,
                    self.target_id,
                    self.authority,
                )
            )
        )


@dataclass(frozen=True, slots=True)
class Composition:
    kind: str
    members: tuple[GlyphInstance | CompositionInstance, ...]
    segues: tuple[TypedSegue, ...] = ()

    def __post_init__(self) -> None:
        if not self.kind:
            raise ValueError("kind is required")

    @property
    def structural_digest(self) -> str:
        parts = [
            SCHEMA,
            "composition",
            self.kind,
        ]

        for member in self.members:
            parts.extend(
                (
                    type(member).__name__,
                    member.id,
                )
            )

        for segue in self.segues:
            parts.extend(
                (
                    "segue",
                    segue.id,
                )
            )

        return _digest(parts)

    @property
    def id(self) -> str:
        return (
            f"composition:{self.kind}:"
            f"{self.structural_digest}"
        )


class GlyphRegistry:
    def __init__(self) -> None:
        self._glyphs: dict[str, Glyph] = {}

    def substantiate(self, value: str) -> Glyph:
        glyph = Glyph(value)
        existing = self._glyphs.get(glyph.id)

        if existing is not None:
            if existing.value != value:
                raise RuntimeError(
                    "canonical glyph identity collision"
                )
            return existing

        self._glyphs[glyph.id] = glyph
        return glyph

    def get(self, glyph_id: str) -> Glyph:
        return self._glyphs[glyph_id]

    def values(self) -> tuple[Glyph, ...]:
        return tuple(
            self._glyphs[key]
            for key in sorted(self._glyphs)
        )

    def decompose_text(
        self,
        text: str,
        *,
        kind: str = "text",
    ) -> Composition:
        members: list[GlyphInstance] = []

        for ordinal, value in enumerate(text):
            glyph = self.substantiate(value)
            members.append(
                GlyphInstance(
                    glyph_id=glyph.id,
                    ordinal=ordinal,
                )
            )

        return Composition(
            kind=kind,
            members=tuple(members),
        )

    def materialize(
        self,
        composition: Composition,
        *,
        compositions: Mapping[str, Composition] | None = None,
    ) -> str:
        composition_map = compositions or {}
        ordered = sorted(
            composition.members,
            key=lambda member: member.ordinal,
        )
        output: list[str] = []

        for member in ordered:
            if isinstance(member, GlyphInstance):
                output.append(
                    self.get(member.glyph_id).value
                )
                continue

            target = composition_map.get(
                member.target_id
            )

            if target is None:
                raise KeyError(
                    "missing referenced composition: "
                    + member.target_id
                )

            output.append(
                self.materialize(
                    target,
                    compositions=composition_map,
                )
            )

        return "".join(output)


def compose(
    kind: str,
    children: Sequence[Composition],
    *,
    segues: Sequence[TypedSegue] = (),
) -> tuple[Composition, dict[str, Composition]]:
    composition_map = {
        child.id: child
        for child in children
    }

    members = tuple(
        CompositionInstance(
            target_id=child.id,
            ordinal=ordinal,
        )
        for ordinal, child in enumerate(children)
    )

    parent = Composition(
        kind=kind,
        members=members,
        segues=tuple(segues),
    )

    composition_map[parent.id] = parent
    return parent, composition_map
