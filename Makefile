DIST := dist
NAME := Discogs.alfredworkflow
BUILD := $(DIST)/.build
RUN := uv run --no-sync
JSON_FILES := $(shell git ls-files '*.json')
export HOMEBREW_NO_AUTO_UPDATE := 1

.PHONY: icons setup test lint lint-shell lint-python lint-data lint-md lint-actions format format-check audit check ci clean build verify release sync-plist link-live

setup:
	brew bundle --quiet
	uv sync --group dev

icons:
	icon-symbol.sh --batch tools/icons.txt --outdir icons --size 256 --fg "#FFFFFF" --style macos

test:
	$(RUN) pytest

lint: lint-shell lint-python lint-data lint-md lint-actions

lint-shell:
	shellcheck src/maintenance.sh

lint-python:
	$(RUN) ruff check .
	$(RUN) pyright

lint-data:
	plutil -lint info.plist
	$(if $(JSON_FILES),jq empty $(JSON_FILES))

lint-md:
	markdownlint-cli2 "**/*.md"

lint-actions:
	actionlint

format:
	$(RUN) ruff format .

format-check:
	$(RUN) ruff format --check .

audit:
	$(RUN) pip-audit --skip-editable

check: lint format-check test

ci: check audit

clean:
	find . -name '__pycache__' -not -path './.git/*' -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache

build: check
	rm -rf $(DIST)
	mkdir -p $(BUILD)/src/dgapi $(BUILD)/icons "$(BUILD)/List Filter Images"
	cp info.plist $(BUILD)/
	cp icon.png $(BUILD)/
	cp src/dgapi/*.py $(BUILD)/src/dgapi/
	cp icons/*.png $(BUILD)/icons/
	mkdir -p $(BUILD)/images
	cp -R images/about $(BUILD)/images/
	mkdir -p $(BUILD)/src
	cp src/maintenance.sh $(BUILD)/src/
	cd $(BUILD) && zip -r -q ../$(NAME) .
	rm -rf $(BUILD)
	@echo "built $(DIST)/$(NAME)"

# audits the built bundle for local paths, baked-in tokens, junk files,
# unresolved script references, and import errors.
verify:
	$(RUN) python tools/verify_bundle.py $(DIST)/$(NAME)

release: build verify
	@test -n "$(VERSION)" || (echo "usage: make release VERSION=v1.0.0" && exit 1)
	git tag $(VERSION)
	git push origin $(VERSION)
	gh release create $(VERSION) $(DIST)/$(NAME) --generate-notes

# pulls info.plist from the live Alfred workflow bundle after editing
# keywords/objects/connections in the Alfred UI. WORKFLOW_DIR is
# machine-specific, never hardcoded here - pass it at invocation.
sync-plist:
	@test -n "$(WORKFLOW_DIR)" || (echo "usage: make sync-plist WORKFLOW_DIR=/path/to/bundle" && exit 1)
	cp "$(WORKFLOW_DIR)/info.plist" info.plist
	@echo "synced info.plist from $(WORKFLOW_DIR)"

# symlinks this repo's source/icons into the live Alfred workflow bundle so
# edits here take effect immediately, without a build/install step.
# WORKFLOW_DIR is machine-specific, never hardcoded here - pass it at
# invocation. Safe to re-run (idempotent).
link-live:
	@test -n "$(WORKFLOW_DIR)" || (echo "usage: make link-live WORKFLOW_DIR=/path/to/bundle" && exit 1)
	ln -sfn "$(CURDIR)/images" "$(WORKFLOW_DIR)/images"
	ln -sfn "$(CURDIR)/src" "$(WORKFLOW_DIR)/src"
	ln -sfn "$(CURDIR)/icons" "$(WORKFLOW_DIR)/icons"
	ln -sfn "$(CURDIR)/icon.png" "$(WORKFLOW_DIR)/icon.png"
	@echo "linked $(WORKFLOW_DIR) to this repo"
