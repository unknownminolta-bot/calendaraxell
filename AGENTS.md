# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is a Python CLI tool that auto-colors Google Family Calendar events based on keyword rules. The core classification logic is fully testable without external services.

### Running tests

```
source .venv/bin/activate
python3 -m unittest discover -s tests -v
```

Tests are pure unit tests of the classifier module — no Google credentials or network access needed.

### Running the application

See `README.md` for full CLI usage. The main entrypoint is `src/main.py`. Requires a valid Google OAuth `credentials.json` and a `config.yaml` (copy from `config.example.yaml`).

**Important**: The application requires Google Calendar API OAuth credentials (`credentials.json`) to run end-to-end. Without these, the app will fail at authentication. The unit tests cover the core classification logic and do not need credentials.

### Gotchas

- The `src/main.py` entrypoint uses relative imports from `src/`, so always run from the workspace root: `python3 src/main.py`.
- No linter is configured in this project — there is no `pyproject.toml`, `setup.cfg`, or linting config.
- `config.yaml` is gitignored; copy `config.example.yaml` to `config.yaml` for local testing.
