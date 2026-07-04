.PHONY: install test run
install:
	cd backend && python -m pip install -r requirements.txt

test:
	cd backend && pytest -q

run:
	cd backend && uvicorn app.main:app --reload
