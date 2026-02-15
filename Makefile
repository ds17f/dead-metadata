# Grateful Dead Archive Data Pipeline
# Stage-based data collection and processing

.PHONY: help stage01-collect-data stage02-generate-data collect-archive-data collect-jerrygarcia-shows collect-show-image-urls collect-show-image-files generate-recordings integrate-shows process-collections package-data package-data-versioned package-release package-dev release release-dry-run all clean

# Default help
help:
	@echo "🎵 Grateful Dead Archive Data Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  stage01-collect-data      - Run complete Stage 1: Data Collection (5-7 hours)"
	@echo "  stage02-generate-data     - Run complete Stage 2: Data Generation (fast)"
	@echo ""
	@echo "  collect-archive-data      - Collect metadata from Archive.org (2-3 hours)"
	@echo "  collect-jerrygarcia-shows - Collect complete show database from jerrygarcia.com (3-4 hours)"
	@echo "  collect-show-image-urls  - Extract ticket/photo URLs into show JSON (fast, no downloads)"
	@echo "  collect-show-image-files - Download ticket images and photos for all shows"
	@echo "  generate-recordings       - Generate minimal recording data with ratings and enhanced metadata from cache"
	@echo "  integrate-shows           - Integrate JG shows with recording data"
	@echo "  process-collections       - Process collections and add to shows"
	@echo "  package-data              - Package all processed data into data.zip for distribution"
	@echo "  package-data-versioned    - Create versioned package with auto-detected version"
	@echo "  package-release VERSION=X - Create release package with specific version"
	@echo "  package-dev               - Create development build with commit hash"
	@echo "  release [VERSION=X]       - Create GitHub release with auto-detected or specified version"
	@echo "  release-dry-run [VERSION=X] - Show what would be released without creating it"
	@echo "  all                       - Run complete pipeline"
	@echo "  clean                     - Clean generated data"

# Stage 1: Data Collection
collect-archive-data:
	@echo "🎵 Collecting Grateful Dead metadata from Archive.org..."
	@echo "This may take 2-3 hours for full collection"
	python scripts/01-collect-data/collect_archive_metadata.py --mode full --verbose
	@echo "✅ Archive.org collection complete!"

collect-jerrygarcia-shows:
	@echo "🎭 Collecting complete Grateful Dead show database from jerrygarcia.com..."
	@echo "This will collect ~2,331 shows from 111 pages (3-4 hours with 2s delay)"
	python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --start-page 1 --end-page 111 --delay 2.0 --verbose
	@echo "✅ Jerry Garcia show database collection complete!"

collect-show-image-urls:
	@echo "🎫 Extracting ticket and photo URLs for all shows (no downloads)..."
	python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --collect-images --images-no-download --delay 2.0 --verbose
	@echo "✅ Show image URL extraction complete!"

collect-show-image-files:
	@echo "🎫 Collecting ticket images and photos for all shows..."
	python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --collect-images --delay 1.0 --verbose
	@echo "✅ Show image collection complete!"

# Stage 2a: Minimal Recording Data Generation  
generate-recordings:
	@echo "⭐ Generating minimal recording data from raw Archive cache..."
	python scripts/02-generate-data/process_recordings_minimal.py --verbose
	@echo "✅ Minimal recording data generation complete!"

# Stage 2b: Show Integration
integrate-shows:
	@echo "🎭 Integrating JG shows with recording data..."
	python scripts/02-generate-data/integrate_jerry_garcia_shows.py --verbose
	@echo "✅ Show integration complete!"

# Stage 2c: Collections Processing
process-collections:
	@echo "📚 Processing collections and adding to shows..."
	python scripts/02-generate-data/process_collections.py --verbose
	@echo "✅ Collections processing complete!"


# Stage 4: Data Packaging
package-data:
	@echo "📦 Packaging all processed data for distribution..."
	python scripts/package_datazip.py --output data.zip --verbose
	@echo "✅ Data packaging complete! Final package: data.zip"

# Versioned packaging targets
package-data-versioned:
	@echo "📦 Creating versioned data package with auto-detected version..."
	python scripts/package_datazip.py --auto-version --verbose
	@echo "✅ Versioned package created!"

package-release:
	@echo "📦 Creating release package..."
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION not specified. Usage: make package-release VERSION=2.1.0"; \
		exit 1; \
	fi
	python scripts/package_datazip.py --version $(VERSION) --verbose
	@echo "✅ Release package v$(VERSION) created!"

package-dev:
	@echo "📦 Creating development build package..."
	python scripts/package_datazip.py --dev-build --verbose
	@echo "✅ Development package created!"

# Stage-based targets
stage01-collect-data: collect-archive-data collect-jerrygarcia-shows
	@echo "🎉 Stage 1: Data Collection complete!"

stage02-generate-data: generate-recordings integrate-shows process-collections
	@echo "🎉 Stage 2: Data Generation complete!"

# Full pipeline
all: stage01-collect-data stage02-generate-data package-data
	@echo "🎉 Complete pipeline finished!"

# Release Management
release:
	@echo "🚀 Creating GitHub release..."
	@$(call check_gh_cli)
	@$(call check_git_clean)
	@DETECTED_VERSION=$$(scripts/detect_version.sh $(VERSION)); \
	echo "📋 Release version: $$DETECTED_VERSION"; \
	echo "📝 Release notes preview:"; \
	scripts/generate_release_notes.sh $$DETECTED_VERSION; \
	echo ""; \
	read -p "🤔 Create release v$$DETECTED_VERSION? [y/N] " confirm && [ "$$confirm" = "y" ]; \
	echo "🏷️  Creating git tag v$$DETECTED_VERSION..."; \
	git tag -a "v$$DETECTED_VERSION" -m "Release v$$DETECTED_VERSION"; \
	git push origin "v$$DETECTED_VERSION"; \
	echo "📡 Creating GitHub release..."; \
	scripts/generate_release_notes.sh $$DETECTED_VERSION | gh release create "v$$DETECTED_VERSION" --title "Release v$$DETECTED_VERSION" --notes-file -; \
	echo "✅ Release v$$DETECTED_VERSION created! The GitHub Actions workflow will build and attach the data package."

release-dry-run:
	@echo "🔍 Dry-run: Showing what would be released..."
	@$(call check_gh_cli)
	@$(call check_git_clean)
	@DETECTED_VERSION=$$(scripts/detect_version.sh $(VERSION)); \
	echo "📋 Would create release: v$$DETECTED_VERSION"; \
	echo "📝 Release notes would be:"; \
	scripts/generate_release_notes.sh $$DETECTED_VERSION; \
	echo ""; \
	echo "🏷️  Git tag: v$$DETECTED_VERSION"; \
	echo "💡 Run 'make release' to actually create the release"

# Helper functions for release management
define check_gh_cli
	@command -v gh >/dev/null 2>&1 || { echo "❌ GitHub CLI (gh) is required but not installed. Visit https://cli.github.com/"; exit 1; }
	@gh auth status >/dev/null 2>&1 || { echo "❌ GitHub CLI not authenticated. Run 'gh auth login'"; exit 1; }
endef

define check_git_clean
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "❌ Working directory is not clean. Please commit or stash changes first."; \
		git status --short; \
		exit 1; \
	fi
endef


# Cleanup
clean:
	@echo "🧹 Cleaning generated data..."
	rm -rf stage02-generated-data/
	@echo "✅ Cleanup complete!"
