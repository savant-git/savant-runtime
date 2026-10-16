from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .projection import canonical_json


DIFF_FIELDS=("version","authority","relationships","dependencies","lineage")


@dataclass(frozen=True)
class ConstitutionalDiff:
    added: tuple[str,...]
    removed: tuple[str,...]
    changed: dict[str,tuple[dict[str,Any],...]]
    schemas: tuple[dict[str,Any],...]
    projections: tuple[dict[str,Any],...]
    migration_plan: tuple[dict[str,Any],...]
    def to_mapping(self): return {"added":self.added,"removed":self.removed,"changed":self.changed,
        "schemas":self.schemas,"projections":self.projections,"migration_plan":self.migration_plan}


class ConstitutionalDiffer:
    def compare(self,before: Any,after: Any) -> ConstitutionalDiff:
        left=set(before.ids); right=set(after.ids); common=sorted(left&right)
        changed={field:[] for field in DIFF_FIELDS}
        for identity in common:
            old=before.get(identity).to_primitives(); new=after.get(identity).to_primitives()
            for field in DIFF_FIELDS:
                if canonical_json(old[field])!=canonical_json(new[field]):
                    changed[field].append({"id":identity,"before":old[field],"after":new[field]})
        schema_ids=sorted(set(before.schemas.ids)|set(after.schemas.ids)); schema_changes=[]
        for identity in schema_ids:
            old=before.schemas.get(identity) if identity in before.schemas.ids else None
            new=after.schemas.get(identity) if identity in after.schemas.ids else None
            if canonical_json(old)!=canonical_json(new): schema_changes.append({"id":identity,"before":old,"after":new})
        projection_changes=[]
        for identity in common:
            old=before.projection_targets(identity); new=after.projection_targets(identity)
            if old!=new: projection_changes.append({"id":identity,"before":old,"after":new})
        plan=[]
        plan.extend({"action":"register","id":i} for i in sorted(right-left))
        for field in DIFF_FIELDS:
            plan.extend({"action":f"change_{field}","id":v["id"],"from":v["before"],"to":v["after"]} for v in changed[field])
        plan.extend({"action":"change_schema","id":v["id"],"from":v["before"],"to":v["after"]} for v in schema_changes)
        plan.extend({"action":"change_projection","id":v["id"],"from":v["before"],"to":v["after"]} for v in projection_changes)
        plan.extend({"action":"retire","id":i} for i in sorted(left-right))
        return ConstitutionalDiff(tuple(sorted(right-left)),tuple(sorted(left-right)),
            {k:tuple(v) for k,v in changed.items()},tuple(schema_changes),tuple(projection_changes),tuple(plan))
