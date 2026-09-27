# MoTA Scholarship & Fellowship Management System — dev shortcuts
# No-Docker path. Requires: python3.13, node 18+.

BACKEND=backend
FRONTEND=frontend
VENV=$(BACKEND)/.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: help setup backend-setup frontend-setup seed dev backend frontend test clean docker

help:
	@echo "Targets:"
	@echo "  make setup           - create venv, install backend + frontend deps"
	@echo "  make seed            - reset DB and load schemes + ~200 synthetic applicants"
	@echo "  make backend         - run FastAPI (http://localhost:8000/docs)"
	@echo "  make frontend        - run Next.js (http://localhost:3000)"
	@echo "  make dev             - run backend + frontend together"
	@echo "  make test            - run backend pytest suite"
	@echo "  make docker          - docker-compose up --build"
	@echo "  make clean           - remove venv, db, uploads, node_modules, .next"

setup: backend-setup frontend-setup

backend-setup:
	python3.13 -m venv $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(BACKEND)/requirements.txt
	@test -f $(BACKEND)/.env || cp $(BACKEND)/.env.example $(BACKEND)/.env

frontend-setup:
	cd $(FRONTEND) && npm install

seed:
	cd $(BACKEND) && ../$(VENV)/bin/python -m app.seed.seed

backend:
	cd $(BACKEND) && ../$(VENV)/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd $(FRONTEND) && npm run dev

dev:
	@echo "Starting backend (:8000) and frontend (:3000)..."
	@( cd $(BACKEND) && ../$(VENV)/bin/uvicorn app.main:app --reload --port 8000 & ) ; \
	  cd $(FRONTEND) && npm run dev

test:
	cd $(BACKEND) && ../$(VENV)/bin/python -m pytest app/tests -q

docker:
	docker compose up --build

clean:
	rm -rf $(VENV) $(BACKEND)/scholarship.db $(BACKEND)/uploads $(FRONTEND)/node_modules $(FRONTEND)/.next
