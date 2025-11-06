# Repository Guidelines

## Project Structure & Module Organization
- Entry point: `main.py` (CLI/runner). GUI helper: `run_gui.py` or `run_gui.bat`.
- Core modules under `nlp/`, `utils/`, `tools/`, and `ui/`. Config in `config/`.
- Documentation in `docs/`. Sample data/logs in `data/` and `logs/`.
- Tests live at repo root as `test_*.py` files (e.g., `test_time_range_filtering.py`).

## Build, Test, and Development Commands
- Create venv (PowerShell): `py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1`
- Create venv (bash): `python3 -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run tests: `pytest -q`
- Format/Lint: `black .` and `flake8 .`
- Run app: `python main.py`  |  GUI: `python run_gui.py`

## Coding Style & Naming Conventions
- Python 3.10+; 4-space indentation; UTF-8 source files.
- Black defaults (88 chars). Keep imports grouped: stdlib, third-party, local.
- Naming: modules `snake_case`, classes `PascalCase`, functions/vars `snake_case`, constants `UPPER_SNAKE_CASE`.
- Type hints encouraged; validate with `flake8` before pushing.

## Testing Guidelines
- Framework: `pytest` (see `requirements.txt`).
- Test files named `test_*.py` at repo root; mirror feature names where possible.
- Add focused unit tests with clear arrange/act/assert blocks. Mark slow/integration if needed.
- Keep coverage from regressing for touched modules.

## Commit & Pull Request Guidelines
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`.
- Subject in imperative mood ≤ 72 chars; body explains rationale and user impact.
- PRs must: describe change, link issues, include screenshots/logs for UI, and add/update tests. Ensure `pytest`, `black`, and `flake8` pass.

## Security & Configuration Tips
- Secrets via environment or `.env` (example keys only). Do not commit real credentials.
- Likely keys: `OPENAI_API_KEY` and related service tokens.
- Pin dependencies in `requirements.txt`; review changes to high-impact packages (e.g., `torch`, `PyQt6`).

## Agent-Specific Instructions
- This AGENTS.md applies repo-wide. If a deeper directory defines its own AGENTS.md, that file takes precedence for its subtree.
- Agents should follow style, testing, and PR rules for any file they modify.

