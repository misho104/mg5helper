.PHONY: clean relax

relax:
	@echo This make file is only for cleaning and testing.
	@echo Use setup.py to install. \(\"python ./setup.py install\"\)

clean:
	python setup.py clean
	rm -rf *.egg-info htmlcov .coverage */__pycache__ */tests/__pycache__ build dist

.PHONY: test unittest typetest formattest
test: unittest typetest formattest

unittest:
	@echo "# Performing the tests..."
	nosetests --config="" --cover-package=mg5helper --with-coverage
	@echo

typetest:
	@echo "# Checking typing by mypy..."
	mypy --ignore-missing-imports --follow-imports=silent --no-strict-optional .
	@echo

formattest:
	@echo "# Checking PEP format..."
	flake8 --max-line-length=120 .
	@echo

