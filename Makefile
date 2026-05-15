# Makefile for common developer tasks

PY ?= python3
VENV ?= .venv
ACTIVATE = . $(VENV)/bin/activate
RUN_IN_ENV = if [ -f "$(VENV)/bin/activate" ]; then . "$(VENV)/bin/activate"; fi;

.PHONY: help init run run-api run-executor test

help:
	@echo "Usage: make <target>"
	@echo "Targets:"
	@echo "  init          Create virtualenv, install requirements and editable package"
	@echo "  run           Alias for run-api (start Mock WMS HTTP API)"
	@echo "  run-api       Start Mock WMS HTTP API (uvicorn, foreground)"
	@echo "  run-executor  Run mock_wms_executor (help)"
	@echo "  test          Run test suite (pytest)"

init:
	@echo "[make] creating virtualenv: $(VENV)"
	$(PY) -m venv $(VENV)
	@echo "[make] activating and installing dependencies"
	bash -lc "$(ACTIVATE) && pip install --upgrade pip setuptools wheel && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && pip install -e ."

run: run-api

run-api:
	@echo "[make] starting Mock WMS HTTP API (foreground)"
	@echo "Set MOCK_WMS_DB_PATH and MOCK_WMS_TASK_POINTS_PATH env vars as needed"
	bash -lc '$(RUN_IN_ENV) uvicorn scripts.mock_wms_api:create_app --factory --host 127.0.0.1 --port 8000'

run-executor:
	@echo "[make] run mock_wms_executor (show help)"
	bash -lc '$(RUN_IN_ENV) $(PY) -m amr_warehouse_sim.mock_wms_executor --help'

test:
	@echo "[make] running pytest"
	bash -lc '$(RUN_IN_ENV) $(PY) -m pytest test -q'
