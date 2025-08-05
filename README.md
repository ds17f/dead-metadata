# Dead Archive Metadata Repository

This repository contains the complete metadata collection and processing pipeline for the Dead Archive project. It transforms raw data from multiple sources into a comprehensive, normalized database suitable for mobile app consumption.

## Overview

**Purpose**: Separate metadata processing from the main Android app repository  
**Coverage**: 2,200+ shows (1965-1995), 484+ venues, 550+ songs with comprehensive ratings data  
**Pipeline**: 4-stage service-oriented architecture with 6,242+ lines of Python code

## Repository Structure

```
dead-metadata/
├── scripts/                    # Python processing scripts
│   ├── generate_metadata.py   # Archive.org metadata collection (769 lines)
│   ├── scrape_cmu_setlists.py # CMU setlist scraping (590 lines)
│   ├── scrape_gdsets.py       # GDSets data extraction (665 lines)
│   ├── merge_setlists.py      # Setlist merging logic (489 lines)
│   ├── process_venues.py      # Venue normalization (727 lines)
│   ├── process_songs.py       # Song processing (643 lines)
│   ├── integrate_setlists.py  # Final integration (574 lines)
│   ├── package_datazip.py     # Data packaging (196 lines)
│   ├── requirements.txt       # Python dependencies
│   └── dead_collections.json  # Collection definitions
├── cache/                     # Raw API responses (reuse existing)
│   └── api/                   # Archive.org JSON files (thousands)
├── docs/                      # Documentation
│   ├── metadata-pipeline-guide.md     # Complete pipeline guide
│   └── setlist-data-pipeline.md       # Legacy pipeline documentation
├── *.json                     # Processed output files
├── data.zip                   # Final package for Android app
├── Makefile                   # Build automation
└── README.md                  # This file
```

## Quick Start

### Setup Environment
```bash
make setup
```

### Run Complete Pipeline (Using Existing Cache)
```bash
# Fast pipeline using cached API data (~1 hour vs 3-5 hours)
make test-pipeline
```

### Individual Steps
```bash
make generate-ratings-from-cache  # Process existing cache → ratings.json
make collect-setlists-full        # Scrape CMU setlists → cmu_setlists.json  
make collect-gdsets-full          # Extract GDSets data → gdsets_setlists.json
make merge-setlists               # Combine sources → raw_setlists.json
make process-venues               # Normalize venues → venues.json
make process-songs                # Process songs → songs.json
make integrate-setlists           # Final integration → setlists.json
make package-datazip              # Create final package → data.zip
```

## Output Files

The pipeline produces these final data products:

1. **`ratings.json`** (2-5MB) - Archive.org ratings with comprehensive review statistics
2. **`setlists.json`** - Complete normalized setlist database with ID references
3. **`venues.json`** - 484+ venue reference database with geographical data
4. **`songs.json`** - 550+ song reference database with relationships and statistics
5. **`data.zip`** - Final compressed package for Android app deployment

## Integration with Main App

The main Android app repository imports the processed metadata:

```bash
# In main dead repository:
make import-metadata    # Copy data.zip from ../dead-metadata/
make build             # Build app with bundled metadata
```

## Key Features

✅ **Cache-First Testing**: Use existing API responses to avoid 3-5 hour collection time  
✅ **Venue Normalization**: Smart venue processing with duplicate detection and merging  
✅ **Quality Assurance**: 99.995% song match rate, 100% venue identification  
✅ **Production Ready**: Battle-tested pipeline used by V1 Android app  
✅ **V2 Integration**: Data structure ready for V2 database architecture

## Documentation

- **[Complete Pipeline Guide](docs/metadata-pipeline-guide.md)** - Comprehensive documentation
- **[Legacy Pipeline Documentation](docs/setlist-data-pipeline.md)** - Original pipeline design
- **Makefile targets** - Run `make help` for all available commands

## Data Sources

- **Archive.org**: 17,790+ recording metadata files, ratings, and reviews
- **CS.CMU.EDU**: 1,604 shows with structured setlist data (1972-1995)  
- **GDSets.com**: 1,961 shows with focus on early years (1965-1971)

## Performance

- **Full Collection**: 3-5 hours (includes API collection)
- **Cache-Based Pipeline**: ~1 hour (using existing cache/api/ data)
- **Individual Processing**: 5-30 minutes per stage
- **Final Output**: 2-5MB compressed for mobile deployment

---

**Maintainer**: Dead Archive Development Team  
**Last Updated**: January 2025  
**Integration**: Feeds V1 Android app, ready for V2 architecture
