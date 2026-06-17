.PHONY: help clean

help: ## Show available make targets.
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

clean: ## Remove generated files, local environments, and preview outputs.
	rm -rf $(BUILD_DIR) $(DIST_DIR) .pytest_cache .coverage src/*.egg-info
