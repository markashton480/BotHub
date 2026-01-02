.PHONY: test lint coverage coverage-report coverage-html

PYTHON := .venv/bin/python
ifeq ($(wildcard $(PYTHON)),)
PYTHON = python
endif

DJANGO_LOG_FILE ?= /tmp/bothub_django.log
export DJANGO_LOG_FILE

test:
	$(PYTHON) manage.py test

lint:
	$(PYTHON) manage.py check

coverage:
	coverage run --source='.' manage.py test
	coverage report
	coverage html

coverage-report:
	coverage report

coverage-html:
	coverage html

collectstatic:
	$(PYTHON) manage.py collectstatic --noinput
