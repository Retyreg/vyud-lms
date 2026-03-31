.PHONY: migrate migration rollback run test

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"

rollback:
	alembic downgrade -1

run:
	uvicorn app.main:app --reload

test:
	pytest tests/ -v
