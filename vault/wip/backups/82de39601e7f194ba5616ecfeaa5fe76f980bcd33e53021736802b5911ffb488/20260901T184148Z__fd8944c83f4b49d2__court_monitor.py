#!/usr/bin/env python3
"""Durable Miami-Dade civil-case monitor. Secrets are never logged."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

KEY_NAME = "MIAMI_DADE_CLERK_API_KEY"
UTC = dt.timezone.utc


def now() -> str:
    return dt.datetime.now(UTC).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS runs(
      id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
      status TEXT NOT NULL, requests INTEGER NOT NULL DEFAULT 0,
      units_balance REAL, message TEXT);
    CREATE TABLE IF NOT EXISTS snapshots(
      id INTEGER PRIMARY KEY, kind TEXT NOT NULL, captured_at TEXT NOT NULL,
      sha256 TEXT NOT NULL, payload TEXT NOT NULL,
      UNIQUE(kind, sha256));
    CREATE TABLE IF NOT EXISTS dockets(
      docket_number TEXT PRIMARY KEY, event_date TEXT, description TEXT,
      comments TEXT, event_type TEXT, payload TEXT NOT NULL,
      first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS documents(
      docket_number TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL,
      size INTEGER NOT NULL, downloaded_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, type TEXT NOT NULL,
      subject TEXT NOT NULL, details TEXT NOT NULL);
    """)
    return db


class Client:
    def __init__(self, cfg: dict[str, Any], key: str, db: sqlite3.Connection, run_id: int):
        self.cfg, self.key, self.db, self.run_id = cfg, key, db, run_id
        self.requests = 0
        self.balance = None

    def get(self, params: dict[str, Any]) -> dict[str, Any]:
        limit = int(self.cfg.get("maximum_requests_per_run", 25))
        if self.requests >= limit:
            raise RuntimeError(f"Safety limit reached: {limit} API requests in this run")
        query = dict(params)
        query["AuthKey"] = self.key
        url = self.cfg["api_base"] + "?" + urllib.parse.urlencode(query)
        attempts = int(self.cfg.get("retries", 3))
        timeout = int(self.cfg.get("timeout_seconds", 45))
        last = "request failed"
        for attempt in range(attempts):
            self.requests += 1
            self.db.execute("UPDATE runs SET requests=? WHERE id=?", (self.requests, self.run_id))
            self.db.commit()
            try:
                req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "SavantCourtMonitor/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    data = json.loads(response.read().decode("utf-8-sig"))
                self.balance = data.get("UnitsBalance", self.balance)
                status = str(data.get("Status", "")).lower()
                desc = str(data.get("StatusDesc", ""))
                if status and status not in {"1", "ok", "success", "true", "0"}:
                    raise RuntimeError(f"Clerk API rejected request: {desc or status}")
                return data
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code} from Clerk API"
                if e.code < 500 and e.code != 429:
                    break
            except urllib.error.URLError as e:
                last = f"Network error: {e.reason}"
            except (json.JSONDecodeError, TimeoutError) as e:
                last = f"Invalid/timeout response: {type(e).__name__}"
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
        raise RuntimeError(last)


def docket_list(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("DocketsList", "docketsList", "DocketList", "dockets"):
        value = data.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            for nested in ("DocketInfo", "docketInfo"):
                rows = value.get(nested)
                if isinstance(rows, list): return rows
                if isinstance(rows, dict): return [rows]
    return []


def field(row: dict[str, Any], *names: str) -> Any:
    lower = {str(k).lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def record_snapshot(db: sqlite3.Connection, kind: str, payload: Any) -> bool:
    clean = {k: v for k, v in payload.items() if k not in {"IPAddress", "UnitsBalance"}} if isinstance(payload, dict) else payload
    before = db.execute("SELECT sha256 FROM snapshots WHERE kind=? ORDER BY id DESC LIMIT 1", (kind,)).fetchone()
    sha = digest(clean)
    db.execute("INSERT OR IGNORE INTO snapshots(kind,captured_at,sha256,payload) VALUES(?,?,?,?)",
               (kind, now(), sha, canonical(clean)))
    return before is not None and before[0] != sha


def decode_document(response: dict[str, Any]) -> bytes:
    value = response.get("DocketDocument") or response.get("docketDocument")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("Document response contained no document")
    try:
        return base64.b64decode(value, validate=True)
    except Exception as e:
        raise RuntimeError("Document was not valid base64") from e


def extension(blob: bytes) -> str:
    if blob.startswith(b"%PDF"): return ".pdf"
    if blob.startswith(b"\x89PNG"): return ".png"
    if blob.startswith(b"\xff\xd8\xff"): return ".jpg"
    if blob[:4] in {b"II*\x00", b"MM\x00*"}: return ".tif"
    return ".bin"


def notify(cfg: dict[str, Any], title: str, message: str) -> None:
    if cfg.get("notify_termux") and shutil.which("termux-notification"):
        subprocess.run(["termux-notification", "--title", title, "--content", message],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def check(cfg: dict[str, Any], key: str) -> int:
    root = Path(os.path.expanduser(cfg["data_dir"])).resolve()
    docs = root / "documents"
    root.mkdir(parents=True, exist_ok=True); docs.mkdir(exist_ok=True)
    os.chmod(root, 0o700)
    db = connect(root / "history.sqlite3")
    cur = db.execute("INSERT INTO runs(started_at,status) VALUES(?,?)", (now(), "running"))
    run_id = int(cur.lastrowid); db.commit()
    client = Client(cfg, key, db, run_id)
    changes: list[str] = []
    try:
        case = cfg["case_number"]
        info = client.get({"caseNumber": case})
        if record_snapshot(db, "case_info", info): changes.append("case information changed")
        dockets_raw = client.get({"civilCaseNumber": case})
        if record_snapshot(db, "docket_response", dockets_raw): changes.append("docket changed")
        rows = docket_list(dockets_raw)
        new_numbers: list[str] = []
        seen_numbers: list[str] = []
        for row in rows:
            number = str(field(row, "docketNumber", "docket_number", "eventID") or "").strip()
            if not number: continue
            seen_numbers.append(number)
            prior = db.execute("SELECT payload FROM dockets WHERE docket_number=?", (number,)).fetchone()
            payload = canonical(row)
            description = str(field(row, "docketDescrition", "docketDescription", "description") or "")
            values = (str(field(row, "eventDate") or ""), description,
                      str(field(row, "comments") or ""), str(field(row, "eventType") or ""), payload)
            if prior is None:
                db.execute("INSERT INTO dockets VALUES(?,?,?,?,?,?,?,?)",
                           (number, *values, now(), now()))
                db.execute("INSERT INTO events(created_at,type,subject,details) VALUES(?,?,?,?)",
                           (now(), "new_docket", number, description))
                new_numbers.append(number)
            else:
                if prior[0] != payload:
                    db.execute("INSERT INTO events(created_at,type,subject,details) VALUES(?,?,?,?)",
                               (now(), "changed_docket", number, description))
                    changes.append(f"docket {number} changed")
                db.execute("UPDATE dockets SET event_date=?,description=?,comments=?,event_type=?,payload=?,last_seen=? WHERE docket_number=?",
                           (*values, now(), number))
        db.commit()
        if new_numbers: changes.append(f"{len(new_numbers)} new docket entr{'y' if len(new_numbers)==1 else 'ies'}")
        if cfg.get("download_documents"):
            # Retry previously missed documents on later runs, not only when the
            # docket itself is first discovered.
            missing_numbers = [n for n in seen_numbers if not db.execute(
                "SELECT 1 FROM documents WHERE docket_number=?", (n,)).fetchone()]
            for number in missing_numbers:
                if db.execute("SELECT 1 FROM documents WHERE docket_number=?", (number,)).fetchone(): continue
                try:
                    response = client.get({"caseNumber": case, "docketNumber": number})
                    blob = decode_document(response); sha = hashlib.sha256(blob).hexdigest()
                    path = docs / f"docket-{int(number):05d}-{sha[:12]}{extension(blob)}"
                    path.write_bytes(blob); os.chmod(path, 0o600)
                    db.execute("INSERT INTO documents VALUES(?,?,?,?,?)", (number, str(path), sha, len(blob), now()))
                except Exception as e:
                    db.execute("INSERT INTO events(created_at,type,subject,details) VALUES(?,?,?,?)",
                               (now(), "document_error", number, str(e)))
        clean_info = {k: v for k, v in info.items() if k not in {"IPAddress", "UnitsBalance"}}
        clean_dockets = {k: v for k, v in dockets_raw.items() if k not in {"IPAddress", "UnitsBalance"}}
        atomic_json(root / "latest-case.json", clean_info)
        atomic_json(root / "latest-dockets.json", clean_dockets)
        balance = client.balance
        if balance is not None and float(balance) < float(cfg.get("minimum_units_balance", 20)):
            changes.append(f"LOW API BALANCE: {balance} units")
        status = "changed" if changes else "ok"
        db.execute("UPDATE runs SET finished_at=?,status=?,requests=?,units_balance=?,message=? WHERE id=?",
                   (now(), status, client.requests, balance, "; ".join(changes), run_id)); db.commit()
        message = "; ".join(changes) if changes else "No case changes"
        print(f"[{now()}] {case}: {message}; requests={client.requests}; units={balance}")
        if changes: notify(cfg, "Miami-Dade case updated", message)
        return 0
    except Exception as e:
        safe = str(e).replace(key, "[REDACTED]")
        db.execute("UPDATE runs SET finished_at=?,status=?,requests=?,units_balance=?,message=? WHERE id=?",
                   (now(), "error", client.requests, client.balance, safe, run_id)); db.commit()
        print(f"[{now()}] ERROR: {safe}", file=sys.stderr)
        notify(cfg, "Court monitor error", safe)
        return 1
    finally:
        db.close()


def doctor(cfg: dict[str, Any], key: str | None) -> int:
    issues = []
    if sys.version_info < (3, 9): issues.append("Python 3.9+ is required")
    if not key: issues.append(f"{KEY_NAME} is missing from environment/.env")
    elif len(key) < 8: issues.append(f"{KEY_NAME} appears too short")
    data = Path(os.path.expanduser(cfg["data_dir"]))
    try:
        data.mkdir(parents=True, exist_ok=True)
        probe = data / ".write-test"; probe.write_text("ok"); probe.unlink()
    except OSError as e: issues.append(f"Data directory is not writable: {e}")
    if issues:
        for item in issues: print(f"FAIL: {item}")
        return 1
    print(f"OK: configuration, Python, secret presence, and data directory")
    print("No paid API request was made.")
    return 0


def status(cfg: dict[str, Any]) -> int:
    db_path = Path(os.path.expanduser(cfg["data_dir"])) / "history.sqlite3"
    if not db_path.exists(): print("No checks have run yet."); return 0
    db = connect(db_path)
    row = db.execute("SELECT started_at,status,requests,units_balance,message FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    counts = db.execute("SELECT (SELECT COUNT(*) FROM dockets),(SELECT COUNT(*) FROM documents),(SELECT COUNT(*) FROM events)").fetchone()
    print(f"Last run: {row}\nDockets: {counts[0]}  Documents: {counts[1]}  Events: {counts[2]}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("check", "doctor", "status"))
    p.add_argument("--config", default="~/savant-runtime/court-monitor.json")
    args = p.parse_args()
    cfg = load_json(Path(os.path.expanduser(args.config)))
    load_env(Path(os.path.expanduser(cfg.get("env_file", "~/.env"))))
    key = os.environ.get(KEY_NAME)
    if args.command == "doctor": return doctor(cfg, key)
    if args.command == "status": return status(cfg)
    if not key:
        print(f"ERROR: {KEY_NAME} not found in {cfg.get('env_file')}", file=sys.stderr); return 2
    return check(cfg, key)


if __name__ == "__main__":
    raise SystemExit(main())
