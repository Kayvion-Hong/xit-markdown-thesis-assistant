PYTHON ?= python3

.PHONY: doctor setup check final-check pdf tex validate clean test

doctor:
	$(PYTHON) tools/doctor.py

setup:
	$(PYTHON) xit.py setup

check validate:
	$(PYTHON) xit.py check

final-check:
	$(PYTHON) xit.py final-check

pdf:
	$(PYTHON) xit.py pdf

tex:
	$(PYTHON) xit.py tex

test:
	$(PYTHON) -m unittest discover -s tests -v

clean:
	rm -rf build
