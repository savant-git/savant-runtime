#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "authority"
PROJECTIONS = ROOT / "projections"
HISTORY = ROOT / "history"
SCHEMA = json.loads((ROOT / "schemas/canon-record.schema.json").read_text())

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def records():
    for path in sorted(AUTHORITY.rglob("*.yaml")):
        yield path, yaml.safe_load(path.read_text())

def validate():
    validator = Draft202012Validator(SCHEMA)
    errors = []
    seen = {}
    for path, record in records():
        rid = record.get("id")
        if rid in seen:
            errors.append(f"duplicate id {rid}: {seen[rid]} and {path}")
        seen[rid] = path
        for error in validator.iter_errors(record):
            errors.append(f"{path}: {'/'.join(map(str,error.path))}: {error.message}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"valid: {len(seen)} records")
    return 0

def md_value(value, level=0):
    if value is None:
        return "_unknown_"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str,int,float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "_none_"
        return "\n".join(f"- {md_value(v, level+1)}" for v in value)
    if isinstance(value, dict):
        out = []
        for k,v in value.items():
            out.append(f"### {k.replace('_',' ')}\n\n{md_value(v, level+1)}")
        return "\n\n".join(out)
    return str(value)

def project():
    if PROJECTIONS.exists():
        shutil.rmtree(PROJECTIONS)
    (PROJECTIONS / "md").mkdir(parents=True)
    index = []
    for path, record in records():
        rid = record["id"]
        title = record.get("title", rid)
        rel = rid.replace(":","/") + ".md"
        target = PROJECTIONS / "md" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        body = [
            f"# {title}",
            "",
            "> generated projection. edit authority yaml, not this file.",
            "",
            f"- id: `{rid}`",
            f"- kind: `{record.get('kind')}`",
            f"- status: `{record.get('status')}`",
            f"- version: `{record.get('version')}`",
            "",
        ]
        for key, value in record.items():
            if key in {"id","title","kind","status","version"}:
                continue
            body += [f"## {key.replace('_',' ')}", "", md_value(value), ""]
        target.write_text("\n".join(body), encoding="utf-8")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        index.append({"id":rid,"authority_path":str(path.relative_to(ROOT)),"projection_path":str(target.relative_to(ROOT)),"version":record["version"],"sha256":digest})
    (PROJECTIONS / "index").mkdir(parents=True)
    (PROJECTIONS / "index/manifest.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"projected: {len(index)} records")

def build_db():
    db = ROOT / "runtime/canon.sqlite3"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript("""
    create table records(
      id text primary key,
      kind text not null,
      status text not null,
      version integer not null,
      authority_path text not null,
      body_json text not null
    );
    create table relationships(
      source_id text not null,
      relation text not null,
      target_id text not null
    );
    create index idx_records_kind on records(kind);
    create index idx_records_status on records(status);
    create index idx_rel_source on relationships(source_id);
    create index idx_rel_target on relationships(target_id);
    """)
    for path, record in records():
        con.execute("insert into records values(?,?,?,?,?,?)",(
            record["id"],record["kind"],record["status"],record["version"],
            str(path.relative_to(ROOT)),json.dumps(record,sort_keys=True)
        ))
        for relation in record.get("relationships",[]):
            if isinstance(relation,dict):
                con.execute("insert into relationships values(?,?,?)",(
                    record["id"],relation.get("type","related_to"),relation.get("target","")
                ))
    con.commit()
    con.close()
    print(db)

def supersede(old_id, new_file):
    old_path = None
    old = None
    for path, record in records():
        if record["id"] == old_id:
            old_path, old = path, record
            break
    if old is None:
        raise SystemExit(f"not found: {old_id}")
    new_path = Path(new_file).resolve()
    new = yaml.safe_load(new_path.read_text())
    if old_id not in new.setdefault("lineage",{}).setdefault("supersedes",[]):
        new["lineage"]["supersedes"].append(old_id)
    old["status"] = "superseded"
    old["lineage"].setdefault("superseded_by",[]).append(new["id"])
    old_path.write_text(yaml.safe_dump(old,sort_keys=False),encoding="utf-8")
    target = AUTHORITY / new_path.name
    if target.exists():
        target = AUTHORITY / f"{new['kind']}s" / new_path.name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(yaml.safe_dump(new,sort_keys=False),encoding="utf-8")
    event = {"type":"supersession","at":now(),"old":old_id,"new":new["id"],"old_version":old["version"],"new_version":new["version"]}
    out = HISTORY / "supersessions" / f"{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}_{old_id.replace(':','_')}.json"
    out.write_text(json.dumps(event,indent=2),encoding="utf-8")
    print(out)

def main():
    p=argparse.ArgumentParser(prog="canonctl")
    s=p.add_subparsers(dest="cmd",required=True)
    s.add_parser("validate")
    s.add_parser("project")
    s.add_parser("build-db")
    q=s.add_parser("supersede")
    q.add_argument("old_id")
    q.add_argument("new_file")
    a=p.parse_args()
    return {"validate":validate,"project":project,"build-db":build_db}.get(a.cmd,lambda:supersede(a.old_id,a.new_file))()

if __name__=="__main__":
    raise SystemExit(main())
