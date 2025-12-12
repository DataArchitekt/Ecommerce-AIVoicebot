.PHONY: venv install seed

venv:
	/Users/A200266445/.pyenv/shims/python3.9 -m venv backend/.venv
	@echo "venv created"

install: venv
	source backend/.venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -r backend/requirements.txt

seed:
	source backend/.venv/bin/activate && export DB_URL="postgresql://postgres:password@localhost:5432/postgres" && python backend/app/seed_catalog.py