.PHONY: lint format lint-format run run-asgi
# Lint Python code (run from project root: make lint)
lint:
	ruff check .

# Format Python code (run from project root: make format)
format:
	ruff format .

# Lint and format in one go
lint-format: format lint

# Run Django dev server (WSGI - no WebSockets)
run:
	python manage.py runserver

# Run with Daphne for WebSocket support (live updates)
# Uses venv/bin/daphne if venv exists
run-asgi:
	$(if $(wildcard venv/bin/daphne),venv/bin/daphne,daphne) -b 127.0.0.1 -p 8000 eld_backend.asgi:application
