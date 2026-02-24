.PHONY: dev test

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v
