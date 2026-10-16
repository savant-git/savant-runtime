from __future__ import annotations

from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


class OntologyRuntime:

    def __init__(self):
        self.entities = {
            entity.id: entity
            for entity in discover_entities()
        }

    def get(self, entity_id):
        return self.entities.get(entity_id)

    def all(self):
        return list(self.entities.values())

    def by_type(self, entity_type):
        return [
            entity
            for entity in self.entities.values()
            if entity.type == entity_type
        ]

    def exists(self, entity_id):
        return entity_id in self.entities

    def path(self, entity_id):
        entity = self.get(entity_id)
        if entity:
            return Path(entity.path)
        return None


runtime = OntologyRuntime()
