.PHONY: install run debug clean lint lint-strict

install:
	pip install -r requirements.txt

run:
	python fly_in.py config.txt

debug:
	python -m pdb fly_in.py config.txt

clean:
	-del /s /q /f *.pyc
	-rmdir /s /q __pycache__
	-rmdir /s /q .mypy_cache
	-rmdir /s /q *.egg-info
	-rmdir /s /q dist
	-rmdir /s /q build

lint:
	python -m flake8 .
	python -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	python -m mypy --strict .
	python -m flake8 .
