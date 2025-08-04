# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a comprehensive Grateful Dead concert metadata collection and processing pipeline that scrapes and aggregates data from multiple sources (Archive.org, CS.CMU.EDU, GDSets) to create structured datasets about Dead concerts from 1965-1995.

## Architecture

The project follows a multi-stage data pipeline architecture:

1. **Data Collection**: Scrapes metadata, ratings, and setlists from various sources
2. **Data Processing**: Normalizes venues, songs, and setlists into structured formats  
3. **Data Integration**: Links setlists with venue/song IDs and creates final datasets
4. **Data Packaging**: Bundles all data into a single ZIP file for app distribution

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

## Data Flow

1. `generate_metadata.py` - Collects Archive.org metadata/ratings → `ratings.json`
2. `scrape_cmu_setlists.py` - Scrapes CMU database → `cmu_setlists.json`  
3. `scrape_gdsets.py` - Extracts GDSets data → `gdsets_setlists.json` + `images.json`
4. `merge_setlists.py` - Combines setlist sources → `raw_setlists.json`
5. `process_venues.py` - Normalizes venues → `venues.json`
6. `process_songs.py` - Normalizes songs → `songs.json`
7. `integrate_setlists.py` - Links everything → `setlists.json`
8. `package_datazip.py` - Creates final bundle → `data.zip`

## Working with the Codebase

- Python dependencies are minimal: requests, lxml, beautifulsoup4, python-dateutil
- All scripts accept command-line arguments with `--verbose` flag for detailed logging
- Cache directory structure preserves API responses for development/debugging
- JSON output files follow consistent schemas across the pipeline