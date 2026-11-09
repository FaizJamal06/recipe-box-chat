# Every target is one plain command; on Windows run them directly (see README).
# Activate the venv first: .venv\Scripts\Activate.ps1 (Windows) or . .venv/bin/activate
# More targets (cli, eval, ui build) are added with their milestones.
.PHONY: setup data db test coverage peek profile run docker

setup:
	python scripts/setup.py

data:
	python scripts/download.py

db:
	python -m backend.app.ingest

test:
	pytest -q -x

coverage:
	python scripts/coverage.py

peek:
	python scripts/peek.py --n 3

profile:
	python scripts/profile_data.py

run:
	python -m uvicorn app.api:app --app-dir backend --port 8000 --reload

docker:
	docker build -t recipe-box . && docker run --rm -p 8000:8000 recipe-box
