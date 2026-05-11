# AGENTS.md

## Cursor Cloud specific instructions

This is a Python CLI tool (no web server, no database, no Docker). See `README.md` for full setup and usage docs.

### Quick reference

- **Activate venv**: `source .venv/bin/activate`
- **Run tests**: `python3 -m unittest discover -s tests -v`
- **Lint**: `flake8 src/ tests/ --max-line-length=100`
- **Run CLI**: `python3 src/main.py --help` (from repo root; `src/main.py` uses relative imports from `src/`)

### Gotchas

- The app requires Google OAuth credentials (`credentials.json`) and a valid `config.yaml` to run end-to-end. Without these, the CLI will error on startup with `FileNotFoundError: credentials.json`. Unit tests do **not** require credentials.
- `config.yaml` is gitignored. Copy from `config.example.yaml` if needed for local testing.
- The test file imports use `from src.classifier import ...` — tests must be run from the repo root with `python3 -m unittest discover -s tests -v`, not from inside the `tests/` directory.
- Source files use `from classifier import ...` (no `src.` prefix). The `src/main.py` entry point must be invoked from the repo root as `python3 src/main.py` so Python resolves `src/` as the working directory for imports.
