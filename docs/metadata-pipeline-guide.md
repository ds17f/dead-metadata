# Dead Archive Metadata Pipeline Guide

## Overview

This guide documents the complete metadata collection and processing pipeline for the Dead Archive project. The system transforms raw data from multiple sources into a comprehensive, normalized database suitable for mobile app consumption.

**Current Status**: Production V1 system with 6,242 lines of Python code across 12 specialized scripts  
**V2 Integration**: This pipeline will feed into the V2 database architecture as the primary data source  
**Coverage**: 2,200+ shows (1965-1995), 484+ venues, 550+ songs with comprehensive ratings data

## Pipeline Architecture

The metadata pipeline follows a 4-stage service-oriented architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Archive.org   │    │   CS.CMU.EDU     │    │   GDSets.com    │
│   (Ratings &    │    │   (Setlists      │    │   (Early Shows  │
│   Metadata)     │    │   1972-1995)     │    │   & Images)     │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          ▼                      ▼                       ▼
    STAGE 1: DATA COLLECTION
          │                      │                       │
          ▼                      ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│generate_metadata│    │scrape_cmu_setlists│    │ scrape_gdsets   │
│   (769 lines)   │    │   (590 lines)    │    │   (665 lines)   │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          ▼                      └───────┬───────────────┘
    STAGE 2: DATA PROCESSING             ▼
          │                    ┌──────────────────┐
          │                    │  merge_setlists  │
          │                    │   (489 lines)    │
          │                    └─────────┬────────┘
          │                              ▼
          │                    ┌──────────────────┐
          │                    │  raw_setlists    │
          │                    │     .json        │
          │                    └─────────┬────────┘
          │                              │
          │      ┌───────────────────────┼───────────────────────┐
          │      ▼                       ▼                       ▼
          │ ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
          │ │ process_venues   │  │ process_songs    │  │ process_images   │
          │ │   (727 lines)    │  │   (643 lines)    │  │   (453 lines)    │
          │ └─────────┬────────┘  └─────────┬────────┘  └─────────┬────────┘
          │           ▼                     ▼                     ▼
          │ ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
          │ │   venues.json    │  │   songs.json     │  │  images.json     │
          │ └─────────┬────────┘  └─────────┬────────┘  └──────────────────┘
          │           │                     │
          │           └───────┬─────────────┘
          │                   ▼
          │         STAGE 3: INTEGRATION
          │                   ▼
          │         ┌──────────────────┐
          │         │ integrate_setlists│
          │         │   (574 lines)    │
          │         └─────────┬────────┘
          │                   ▼
          │         ┌──────────────────┐
          │         │  setlists.json   │
          │         │    (final)       │
          │         └─────────┬────────┘
          │                   │
          └───────────────────┼───────────────────────┐
                              ▼                       │
                    STAGE 4: DEPLOYMENT               │
                              ▼                       │
                    ┌──────────────────┐              │
                    │ package_datazip  │              │
                    │   (196 lines)    │              │
                    └─────────┬────────┘              │
                              ▼                       │
                    ┌──────────────────┐              │
                    │    data.zip      │◀─────────────┘
                    │  (app assets)    │
                    └──────────────────┘
```

## Complete Metadata Creation Sequence

### Prerequisites

**Environment Setup**:
```bash
# Python environment
python3 -m venv scripts/venv
source scripts/venv/bin/activate
pip install -r scripts/requirements.txt

# Directory structure
mkdir -p scripts/metadata/{recordings,shows}
mkdir -p scripts/setlists
mkdir -p scripts/processed
```

**Dependencies** (`scripts/requirements.txt`):
- `requests==2.31.0` - HTTP client for Archive.org API
- `lxml==4.9.3` - XML/HTML parsing for web scraping
- `python-dateutil>=2.8.0` - Date normalization
- `beautifulsoup4==4.12.2` - HTML parsing for setlists

### Execution Options

#### Option A: Full Automated Pipeline
```bash
# Single command runs complete pipeline (3-5 hours)
make collect-all-data
```

#### Option B: Manual Step-by-Step (Recommended for first run)

##### Phase 1: Data Collection (2-4 hours)
```bash
# Stream A: Archive.org metadata (longest running - start first)
make collect-metadata-test        # Test run (10 recordings)
make collect-metadata-1977       # Golden year focus  
make collect-metadata-full       # Complete collection (2-3 hours)

# Stream B: Setlist data (can run parallel to metadata collection)
make collect-setlists-full       # CMU setlists (1972-1995)
make collect-gdsets-full         # GDSets data (1965-1995)
```

##### Phase 2: Data Processing (30 minutes)
```bash
# Step 1: Merge setlist sources (sequential - order critical)
make merge-setlists
# Output: raw_setlists.json

# Step 2: Normalize reference data (parallel execution possible)
make process-venues              # Creates venues.json (484+ venues)
make process-songs               # Creates songs.json (550+ songs)
make process-images              # Creates images.json (optional)

# Step 3: Final integration
make integrate-setlists          # Creates setlists.json with ID references
# Output: Final normalized setlist database
```

##### Phase 3: App Deployment (5 minutes)
```bash
# Generate final package for Android app
make package-datazip
# Output: app/src/main/assets/data.zip (2-5MB compressed)
```

## Data Sources and Coverage

### Archive.org Integration
**Script**: `generate_metadata.py` (769 lines)
- **API**: Archive.org advanced search and metadata endpoints
- **Coverage**: 17,790+ recording metadata files, 3,252+ show metadata files
- **Rate Limiting**: 0.25s delay between API calls (configurable)
- **Features**: Resume capability, progress tracking, weighted rating system
- **Caching**: Local 500MB metadata cache, 2-5MB production output

**Data Models**:
```python
@dataclass
class RecordingMetadata:
    identifier: str
    title: str
    date: str                    # Normalized YYYY-MM-DD
    venue: str
    location: str
    source_type: str             # SBD, AUD, MATRIX, FM, REMASTER
    rating: float                # Weighted rating (0.0-5.0)
    raw_rating: float            # Simple average
    review_count: int
    confidence: float            # Based on review count
    distribution: Dict[int, int] # Star rating distribution {1: 7, 2: 6, ...}
    reviews: List[ReviewData]
    files: List[Dict]            # Archive.org file metadata
```

### CMU Setlist Collection
**Script**: `scrape_cmu_setlists.py` (590 lines)
- **Source**: CS.CMU.EDU Grateful Dead setlist archive
- **Coverage**: 1,604 shows with structured setlist data (1972-1995)
- **Features**: Year-by-year scraping, set separation detection, venue extraction
- **Quality**: Comprehensive post-Pigpen era coverage

### GDSets Data Extraction
**Script**: `scrape_gdsets.py` (665 lines)
- **Source**: GDSets.com HTML files and image metadata
- **Coverage**: 1,961 shows (1965-1995) with focus on early years (1965-1971)
- **Priority**: Superior data quality - takes precedence over CMU for overlapping shows
- **Features**: Image metadata extraction (posters, tickets, programs), early years coverage

## Data Processing Pipeline

### Stage 1: Setlist Merging
**Script**: `merge_setlists.py` (489 lines)
- **Strategy**: GDSets as primary source due to superior quality
- **Conflict Resolution**: GDSets precedence for overlapping dates
- **Normalization**: Set classification (CMU "set3" → "encore")
- **Output**: `raw_setlists.json` - unified setlist database

### Stage 2: Reference Data Processing

#### Venue Normalization
**Script**: `process_venues.py` (727 lines)
- **Purpose**: Create standardized venue reference database
- **Features**: 
  - Smart name normalization ("Fillmore West" variations)
  - City/state/country parsing with international support
  - Duplicate venue detection and merging
  - Geographical data preparation
- **Output**: `venues.json` - 484+ unique venues with statistics

#### Song Processing
**Script**: `process_songs.py` (643 lines)
- **Purpose**: Normalized songs database with relationship mapping
- **Features**:
  - Song name normalization and alias tracking
  - Segue detection ("Scarlet > Fire" relationships)
  - Performance statistics and frequency analysis
  - Historical data (first/last played dates)
- **Output**: `songs.json` - 550+ unique songs with relationships

### Stage 3: Final Integration
**Script**: `integrate_setlists.py` (574 lines)
- **Purpose**: Create ID-referenced final database
- **Features**:
  - Venue and song ID linking for referential integrity
  - Show ID standardization for app integration
  - Date normalization and validation
  - Graceful handling of missing data
- **Output**: `setlists.json` - complete normalized database

### Stage 4: App Deployment
**Script**: `package_datazip.py` (196 lines)
- **Required Inputs**:
  - `ratings.json` - Archive.org ratings and metadata
  - `setlists.json` - Complete setlist database
  - `venues.json` - Venue reference database
  - `songs.json` - Song reference database
- **Output**: `data.zip` - compressed package for Android app assets
- **Optimization**: Size-optimized for mobile deployment

## Collections Framework

**Configuration**: `scripts/dead_collections.json`
Pre-defined collections ready for V2 implementation:

```json
{
  "collections": [
    {
      "id": "acid-tests",
      "name": "The Acid Tests",
      "description": "Early Dead at Ken Kesey's Acid Tests (1965-1966)",
      "show_selector": {"dates": ["1965-11-27", "1965-12-04", ...]}
    },
    {
      "id": "pigpen-years", 
      "name": "The Pigpen Years",
      "description": "Ron McKernan era (1965-1972)",
      "show_selector": {"range": {"start": "1965-05-05", "end": "1972-06-17"}}
    }
  ]
}
```

## Quality Metrics and Performance

### Data Quality Assurance
- **Song Match Rate**: 99.995% successful song identification
- **Venue Match Rate**: 100% venue identification and normalization
- **Source Priority**: GDSets data preferred over CMU for superior quality
- **Rating Confidence**: Weighted system prioritizing SBD recordings with multiple reviews

### Pipeline Performance
- **Total Time**: 3-5 hours for complete pipeline from scratch
- **Archive.org Collection**: 2-3 hours (rate-limited, resumable)
- **Setlist Processing**: 30-60 minutes (3,500+ shows)
- **Data Processing**: 15-30 minutes (normalization and integration)
- **Final Packaging**: < 5 minutes

### Resource Requirements
- **Working Storage**: ~5GB (includes 500MB metadata cache)
- **Final Output**: 2-5MB compressed data.zip
- **Network**: Stable internet for API calls, respectful rate limiting
- **Dependencies**: Python 3.8+, virtual environment recommended

## Output Data Products

### Final Deliverables
1. **`ratings.json`** (2-5MB) - Archive.org ratings with comprehensive review statistics
2. **`setlists.json`** - Complete normalized setlist database with ID references
3. **`venues.json`** - 484+ venue reference database with geographical data
4. **`songs.json`** - 550+ song reference database with relationships and statistics
5. **`data.zip`** - Final compressed package for Android app deployment

### Data Structure Examples

**Show Rating Entry**:
```json
{
  "gd1977-05-08_Barton_Hall": {
    "date": "1977-05-08",
    "venue": "Barton Hall",
    "rating": 4.8,
    "confidence": 0.95,
    "best_recording": "gd1977-05-08.sbd.miller.110987.sbeok.flac16",
    "recording_count": 12
  }
}
```

**Venue Entry**:
```json
{
  "fillmore_west": {
    "name": "Fillmore West",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "aliases": ["The Fillmore West", "Fillmore West Auditorium"],
    "show_count": 58,
    "date_range": {"first": "1968-02-14", "last": "1971-07-04"}
  }
}
```

## V2 Integration Strategy

### Current V1 Status
This metadata pipeline is production-ready and actively used by the V1 Android app. The data structure and quality metrics demonstrate mature, battle-tested data processing.

### V2 Database Integration Path
The pipeline outputs provide the exact data needed for V2 entities:

- **ShowV2Entity**: Date, venue, location from processed setlists
- **VenueV2Entity**: Normalized venue database with geographical data  
- **RecordingV2Entity**: Archive.org metadata with ratings and source types
- **TrackV2Entity**: File information from metadata pipeline
- **CollectionV2Entity**: Pre-defined collections ready for implementation

### Migration Considerations
- Pipeline can be enhanced to output V2-specific formats
- Existing data quality and coverage is suitable for V2 requirements
- Collections framework provides immediate V2 feature support
- Incremental updates and maintenance procedures already established

## Maintenance and Operations

### Regular Maintenance Schedule
- **Archive.org Updates**: Quarterly collection of new recordings and reviews
- **Venue Database**: Annual review and expansion of normalization rules
- **Song Database**: Ongoing refinement of aliases and segue handling
- **Pipeline Optimization**: Continuous improvement of processing speed and data quality

### Error Handling and Recovery
- **Resume Capability**: Interrupted collections can resume from progress files
- **Rate Limiting**: Respectful API usage with configurable delays
- **Validation**: Data quality checks at each processing stage
- **Logging**: Comprehensive error tracking and performance monitoring

### Operational Commands
```bash
# Test pipeline health
make collect-metadata-test

# Incremental updates
make collect-metadata-recent --since 2024-01-01

# Full rebuild (when needed)
make deep-clean && make collect-all-data

# Monitor progress
tail -f scripts/metadata/progress.json
```

---

**Last Updated**: January 2025  
**Pipeline Version**: 1.0.0 (Production)  
**V2 Integration**: Planned for Q1 2025  
**Maintainer**: Dead Archive Development Team

This comprehensive metadata pipeline ensures the Dead Archive application has access to the most complete, accurate, and well-structured dataset of Grateful Dead concert information available, providing the foundation for both current V1 operations and future V2 architecture implementation.