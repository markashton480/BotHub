# Repository Guidelines

## Project Structure & Module Organization
- `bothub/` holds the Django project settings, URLs, and WSGI/ASGI entry points.
- `hub/` is the core Django app (models, views, serializers, GraphQL, templates).
- `hub/templates/hub/` and `templates/` contain server-rendered HTML.
- `db.sqlite3` is the default local database (created after migrations).
- `manage.py` is the standard Django management entry point.

## Build, Test, and Development Commands
- `python -m venv .venv && . .venv/bin/activate` sets up the local virtualenv.
- `pip install -r requirements.txt` installs backend dependencies.
- `python manage.py migrate` prepares the database schema.
- `python manage.py runserver` starts the dev server at `http://127.0.0.1:8000/`.
- `make test` runs the Django test suite (`manage.py test`).
- `make lint` runs Django system checks (`manage.py check`).
- `make collectstatic` gathers static assets for deployment.

## Coding Style & Naming Conventions
- Python follows standard Django/PEP 8 conventions with 4-space indentation.
- Keep app-level code in `hub/` and project-level configuration in `bothub/`.
- Use descriptive model and view names (e.g., `Project`, `Task`, `Thread`).
- No formatter is enforced in the repo; keep changes consistent with existing style.

## Testing Guidelines
- Tests live in `hub/tests.py` (Django `TestCase`).
- Name tests with `test_` prefixes (e.g., `test_create_project`).
- Run `make test` before submitting changes.

## Commit & Pull Request Guidelines
- Commit messages use short, imperative summaries (e.g., “Add webhooks and Postgres config”).
- Link PRs to the relevant issue/task when applicable.
- Include a clear description of changes and any API/UI impacts.
- Add screenshots or curl examples for UI/API changes when useful.

## Agent-Specific Instructions
- Track work via Version Declarations (VD), Work Orders (WO), and Tasks when provided.
- Add notable failures to the “What Broke Last Time” section.
- Server access: `ssh bothub` authenticates successfully.
