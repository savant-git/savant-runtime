#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from collections import Counter
from pathlib import Path

def manifest_from(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith('{"authoritative_source_preserved_by_sha256"'):
                return json.loads(line)
    raise ValueError("sdump manifest not found")

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("dump",type=Path); parser.add_argument("--root",type=Path,default=Path("/root/savant-runtime")); args=parser.parse_args()
    root=args.root.resolve(); manifest=manifest_from(args.dump.resolve())
    categories=Counter(); top_levels=Counter(); languages=Counter(); matched=[]; changed=[]; missing=[]
    redacted=[]; skipped=manifest["diagnostics"]["skipped_by_reason"]
    for item in manifest["files"]:
        path=item["path"]; categories[item["category"]]+=1; top_levels[path.split("/",1)[0]]+=1; languages[item["language"]]+=1
        if item.get("redactions"): redacted.append({"path":path,"count":item["redactions"]})
        live=root/path
        if not live.is_file(): missing.append(path); continue
        actual=hashlib.sha256(live.read_bytes()).hexdigest()
        if actual == item["source_sha256"]: matched.append(path)
        else: changed.append({"path":path,"snapshot_sha256":item["source_sha256"],"live_sha256":actual})
    report={"id":"projection:sdump-reconciliation-20260721","kind":"projection","source_dump":args.dump.name,
            "snapshot_hash":manifest.get("snapshot_hash"),"composition_registry_hash":manifest["composition_registry_hash"],
            "authority_interpretation":"Evidence projection only; hash fidelity does not promote authority.",
            "counts":{"manifest_files":len(manifest["files"]),"matched":len(matched),"changed":len(changed),"missing":len(missing),
                      "canon":categories["canon"],"source":categories["source"],"duplicate_files":manifest["counts"]["duplicate_files"],
                      "redactions":manifest["counts"]["redactions"],"skipped":manifest["counts"]["skipped"]},
            "categories":dict(sorted(categories.items())),"top_levels":dict(sorted(top_levels.items())),"languages":dict(sorted(languages.items())),
            "changed":changed,"missing":missing,"redacted_files":redacted,"skipped_by_reason":skipped,
            "complete_match":not changed and not missing,"unknowns_preserved":bool(redacted or skipped)}
    out=root/"context/SDUMP_RECONCILIATION_20260721.json"; out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    md=root/"context/SDUMP_RECONCILIATION_20260721.md"
    comparison = ("All captured files match the live repository byte-for-byte." if report["complete_match"] else
                  f"{len(matched)} captured files remain byte-for-byte matches; {len(changed)} changed and {len(missing)} are missing. Exact deltas are recorded in the JSON projection.")
    md.write_text(f"# Source Dump Reconciliation — 2026-07-21\n\nThe dump `{args.dump.name}` is an evidence projection, not authority.\n\n- Snapshot hash: `{report['snapshot_hash']}`\n- Manifest files: {len(manifest['files'])}\n- Live SHA-256 matches: {len(matched)}\n- Changed: {len(changed)}\n- Missing: {len(missing)}\n- Canon-classified: {categories['canon']}\n- Source-classified: {categories['source']}\n- Redactions: {manifest['counts']['redactions']} across {len(redacted)} files\n- Skipped candidates: {manifest['counts']['skipped']}\n\n{comparison} Redacted and skipped material remains unknown and was not inferred into canon.\n",encoding="utf-8")
    print(out); print(md); return 0

if __name__ == "__main__": raise SystemExit(main())
