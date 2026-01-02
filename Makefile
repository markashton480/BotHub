.PHONY: test lint

PYTHON := .venv/bin/python
ifeq ($(wildcard $(PYTHON)),)
PYTHON = python
endif

test:
	$(PYTHON) manage.py test

lint:
	$(PYTHON) manage.py check

collectstatic:
	$(PYTHON) manage.py collectstatic --noinput
