# Savant Runtime

Savant Runtime is a filesystem-oriented canon, graph-compilation, and conversational service repository. The authoritative dynamic canon lives in `canon-system/authority/`; Markdown projections and the SQLite database are derived artifacts.

## Supported local workflow

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python canon-system/runtime/canonctl.py validate
```

The Palaver API requires an explicit bearer token and never reads dotenv files itself:

```bash
export PALAVER_API_TOKEN='replace-with-a-long-random-token'
export PALAVER_ALLOWED_ORIGINS='http://127.0.0.1:5173'
.venv/bin/python palaver_voice_backend.py
```

Use a protected service-manager environment file outside the repository for credentials. Never commit populated `.env` files. The baseline contains external symlinks and historical scripts that target `/root/savant-runtime`; those are not supported local entry points until the audit ledger marks them contained and validated.

See [the audit documentation](docs/codex-audit/AUDIT_LEDGER.md) for architecture, validation evidence, and remaining risks.
