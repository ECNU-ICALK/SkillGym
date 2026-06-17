.PHONY: package packaged-smoke preview release

RELEASE_LOCK := $(BUILD_DIR)/package.lock

package: ## Build the packaged CLI preview under dist/package/.
	rm -rf $(DIST_DIR)/package
	$(PYTHON) -m airdesk --data-dir $(DEFAULT_DATA_DIR) release --contract $(DEFAULT_CONTRACT) --output-dir $(DIST_DIR)/package --build-target "make package" --format json >/dev/null
	mkdir -p $(BUILD_DIR)
	touch $(RELEASE_LOCK)

packaged-smoke: package ## Execute smoke scenarios against the packaged CLI preview.
	$(PYTHON) scripts/run_packaged_smoke.py --release-dir $(DIST_DIR)/package --data-dir $(DEFAULT_DATA_DIR) --contract $(DEFAULT_CONTRACT)

preview: package ## Build a release preview under build/release-preview/.
	rm -rf $(BUILD_DIR)/release-preview
	$(PYTHON) -m airdesk --data-dir $(DEFAULT_DATA_DIR) release --contract $(DEFAULT_CONTRACT) --output-dir $(BUILD_DIR)/release-preview --build-target "make preview" --require-package-lock --format json >/dev/null

release: packaged-smoke ## Build the final release delivery under /app/output/release.
	rm -rf $(DEFAULT_RELEASE_DIR)
	$(PYTHON) -m airdesk --data-dir $(DEFAULT_DATA_DIR) release --contract $(DEFAULT_CONTRACT) --output-dir $(DEFAULT_RELEASE_DIR) --build-target "make release" --require-package-lock --format json >/dev/null
