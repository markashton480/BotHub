.PHONY: test lint

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

collectstatic:
	$(PYTHON) manage.py collectstatic --noinput
