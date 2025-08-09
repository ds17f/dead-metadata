# Grateful Dead Database Pipeline

A comprehensive system for collecting, processing, and integrating Grateful Dead concert data from authoritative sources.

## System Overview

The pipeline creates a complete database of Grateful Dead concerts by combining definitive show information from JerryGarcia.com with recording quality data from Archive.org. The system produces mobile-ready data for the Dead Archive application.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│  JerryGarcia    │    │   Archive.org   │
│     .com        │    │   Recordings    │
│                 │    │                 │
│ • Show Details  │    │ • Ratings       │
│ • Setlists      │    │ • Reviews       │
│ • Lineups       │    │ • Source Types  │
│ • Venues        │    │ • Quality Data  │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          ▼                      ▼
     COLLECTION                 COLLECTION
          │                      │
          ▼                      ▼
┌─────────────────────────────────────────┐
│        stage01-collected-data/          │
│                                         │
│  jerrygarcia/                archive/   │
│  ├── 2,313+ shows             ├── 17,790+ │
│  └── complete data            └── recordings │
└─────────────┬───────────────────────────┘
              │
              ▼
         INTEGRATION
              │
              ▼
┌─────────────────────────────────────────┐
│       stage02-generated-data/           │
│                                         │
│  shows/                    ratings.json │
│  ├── 2,313+ integrated    └── app-ready │
│  └── show files               format    │
└─────────────────────────────────────────┘
```

## Data Sources

### JerryGarcia.com
**Primary Authority for Show Information**

- **Coverage**: Complete Grateful Dead history (1965-1995)
- **Quality**: Single authoritative source, manually curated
- **Content**:
  - Complete setlists with song sequences
  - Segue notation (>, →) showing song connections  
  - Band lineups with member names and instruments
  - Venue information with geographic data
  - Supporting acts and special guests
  - Show timing (early/late show detection)

### Archive.org
**Recording Quality and Community Data**

- **Coverage**: 17,790+ concert recordings with metadata
- **Quality**: Community-driven ratings and reviews
- **Content**:
  - Recording quality ratings (0-5 stars)
  - Source type classification (SBD, AUD, MATRIX, FM)
  - Review counts and confidence metrics
  - Technical metadata (format, lineage, etc.)

## Collection System

### JerryGarcia.com Collection
**Script**: `scripts/01-collect-data/collect_jerrygarcia_com_shows.py`

**Features**:
- Comprehensive crawl of entire show database
- Built-in error recovery and retry logic
- Venue data recovery system for incomplete records
- Progress tracking with resume capability
- Rate limiting for respectful server usage

**Key Capabilities**:
```
Show Data Recovery:
├── Primary extraction from show pages
├── Filename parsing for missing venue data
├── Cross-reference matching with other shows
└── Automatic data completion and validation
```

**Output**: Individual JSON files for each show in `stage01-collected-data/jerrygarcia/`

### Archive.org Collection  
**Script**: `scripts/01-collect-data/collect_archive_metadata.py`

**Features**:
- Archive.org API integration with intelligent pagination
- Weighted rating calculation based on review quality
- Source type detection and classification
- Batch processing with progress tracking
- Resume capability for interrupted collections

**Output**: Individual recording metadata files in `stage01-collected-data/archive/`

## Integration Engine

### Core Integration Script
**Script**: `scripts/02-generate-data/integrate_jerry_garcia_shows.py`

The integration system matches Archive.org recordings to JerryGarcia shows using a multi-level approach:

#### Level 1: Date-Based Grouping
```
Date Parsing & Normalization:
├── Handle multiple date formats (M/D/YYYY, MM/DD/YYYY)
├── Clean contaminated fields (tabs, extra text)
├── Extract show timing information (early/late)
└── Group recordings by normalized date
```

#### Level 2: Time-Based Distribution
```
Show Time Matching:
├── Early Shows ← recordings with "early" markers + non-specific
├── Late Shows  ← recordings with "late" markers + non-specific  
├── Regular     ← all recordings for single-show dates
└── Smart Logic: ambiguous recordings appear in ALL shows
```

#### Level 3: Venue-Based Filtering
```
Venue Matching (when needed):
├── Activate: multiple shows, same date, different venues
├── Normalize venue names for comparison
├── Route recordings by venue similarity scores
└── Fallback: unmatched recordings go to all shows
```

### Advanced Processing Features

#### Show ID Correction
- Detects date mismatches between URL slugs and actual show dates
- Generates corrected IDs using actual venue/date data
- Maintains data integrity while fixing source inconsistencies

#### Source Type Prioritization
```
Recording Selection Hierarchy:
1. FM (Radio broadcast) - Highest quality, broadcast standard
2. SBD (Soundboard) - Professional board recording
3. MATRIX (Mixed sources) - High quality hybrid
4. AUD (Audience) - Variable quality
5. UNKNOWN - Unclassified sources
```

#### Quality Metrics
- Confidence scoring based on review volume and consistency
- Best recording selection using quality and source type
- Statistical analysis of recording distribution per show

## Output Products

### Integrated Show Files
**Location**: `stage02-generated-data/shows/`

Each show contains complete information from both sources:

```json
{
  "show_id": "1977-05-08-cornell-university-ithaca-ny-usa",
  "url": "https://jerrygarcia.com/show/1977-05-08-cornell-university-ithaca-ny-usa/",
  "band": "Grateful Dead",
  "venue": "Barton Hall, Cornell University", 
  "city": "Ithaca",
  "state": "NY",
  "country": "USA",
  "date": "1977-05-08",
  "show_time": null,
  
  "setlist_status": "found",
  "setlist": [
    {
      "set_name": "Set 1",
      "songs": [
        {
          "name": "Minglewood Blues",
          "url": "https://jerrygarcia.com/song/minglewood-blues/",
          "segue_into_next": false
        }
      ]
    }
  ],
  
  "lineup_status": "found", 
  "lineup": [
    {
      "name": "Jerry Garcia",
      "instruments": "guitar, vocals",
      "image_url": "https://cdn.jerrygarcia.com/wp-content/uploads/..."
    }
  ],
  
  "recordings": [
    "gd1977-05-08.sbd.miller.110987.sbeok.flac16",
    "gd1977-05-08.aud.berger.112093.sbeok.flac16"
  ],
  "best_recording": "gd1977-05-08.sbd.miller.110987.sbeok.flac16",
  "avg_rating": 4.8,
  "recording_count": 12,
  "confidence": 1.0,
  "source_types": {
    "SBD": 8,
    "AUD": 4
  },
  
  "matching_method": "date_only",
  "filtering_applied": [],
  "collection_timestamp": "2025-08-09T12:00:00.000000"
}
```

### App-Ready Ratings
**Location**: `stage02-generated-data/ratings.json`

Simplified recording quality data optimized for mobile applications.

## Operation

### Complete Pipeline Execution

#### Stage 1: Data Collection
```bash
# Collect JerryGarcia show database (3-4 hours)
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py

# Collect Archive.org recordings (2-3 hours, can run parallel)  
python scripts/01-collect-data/collect_archive_metadata.py
```

#### Stage 2: Integration & Generation
```bash
# Integrate shows with recordings (< 10 minutes)
python scripts/02-generate-data/integrate_jerry_garcia_shows.py

# Generate app-ready ratings
python scripts/02-generate-data/generate_archive_products.py --ratings-only

# Package for deployment
python scripts/package_datazip.py
```

### Development Workflows

#### Testing Integration
```bash
# Test with limited dataset
python scripts/02-generate-data/integrate_jerry_garcia_shows.py --max-shows 50

# Process specific date range
python scripts/02-generate-data/integrate_jerry_garcia_shows.py \
  --start-date 1977-01-01 --end-date 1977-12-31

# Verbose logging for debugging
python scripts/02-generate-data/integrate_jerry_garcia_shows.py --verbose
```

#### Incremental Updates
```bash
# Update only recent shows
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --start-page 1 --end-page 10

# Retry failed collections
python scripts/01-collect-data/collect_jerrygarcia_com_shows.py --retry-failed
```

## System Capabilities

### Data Quality Features
- **100% Show Coverage**: Complete Grateful Dead performing history
- **Comprehensive Integration**: All Archive recordings matched to shows
- **Data Validation**: Built-in integrity checking and error correction
- **Transparent Processing**: Detailed logging of all matching decisions

### Scalability Features
- **Resume Capability**: Interrupted processes can resume from checkpoints
- **Progress Tracking**: Real-time status monitoring during collection
- **Error Isolation**: Individual failures don't stop overall processing
- **Resource Management**: Memory-efficient processing of large datasets

### Complex Scenario Handling
- **Multiple Shows Per Date**: Smart routing based on timing and venue
- **Early/Late Shows**: Automatic detection and appropriate recording distribution
- **Ambiguous Recordings**: Intelligent fallback strategies ensure no data loss
- **Data Inconsistencies**: Automatic correction of common source data issues

## Monitoring & Operations

### Health Monitoring
```bash
# Quick system health check
python scripts/02-generate-data/integrate_jerry_garcia_shows.py --max-shows 10

# Validate data integrity
python scripts/02-generate-data/integrate_jerry_garcia_shows.py --validate-only
```

### Performance Metrics
- **Collection Time**: 3-4 hours for complete data gathering
- **Integration Time**: < 10 minutes for full show database processing  
- **Storage**: ~500MB working data, ~50MB final output
- **Accuracy**: 100% recording assignment with transparent method reporting

## Technical Specifications

### Dependencies
- **Python 3.8+** with requests, lxml, beautifulsoup4, python-dateutil
- **Network Access** for API calls to JerryGarcia.com and Archive.org
- **Storage Space** ~1GB working space, 50MB+ final output

### Data Models
- **Shared Models** (`scripts/shared/models.py`) ensure consistency
- **JSON Schema** standardized format across all outputs
- **Mobile Optimization** efficient structures for app consumption

### API Integration
- **Rate Limiting** respectful server usage with configurable delays
- **Error Recovery** robust retry logic with exponential backoff
- **Caching** intelligent data caching to minimize redundant requests

---

**System Version**: 2.0  
**Last Updated**: August 2025  
**Pipeline Status**: Production Ready