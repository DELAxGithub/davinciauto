PY ?= python3.11
VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
CLI := $(VENV)/bin/davinciauto-cli
PYINSTALLER := $(VENV)/bin/pyinstaller
SPEC := pyinstaller/davinciauto_cli.spec
FFMPEG ?= $(shell which ffmpeg 2>/dev/null)
FFPROBE ?= $(shell which ffprobe 2>/dev/null)
CLI_VERSION ?= 0.1.0
CLI_ARCH ?= $(shell uname -m)
BUNDLE_NAME ?= davinciauto-cli-$(CLI_VERSION)-$(CLI_ARCH)
BUNDLE_DIR := dist/$(BUNDLE_NAME)
BUNDLE_DMG := dist/$(BUNDLE_NAME).dmg
BUNDLE_TAR := dist/$(BUNDLE_NAME).tar.gz
BUNDLE_HASH := dist/$(BUNDLE_NAME)-SHA256SUMS.txt

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  make setup        # create virtualenv and install project (editable)"
	@echo "  make self-check   # run CLI self-check with JSON output"
	@echo "  make fake-tts     # run pipeline in fake TTS mode against sample data"
	@echo "  make run ARGS=…   # pass custom args to davinciauto-cli"
	@echo "  make smoke        # execute smoke test script"
	@echo "  make bundle       # build PyInstaller bundle and DMG"
	@echo "  make clean        # remove virtualenv and build artefacts"

.PHONY: setup
setup:
	@$(PY) -m venv $(VENV)
	@$(PYTHON) -m pip install -U pip wheel
	@$(PIP) install -e .[cli,dev]
	@echo "Virtualenv ready at $(VENV)"

.PHONY: self-check
self-check:
	@DAVINCIAUTO_FFMPEG="$(FFMPEG)" DAVINCIAUTO_FFPROBE="$(FFPROBE)" \
	 DAVA_FFMPEG_PATH="$(FFMPEG)" DAVA_FFPROBE_PATH="$(FFPROBE)" \
	 $(CLI) --self-check --json || true

.PHONY: fake-tts
fake-tts:
	@mkdir -p .out/fake_tts
	@DAVINCIAUTO_FFMPEG="$(FFMPEG)" DAVINCIAUTO_FFPROBE="$(FFPROBE)" \
	 DAVA_FFMPEG_PATH="$(FFMPEG)" DAVA_FFPROBE_PATH="$(FFPROBE)" \
	 $(CLI) run --script samples/sample_script.txt --output .out/fake_tts --fake-tts --provider fake --target resolve
	@echo "Outputs written to .out/fake_tts"

.PHONY: run
run:
	@if [ -z "$(ARGS)" ]; then \
		echo "Usage: make run ARGS='--script path --output path [options]'" >&2; \
		exit 1; \
	fi
	@$(CLI) run $(ARGS)

.PHONY: smoke
smoke:
	@bash scripts/smoke_fake_tts.sh

.PHONY: bundle
bundle:
	@if [ ! -x "$(PYINSTALLER)" ]; then \
		echo "PyInstaller not installed; run 'make setup' first." >&2; \
		exit 1; \
	fi
	@if [ ! -f "$(SPEC)" ]; then \
		echo "Spec file $(SPEC) not found." >&2; \
		exit 1; \
	fi
	@echo "Building PyInstaller bundle ($(BUNDLE_NAME))..."
	@rm -rf dist && mkdir -p dist
	@DAVINCIAUTO_FFMPEG_BUNDLE="$${DAVINCIAUTO_FFMPEG_BUNDLE:-$$(which ffmpeg 2>/dev/null)}" \
	 DAVINCIAUTO_FFPROBE_BUNDLE="$${DAVINCIAUTO_FFPROBE_BUNDLE:-$$(which ffprobe 2>/dev/null)}" \
	 DAVINCIAUTO_CLI_BUNDLE="$(BUNDLE_NAME)" \
	 DAVINCIAUTO_CLI_VERSION="$(CLI_VERSION)" \
	 BUILD_VERSION="$(CLI_VERSION)" \
	 "$(PYINSTALLER)" "$(SPEC)" --noconfirm --clean
	@if [ ! -d "$(BUNDLE_DIR)" ]; then \
		echo "Collector directory $(BUNDLE_DIR) not found" >&2; \
		exit 1; \
	fi
	@echo "$(CLI_VERSION)" > "$(BUNDLE_DIR)/VERSION"
	@if [ -d "$(BUNDLE_DIR)/_internal/licenses" ]; then \
		mkdir -p "$(BUNDLE_DIR)/licenses"; \
		rsync -a "$(BUNDLE_DIR)/_internal/licenses/" "$(BUNDLE_DIR)/licenses/"; \
	fi
	@cp resources/README_FIRST.txt "$(BUNDLE_DIR)/README_FIRST.txt"
	@mkdir -p "$(BUNDLE_DIR)/samples"
	@cp samples/sample_script.txt "$(BUNDLE_DIR)/samples/sample_script.txt"
	@cp docs/CLI_SETUP.md $(BUNDLE_DIR)/CLI_SETUP.md
	@echo "Creating DMG $(BUNDLE_DMG)..."
	@scripts/package_dmg.sh "$(BUNDLE_DIR)" "$(BUNDLE_NAME)"
	@echo "Creating tarball $(BUNDLE_TAR)..."
	@tar -czf "$(BUNDLE_TAR)" -C dist "$(BUNDLE_NAME)"
	@echo "Generating SHA256 sums $(BUNDLE_HASH)..."
	@shasum -a 256 "$(BUNDLE_DMG)" "$(BUNDLE_TAR)" > "$(BUNDLE_HASH)"
	@echo "Bundle artifacts available under dist/:"
	@ls -1 dist

.PHONY: clean
clean:
	@rm -rf $(VENV) build dist .out
	@echo "Cleaned virtualenv and build artefacts."
