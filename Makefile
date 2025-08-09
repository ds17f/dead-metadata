# Grateful Dead Archive Data Pipeline
# Stage-based data collection and processing

.PHONY: help stage01-collect-data stage02-generate-data collect-archive-data collect-jerrygarcia-shows generate-recording-ratings integrate-shows all clean

# Default help
help:
	@echo "🎵 Grateful Dead Archive Data Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  stage01-collect-data      - Run complete Stage 1: Data Collection (5-7 hours)"
	@echo "  stage02-generate-data     - Run complete Stage 2: Data Generation (fast)"
	@echo "  collect-archive-data      - Collect metadata from Archive.org (2-3 hours)"
	@echo "  collect-jerrygarcia-shows - Collect complete show database from jerrygarcia.com (3-4 hours)"
	@echo "  generate-recording-ratings- Generate comprehensive recording ratings from cache"
	@echo "  integrate-shows           - Integrate JG shows with recording ratings"
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

# Stage-based targets
stage01-collect-data: collect-archive-data collect-jerrygarcia-shows
	@echo "🎉 Stage 1: Data Collection complete!"

stage02-generate-data: generate-recording-ratings integrate-shows
	@echo "🎉 Stage 2: Data Generation complete!"

# Full pipeline
all: stage01-collect-data stage02-generate-data
	@echo "🎉 Complete pipeline finished!"

# Cleanup
clean:
	@echo "🧹 Cleaning generated data..."
	rm -rf stage02-generated-data/
	@echo "✅ Cleanup complete!"