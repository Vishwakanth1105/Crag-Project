.PHONY: install test lint typecheck run docker-up docker-down docker-config compile

install:
	pip install -r requirements.txt

test:
	python -m pytest

lint:
	ruff check .

typecheck:
	mypy src

compile:
	python -m compileall src tests

run:
	uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-config:
	docker compose config
