# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production-ready Grateful Dead concert metadata collection and processing pipeline that transforms raw data from multiple sources into a comprehensive, normalized database suitable for mobile app consumption.

**Coverage**: 2,200+ shows (1965-1995), 484+ venues, 550+ songs with comprehensive ratings data  
**Status**: Production V1 system actively used by Android app, ready for V2 architecture integration  
**Pipeline**: 4-stage service-oriented architecture with 6,812+ lines of Python code across 13 specialized scripts

## Architecture

The pipeline follows a 4-stage service-oriented architecture with clear separation between raw collected data and processed derivatives:

### Stage 1: Data Collection → `stage01-collected-data/`
- **Archive.org**: `scripts/01-collect-data/collect_archive_metadata.py` (661 lines) - Collects 17,790+ recording metadata files with ratings → `archive/`
- **Jerry Garcia Shows**: `scripts/01-collect-data/collect_jerrygarcia_com_shows.py` (1,100+ lines) - Complete Grateful Dead show database with setlists, venues, lineups → `jerrygarcia/`
- **CMU Setlists**: `scrape_cmu_setlists.py` (590 lines) - 1,604 shows with structured setlist data (1972-1995) → `cmu/`
- **GDSets**: `scrape_gdsets.py` (665 lines) - 1,961 shows with focus on early years (1965-1971) → `gdsets/`

### Stage 2: Data Generation → `stage02-generated-data/` + `stage02-processed-data/`
- **Archive.org Processing**: `scripts/02-generate-data/generate_archive_products.py` (362 lines) - Processes cached Archive.org data → `stage02-generated-data/ratings.json` + `shows/`
- **Jerry Garcia Integration**: `scripts/02-generate-data/integrate_jerry_garcia_shows.py` - Integrates JG shows with recording ratings → enhanced `shows/`
- **Collections Processing**: `scripts/02-generate-data/process_collections.py` (570 lines) - Resolves collection selectors to show IDs, adds collection metadata to shows → `collections.json`
- **Setlist Merging**: `merge_setlists.py` (489 lines) - Combines CMU + GDSets sources with GDSets priority → `raw_setlists.json`
- **Venue Normalization**: `process_venues.py` (727 lines) - 484+ venues with smart name normalization → `venues.json`
- **Song Processing**: `process_songs.py` (643 lines) - 550+ songs with alias and segue handling → `songs.json`

### Stage 3: Search Data Generation → `stage03-search-data/`
- **Search Tables**: `scripts/03-search-data/generate_search_tables.py` - Generates denormalized search indexes for mobile app optimization
- **Collections Search**: Auto-generated from Stage 2 collections processing for search integration
- **Final Integration**: `integrate_setlists.py` (574 lines) - Links setlists with venue/song IDs → `setlists.json`

### Stage 4: Deployment
- **Data Packaging**: `package_datazip.py` (196 lines) - Bundles processed data into compressed mobile-ready package → `data.zip`

**Key Insight**: Archive.org data and setlist data remain **separate streams** - Archive data provides ratings, setlist data provides concert structure. They are not integrated, serving different app functions.

## Common Development Commands

All development is managed through the Makefile. Key commands:

### Data Collection Pipeline
```bash
make collect-archive-data      # Collect metadata from Archive.org (2-3 hours)
make collect-jerrygarcia-shows # Collect complete show database from jerrygarcia.com (3-4 hours)
make generate-recording-ratings# Generate comprehensive recording ratings from cache
make integrate-shows           # Integrate JG shows with recording ratings
make process-collections       # Process collections and add to shows
make generate-search-data      # Generate denormalized search tables for mobile app
make all                       # Run complete pipeline
make clean                     # Clean generated data
```

### Individual Script Usage
```bash
# Collection with custom options
python scripts/01-collect-data/collect_archive_metadata.py --mode test --max-recordings 10
python scripts/01-collect-data/collect_archive_metadata.py --year 1977 --verbose

# Generation with custom options  
python scripts/02-generate-data/generate_archive_products.py --shows-only
python scripts/02-generate-data/generate_archive_products.py --ratings-only
python scripts/02-generate-data/generate_archive_products.py --input-dir custom-cache

# Collections processing
python scripts/02-generate-data/process_collections.py --verbose
python scripts/02-generate-data/process_collections.py --collections-file custom-collections.json

# Search data generation
python scripts/03-search-data/generate_search_tables.py --verbose
python scripts/03-search-data/generate_search_tables.py --analyze

# Jerry Garcia show collection with custom options
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --start-page 50 --end-page 60 --delay 3.0
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --retry-failed --max-retries 5
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --fix-venues --verbose
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --fix-venues-dry-run
```

### Legacy Pipeline Commands (Setlist Processing)
```bash
# Individual script usage for setlist processing
python scripts/scrape_cmu_setlists.py --output cmu_setlists.json
python scripts/scrape_gdsets.py --output-setlists gdsets_setlists.json
python scripts/merge_setlists.py --cmu cmu.json --gdsets gdsets.json --output merged.json
python scripts/process_venues.py --input raw_setlists.json --output venues.json
python scripts/process_songs.py --input raw_setlists.json --output songs.json
python scripts/integrate_setlists.py --setlists raw.json --venues venues.json --songs songs.json --output final.json
python scripts/package_datazip.py --ratings ratings.json --setlists setlists.json --output data.zip
```

### Testing/Validation
The project doesn't have a traditional test suite. Validation is done through:
- Data integrity checks in each processing script
- Manual review of output JSON files
- Statistics logging during processing

## Key Data Sources

- **Archive.org**: Concert recordings, ratings, and technical metadata
- **jerrygarcia.com**: Definitive Grateful Dead show database with complete setlists, lineups, venues (1965-1995)
- **CS.CMU.EDU**: Historical setlist database (1972-1995)
- **GDSets**: Setlist data and concert images

## Jerry Garcia Show Database System

### Complete Show Collection Features
- **Comprehensive Coverage**: 2,313+ shows (1965-1995) with 99.7% completeness
- **Complete Setlists**: Full song sequences with segue notation (>, →) 
- **Band Lineups**: Member names, instruments, profile images
- **Supporting Acts**: Opening bands and special guests
- **Venue Data**: Name, city, state, country with location parsing
- **Automatic Recovery**: Built-in venue data recovery using filename parsing and reference matching

### Advanced Error Handling
- **500 Error Resilience**: Parses HTML content even from server errors to recover setlists
- **Failure Tracking**: Individual URL logging to `failed_urls.json` with retry capability
- **Automatic Retries**: Built-in exponential backoff for temporary server issues  
- **Resume Capability**: Skip existing files, can interrupt and restart without data loss

### Venue Data Recovery System
- **Filename Parsing**: Extracts venue/date from `YYYY-MM-DD-venue-city-state.json` structure
- **Reference Matching**: Finds other shows at same venue to copy complete venue data
- **Automatic Integration**: Runs after every collection to fix missing venue information
- **Status Tracking**: Flags unfixable venues with `venue_recovery_status` and notes

### Usage Examples
```bash
# Complete database collection (3-4 hours)
make collect-jerrygarcia-shows

# Custom page ranges with retry capability  
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --start-page 50 --end-page 60 --delay 3.0

# Retry failed URLs from previous runs
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --retry-failed --max-retries 5

# Fix missing venue data (automatic after collection, or manual)
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --fix-venues
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --fix-venues-dry-run
```

## Important Implementation Details

- All scripts run in a Python virtual environment (`.venv`) created in `/scripts/`
- API requests are rate-limited (0.25-0.5 second delays) to be respectful to servers
- Large metadata cache is stored locally for development, simplified ratings exported for apps
- Data processing is idempotent - can be run multiple times safely
- Progress tracking and resume functionality for long-running collection jobs

## Data Flow and Quality Metrics

### Pipeline Execution Order

**Stage 1 - Data Collection:**
1. `scripts/01-collect-data/collect_archive_metadata.py` - Archive.org API collection → `stage01-collected-data/archive/`
2. `scrape_cmu_setlists.py` - CMU database scraping → `stage01-collected-data/cmu/cmu_setlists.json`
3. `scrape_gdsets.py` - GDSets HTML extraction → `stage01-collected-data/gdsets/gdsets_setlists.json`

**Stage 2 - Data Processing (Two Parallel Streams):**

*Setlist Stream:*
4. `merge_setlists.py` - Combines CMU + GDSets → `stage02-processed-data/raw_setlists.json`
5. `process_venues.py` - Venue normalization → `stage02-processed-data/venues.json`
6. `process_songs.py` - Song normalization → `stage02-processed-data/songs.json`

*Archive.org Stream:*
4. `scripts/02-generate-data/generate_archive_products.py` - Processes cached Archive.org data → `stage02-generated-data/ratings.json` + `shows/`
5. `scripts/02-generate-data/integrate_jerry_garcia_shows.py` - Integrates JG shows with ratings → enhanced `shows/`
6. `scripts/02-generate-data/process_collections.py` - Resolves collections and adds to shows → `collections.json`

**Stage 3 - Search Data Generation:**
7. `scripts/03-search-data/generate_search_tables.py` - Generate search indexes → `stage03-search-data/`
8. `integrate_setlists.py` - Link setlists with venue/song IDs → `stage02-processed-data/setlists.json`

**Stage 4 - Deployment:**
9. `package_datazip.py` - Bundle all processed data → `data.zip`

**Final Bundle Contains:**
- `ratings.json` (from Archive.org stream in `stage02-generated-data/`)
- `collections.json` (from collections processing in `stage02-generated-data/`)
- `setlists.json` (from setlist stream in `stage02-processed-data/`) 
- `venues.json` + `songs.json` (supporting data in `stage02-processed-data/`)
- Search indexes (from `stage03-search-data/` for mobile app optimization)

**Note**: The two data streams remain independent - ratings provide recording quality data, setlists provide concert structure data.

### Quality Assurance
- **Song Match Rate**: 99.995% successful song identification
- **Venue Match Rate**: 100% venue identification and normalization  
- **Source Priority**: GDSets data preferred over CMU for superior quality
- **Data Completeness**: Comprehensive coverage of Grateful Dead's performing years (1965-1995)

### Performance Metrics
- **Archive.org Collection**: 2-3 hours for full dataset (17,790+ recordings, rate-limited, resumable)
- **Archive.org Generation**: ~8 seconds for complete processing of cached data
- **Legacy Pipeline**: 15-30 minutes (setlist normalization and integration)
- **Full Legacy Pipeline**: 3-5 hours (includes all collection stages)
- **Final Output**: 2-5MB compressed for mobile deployment
- **Cache Storage**: ~500MB for Archive.org metadata cache

## Working with the Codebase

### New Stage-Based Architecture

The Archive.org collection system has been reorganized into a clean two-stage pipeline:

**Collection Stage** (Expensive, Long-Running):
- `scripts/01-collect-data/collect_archive_metadata.py` - Pure Archive.org API collection
- Caches individual recording files to `stage01-collected-data/archive/`
- Progress tracking and resume capability
- Rate-limited and respectful to servers
- Run once: `make collect-archive-data`

**Generation Stage** (Fast, Local Processing):
- `scripts/02-generate-data/generate_archive_products.py` - Processes cached data into outputs
- Creates show aggregations in `stage02-generated-data/shows/`
- Generates app-ready `stage02-generated-data/ratings.json`
- Multiple runs from same cache: `make generate-shows`, `make generate-reviews`

**Shared Data Models**:
- `scripts/shared/models.py` - Consistent dataclasses across both scripts
- Ensures compatibility between collection and generation stages

### Dependencies and Environment
- **Python Requirements**: requests==2.31.0, lxml==4.9.3, beautifulsoup4==4.12.2, python-dateutil>=2.8.0
- **Virtual Environment**: Created in `/scripts/.venv/` by Makefile targets
- **Storage Requirements**: ~5GB working storage, 500MB metadata cache, 2-5MB final output

### Development Practices
- All scripts accept command-line arguments with `--verbose` flag for detailed logging
- Rate limiting (0.25-0.5s delays) implemented for respectful API usage
- Resume capability and progress tracking for long-running collection jobs
- Comprehensive error handling and data validation at each stage
- Stage-based directory structure separates raw collected data (`stage01-collected-data/`) from processed derivatives (`stage02-processed-data/`)

### Data Models and Structure
- **RecordingMetadata**: Archive.org metadata with weighted ratings, review statistics (in `scripts/shared/models.py`)
- **ShowMetadata**: Aggregated show-level data with best recording selection (in `scripts/shared/models.py`)
- **ProgressState**: Collection progress tracking with resume capability (in `scripts/shared/models.py`)
- **Venue Database**: Normalized venue data with geographical information and aliases
- **Song Database**: Song relationships, aliases, segue notation, performance statistics
- **Collections Framework**: Pre-defined collections in `stage00-created-data/dead_collections.json` with automated processing system
- **Collections Data**: Resolved collection selectors with show membership and search optimization

### Integration Points
- **V1 Android App**: Currently consumes `data.zip` package from this pipeline
- **V2 Architecture**: Pipeline outputs provide exact data needed for V2 database entities
- **API Endpoints**: Can be enhanced to output V2-specific formats
- **Maintenance Schedule**: Quarterly Archive.org updates, annual venue/song refinements