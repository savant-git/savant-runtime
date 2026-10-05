from __future__ import annotations

from ENTITY_DISCOVERY import discover_entities


def search(text):

    text = text.lower()

    return [
        entity
        for entity in discover_entities()
        if text in entity.id.lower()
        or text in entity.type.lower()
        or text in entity.path.lower()
    ]
