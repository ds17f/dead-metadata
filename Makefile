# Dead Archive Metadata Collection Pipeline
# Comprehensive data processing for Grateful Dead concert metadata

.PHONY: help setup test-pipeline generate-ratings-from-cache collect-metadata-full collect-metadata-test collect-metadata-1977 collect-metadata-1995 collect-setlists-full collect-gdsets-full merge-setlists process-venues process-songs integrate-setlists package-datazip clean

# Default target
help:
	@echo "Dead Archive Metadata Pipeline - Available Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make setup              - Set up Python environment and dependencies"
	@echo ""
	@echo "Pipeline (Using Existing Cache):"
	@echo "  make test-pipeline      - Full pipeline using cached API data (~1 hour)"
	@echo "  make generate-ratings-from-cache - Generate ratings from existing cache"
	@echo ""
	@echo "Data Collection (Long Running):"
	@echo "  make collect-metadata-full - Full metadata collection (2-3 hours)"
	@echo "  make collect-metadata-test - Test collection (10 recordings)"
	@echo "  make collect-metadata-1977 - Collect 1977 shows (golden year)"
	@echo "  make collect-metadata-1995 - Collect 1995 shows (final year)"
	@echo ""
	@echo "Setlist Processing:"
	@echo "  make collect-setlists-full - Collect all setlists from CMU (1972-1995)"
	@echo "  make collect-gdsets-full   - Collect all setlists and images from GDSets"
	@echo "  make merge-setlists        - Merge CMU and GDSets setlist data"
	@echo ""
	@echo "Data Processing:"
	@echo "  make process-venues        - Process and normalize venue data"
	@echo "  make process-songs         - Process and normalize song data"  
	@echo "  make integrate-setlists    - Integrate setlists with venue and song IDs"
	@echo ""
	@echo "Output:"
	@echo "  make package-datazip       - Package all metadata into data.zip"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean                 - Clean temporary files and virtual environment"

# Setup Python environment
setup:
	@echo "🐍 Setting up Python environment for metadata processing..."
	@cd scripts && \
		rm -rf .venv && \
		python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt
	@echo "✅ Python environment setup complete!"

# Test pipeline using existing cache (fast)
test-pipeline:
	@echo "🚀 Running complete metadata pipeline using cached data..."
	make generate-ratings-from-cache
	make collect-setlists-full  
	make collect-gdsets-full
	make merge-setlists
	make process-venues
	make process-songs
	make integrate-setlists
	make package-datazip
	@echo "✅ Complete metadata pipeline finished!"

# Generate ratings from existing cache
generate-ratings-from-cache:
	@echo "📊 Generating ratings from cached metadata..."
	@cd scripts && \
		. .venv/bin/activate || (python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt) && \
		python generate_metadata.py \
		--mode ratings-only \
		--cache "$(PWD)/cache" \
		--output "$(PWD)/ratings.json" \
		--verbose
	@echo "✅ Ratings generation from cache complete!"

# Full metadata collection (2-3 hours)
collect-metadata-full:
	@echo "⭐ Collecting complete Grateful Dead metadata from Archive.org..."
	@cd scripts && \
		rm -rf .venv && \
		python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt && \
		python generate_metadata.py \
		--mode full \
		--delay 0.25 \
		--cache "$(PWD)/cache" \
		--output "$(PWD)/ratings.json" \
		--verbose
	@echo "✅ Complete metadata collection finished!"

# Test collection (small subset)
collect-metadata-test:
	@echo "🧪 Testing metadata collection with small subset..."
	@cd scripts && \
		rm -rf .venv && \
		python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt && \
		python generate_metadata.py \
		--mode test \
		--delay 0.25 \
		--cache "$(PWD)/cache-test" \
		--output "$(PWD)/ratings-test.json" \
		--max-recordings 10 \
		--verbose
	@echo "✅ Test metadata collection finished!"

# Collect 1977 data specifically (golden year)
collect-metadata-1977:
	@echo "🎸 Collecting 1977 Grateful Dead metadata (the golden year)..."
	@cd scripts && \
		rm -rf .venv && \
		python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt && \
		python generate_metadata.py \
		--mode full \
		--year 1977 \
		--delay 0.5 \
		--cache "$(PWD)/cache-1977" \
		--output "$(PWD)/ratings-1977.json" \
		--verbose
	@echo "✅ 1977 metadata collection finished!"

# Collect 1995 data specifically (final year)
collect-metadata-1995:
	@echo "🌹 Collecting 1995 Grateful Dead metadata (the final year)..."
	@cd scripts && \
		rm -rf .venv && \
		python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt && \
		python generate_metadata.py \
		--mode full \
		--year 1995 \
		--delay 0.5 \
		--cache "$(PWD)/cache-1995" \
		--output "$(PWD)/ratings-1995.json" \
		--verbose
	@echo "✅ 1995 metadata collection finished!"

# Setlist Collection
collect-setlists-full:
	@echo "⭐ Collecting complete Grateful Dead setlists from CS.CMU.EDU..."
	@cd scripts && \
		. .venv/bin/activate || (python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt) && \
		python scrape_cmu_setlists.py \
		--output "$(PWD)/cmu_setlists.json" \
		--delay 0.5 \
		--verbose
	@echo "✅ Complete setlist collection finished!"

# GDSets Collection
collect-gdsets-full:
	@echo "⭐ Extracting Grateful Dead setlists and images from GDSets HTML..."
	@cd scripts && \
		. .venv/bin/activate || (python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt) && \
		python scrape_gdsets.py \
		--output-setlists "$(PWD)/gdsets_setlists.json" \
		--output-images "$(PWD)/images.json" \
		--focus-years 1965-1995 \
		--verbose
	@echo "✅ Complete GDSets extraction finished!"

# Setlist Merging
merge-setlists:
	@echo "🔄 Merging CMU and GDSets setlist data..."
	@cd scripts && \
		. .venv/bin/activate || (python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt) && \
		python merge_setlists.py \
		--cmu "$(PWD)/cmu_setlists.json" \
		--gdsets "$(PWD)/gdsets_setlists.json" \
		--output "$(PWD)/raw_setlists.json" \
		--verbose
	@echo "✅ Setlist merge completed!"

# Venue Processing
process-venues:
	@echo "🏛️ Processing venue data from merged setlists..."
	@cd scripts && \
		. .venv/bin/activate || (python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt) && \
		python process_venues.py \
		--input "$(PWD)/raw_setlists.json" \
		--output "$(PWD)/venues.json" \
		--verbose
	@echo "✅ Venue processing completed!"

# Song Processing
process-songs:
	@echo "🎵 Processing song data from merged setlists..."
	@cd scripts && \
		. .venv/bin/activate || (python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt) && \
		python process_songs.py \
		--input "$(PWD)/raw_setlists.json" \
		--output "$(PWD)/songs.json" \
		--verbose
	@echo "✅ Song processing completed!"

# Setlist Integration  
integrate-setlists:
	@echo "🔗 Integrating setlists with venue and song IDs..."
	@cd scripts && \
		. .venv/bin/activate || (python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt) && \
		python integrate_setlists.py \
		--setlists "$(PWD)/raw_setlists.json" \
		--venues "$(PWD)/venues.json" \
		--songs "$(PWD)/songs.json" \
		--output "$(PWD)/setlists.json" \
		--verbose
	@echo "✅ Setlist integration completed!"

# Data Packaging
package-datazip:
	@echo "📦 Packaging metadata into data.zip for app deployment..."
	@cd scripts && \
		. .venv/bin/activate || (python3 -m venv .venv && \
		. .venv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip install -r requirements.txt) && \
		python package_datazip.py \
		--ratings "$(PWD)/ratings.json" \
		--setlists "$(PWD)/setlists.json" \
		--venues "$(PWD)/venues.json" \
		--songs "$(PWD)/songs.json" \
		--output "$(PWD)/data.zip" \
		--verbose
	@echo "✅ Data packaging completed!"

# Cleanup
clean:
	@echo "🧹 Cleaning up temporary files..."
	@rm -rf scripts/.venv
	@rm -f raw_setlists.json
	@rm -f ratings-test.json
	@rm -f ratings-1977.json  
	@rm -f ratings-1995.json
	@rm -rf cache-test cache-1977 cache-1995
	@echo "✅ Cleanup completed!"