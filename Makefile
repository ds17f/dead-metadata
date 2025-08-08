# Grateful Dead Archive Data Pipeline
# Stage-based data collection and processing

.PHONY: help collect-archive-data collect-jerrygarcia-shows generate-shows generate-reviews all clean

# Default help
help:
	@echo "🎵 Grateful Dead Archive Data Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  collect-archive-data      - Collect metadata from Archive.org (2-3 hours)"
	@echo "  collect-jerrygarcia-shows - Collect complete show database from jerrygarcia.com (3-4 hours)"
	@echo "  generate-shows            - Generate show aggregations from cache"
	@echo "  generate-reviews          - Generate ratings/reviews from cache"
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

# Stage 2a: Show Generation  
generate-shows:
	@echo "🎭 Generating show-level metadata from cached recordings..."
	python scripts/02-generate-data/generate_archive_products.py --shows-only --verbose
	@echo "✅ Show generation complete!"

# Stage 2b: Reviews Generation
generate-reviews:
	@echo "⭐ Generating ratings and reviews from cached recordings..."
	python scripts/02-generate-data/generate_archive_products.py --ratings-only --verbose
	@echo "✅ Reviews generation complete!"

# Full pipeline
all: collect-archive-data generate-shows generate-reviews
	@echo "🎉 Complete pipeline finished!"

# Cleanup
clean:
	@echo "🧹 Cleaning generated data..."
	rm -rf stage02-generated-data/
	@echo "✅ Cleanup complete!"