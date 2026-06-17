PYTHON ?= python3
SRC_DIR := src
BUILD_DIR := build
DIST_DIR := dist
PY_DEPS_DIR := $(BUILD_DIR)/pydeps
PY_BOOTSTRAP := $(PY_DEPS_DIR)/.ready

DEFAULT_DATA_DIR ?= /app/data/ourairports
DEFAULT_CONTRACT ?= /app/data/contracts/release_contract.json
DEFAULT_RELEASE_DIR ?= /app/output/release

export PYTHONPATH := $(PY_DEPS_DIR):$(SRC_DIR)

include mk/common.mk
include mk/python.mk
include mk/release.mk
