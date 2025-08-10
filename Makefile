# Grateful Dead Archive Data Pipeline
# Stage-based data collection and processing

.PHONY: help stage01-collect-data stage02-generate-data stage03-generate-search-data collect-archive-data collect-jerrygarcia-shows generate-recording-ratings integrate-shows process-collections generate-search-data analyze-search-data package-data all clean

# Default help
help:
	@echo "🎵 Grateful Dead Archive Data Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  stage01-collect-data      - Run complete Stage 1: Data Collection (5-7 hours)"
	@echo "  stage02-generate-data     - Run complete Stage 2: Data Generation (fast)"
	@echo "  stage03-generate-search-data - Run complete Stage 3: Search Data Generation (fast)"
	@echo "  collect-archive-data      - Collect metadata from Archive.org (2-3 hours)"
	@echo "  collect-jerrygarcia-shows - Collect complete show database from jerrygarcia.com (3-4 hours)"
	@echo "  generate-recording-ratings- Generate comprehensive recording ratings from cache"
	@echo "  integrate-shows           - Integrate JG shows with recording ratings"
	@echo "  process-collections       - Process collections and add to shows"
	@echo "  generate-search-data      - Generate denormalized search tables for mobile app"
	@echo "  analyze-search-data       - Development tool: analyze data patterns (manual use)"
	@echo "  package-data              - Package all processed data into data.zip for distribution"
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

# Stage 2a: Recording Ratings Generation  
generate-recording-ratings:
	@echo "⭐ Generating comprehensive recording ratings from Archive cache..."
	python scripts/02-generate-data/generate_recording_ratings.py --verbose
	@echo "✅ Recording ratings generation complete!"

# Stage 2b: Show Integration
integrate-shows:
	@echo "🎭 Integrating JG shows with recording ratings..."
	python scripts/02-generate-data/integrate_jerry_garcia_shows.py --verbose
	@echo "✅ Show integration complete!"

# Stage 2c: Collections Processing
process-collections:
	@echo "📚 Processing collections and adding to shows..."
	python scripts/02-generate-data/process_collections.py --verbose
	@echo "✅ Collections processing complete!"

# Stage 3: Search Data Generation
generate-search-data:
	@echo "🔍 Generating denormalized search tables for mobile app..."
	python scripts/03-search-data/generate_search_tables.py --verbose
	@echo "✅ Search data generation complete!"

# Development tools (run manually as needed)
analyze-search-data:
	@echo "🔍 Analyzing search data patterns (development tool)..."
	python scripts/03-search-data/analyze_search_data.py --verbose
	@echo "✅ Search data analysis complete!"

# Stage 4: Data Packaging
package-data:
	@echo "📦 Packaging all processed data for distribution..."
	python scripts/package_datazip.py --output data.zip --verbose
	@echo "✅ Data packaging complete! Final package: data.zip"

# Stage-based targets
stage01-collect-data: collect-archive-data collect-jerrygarcia-shows
	@echo "🎉 Stage 1: Data Collection complete!"

stage02-generate-data: generate-recording-ratings integrate-shows process-collections
	@echo "🎉 Stage 2: Data Generation complete!"

stage03-generate-search-data: generate-search-data
	@echo "🎉 Stage 3: Search Data Generation complete!"

# Full pipeline
all: stage01-collect-data stage02-generate-data stage03-generate-search-data package-data
	@echo "🎉 Complete pipeline finished!"

# Cleanup
clean:
	@echo "🧹 Cleaning generated data..."
	rm -rf stage02-generated-data/
	@echo "✅ Cleanup complete!"