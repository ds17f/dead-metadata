# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production-ready Grateful Dead concert metadata collection and processing pipeline that transforms raw data from multiple sources into a comprehensive, normalized database suitable for mobile app consumption.

**Coverage**: 2,200+ shows (1965-1995), 484+ venues, 550+ songs with comprehensive ratings data  
**Status**: Production V1 system actively used by Android app, ready for V2 architecture integration  
**Pipeline**: 4-stage service-oriented architecture with 6,242+ lines of Python code across 12 specialized scripts

## Architecture

The pipeline follows a 4-stage service-oriented architecture:

### Stage 1: Data Collection
- **Archive.org**: `generate_metadata.py` (769 lines) - Collects 17,790+ recording metadata files with ratings
- **CMU Setlists**: `scrape_cmu_setlists.py` (590 lines) - 1,604 shows with structured setlist data (1972-1995)  
- **GDSets**: `scrape_gdsets.py` (665 lines) - 1,961 shows with focus on early years (1965-1971)

### Stage 2: Data Processing
- **Setlist Merging**: `merge_setlists.py` (489 lines) - Combines sources with GDSets priority
- **Venue Normalization**: `process_venues.py` (727 lines) - 484+ venues with smart name normalization
- **Song Processing**: `process_songs.py` (643 lines) - 550+ songs with alias and segue handling

### Stage 3: Integration
- **Final Integration**: `integrate_setlists.py` (574 lines) - Creates ID-referenced final database

### Stage 4: Deployment  
- **Data Packaging**: `package_datazip.py` (196 lines) - Bundles into compressed mobile-ready package

Key files are stored in `/scripts/` and final outputs (JSON files) are in the project root.

## Common Development Commands

All development is managed through the Makefile. Key commands:

### Setup
```bash
make setup                    # Set up Python virtual environment and dependencies
```

### Quick Development (Uses Cached Data)
```bash
make test-pipeline           # Complete pipeline using cached API responses (~1 hour)
make generate-ratings-from-cache  # Generate ratings from existing cache
```

### Full Data Collection (Long Running)
```bash
make collect-metadata-full   # Full metadata collection from Archive.org (2-3 hours)
make collect-metadata-test   # Test with 10 recordings only
make collect-metadata-1977   # Collect just 1977 shows
make collect-metadata-1995   # Collect just 1995 shows
```

### Setlist Processing
```bash
make collect-setlists-full   # Scrape CMU setlist database
make collect-gdsets-full     # Extract from GDSets HTML
make merge-setlists         # Merge CMU and GDSets data
```

### Data Processing Pipeline
```bash
make process-venues         # Normalize venue data
make process-songs          # Normalize song data  
make integrate-setlists     # Link setlists with IDs
make package-datazip        # Create final data.zip
```

### Testing/Validation
The project doesn't have a traditional test suite. Validation is done through:
- Data integrity checks in each processing script
- Manual review of output JSON files
- Statistics logging during processing

## Key Data Sources

- **Archive.org**: Concert recordings, ratings, and technical metadata
- **CS.CMU.EDU**: Historical setlist database (1972-1995)
- **GDSets**: Setlist data and concert images

## Important Implementation Details

- All scripts run in a Python virtual environment (`.venv`) created in `/scripts/`
- API requests are rate-limited (0.25-0.5 second delays) to be respectful to servers
- Large metadata cache is stored locally for development, simplified ratings exported for apps
- Data processing is idempotent - can be run multiple times safely
- Progress tracking and resume functionality for long-running collection jobs

## Data Flow and Quality Metrics

### Pipeline Execution Order
1. `generate_metadata.py` - Collects Archive.org metadata/ratings → `ratings.json`
2. `scrape_cmu_setlists.py` - Scrapes CMU database → `cmu_setlists.json`  
3. `scrape_gdsets.py` - Extracts GDSets data → `gdsets_setlists.json` + `images.json`
4. `merge_setlists.py` - Combines setlist sources → `raw_setlists.json`
5. `process_venues.py` - Normalizes venues → `venues.json`
6. `process_songs.py` - Normalizes songs → `songs.json`
7. `integrate_setlists.py` - Links everything → `setlists.json`
8. `package_datazip.py` - Creates final bundle → `data.zip`

### Quality Assurance
- **Song Match Rate**: 99.995% successful song identification
- **Venue Match Rate**: 100% venue identification and normalization  
- **Source Priority**: GDSets data preferred over CMU for superior quality
- **Data Completeness**: Comprehensive coverage of Grateful Dead's performing years (1965-1995)

### Performance Metrics
- **Full Pipeline**: 3-5 hours (includes API collection)
- **Cache-Based Pipeline**: ~1 hour (using existing `cache/api/` data)
- **Archive.org Collection**: 2-3 hours (rate-limited, resumable)
- **Data Processing**: 15-30 minutes (normalization and integration)
- **Final Output**: 2-5MB compressed for mobile deployment

## Working with the Codebase

### Dependencies and Environment
- **Python Requirements**: requests==2.31.0, lxml==4.9.3, beautifulsoup4==4.12.2, python-dateutil>=2.8.0
- **Virtual Environment**: Created in `/scripts/.venv/` by Makefile targets
- **Storage Requirements**: ~5GB working storage, 500MB metadata cache, 2-5MB final output

### Development Practices
- All scripts accept command-line arguments with `--verbose` flag for detailed logging
- Rate limiting (0.25-0.5s delays) implemented for respectful API usage
- Resume capability and progress tracking for long-running collection jobs
- Comprehensive error handling and data validation at each stage
- Cache directory structure in `/cache/api/` preserves API responses for development/debugging

### Data Models and Structure
- **RecordingMetadata**: Archive.org metadata with weighted ratings, review statistics
- **Venue Database**: Normalized venue data with geographical information and aliases
- **Song Database**: Song relationships, aliases, segue notation, performance statistics
- **Collections Framework**: Pre-defined collections in `dead_collections.json` ready for V2 implementation

### Integration Points
- **V1 Android App**: Currently consumes `data.zip` package from this pipeline
- **V2 Architecture**: Pipeline outputs provide exact data needed for V2 database entities
- **API Endpoints**: Can be enhanced to output V2-specific formats
- **Maintenance Schedule**: Quarterly Archive.org updates, annual venue/song refinements