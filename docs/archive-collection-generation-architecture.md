# Archive Collection & Generation Architecture

## Overview

This document outlines the architectural split of Archive.org metadata collection into two distinct, specialized scripts that separate data collection from data generation. This separation transforms the monolithic `generate_metadata.py` into a clean two-stage pipeline optimized for different operational needs.

### Rationale

**Collection** (expensive, long-running):
- Archive.org API calls with rate limiting
- Network-dependent operations
- Progress tracking and resume capability
- Run once, cache results

**Generation** (fast, local):
- Process cached data into useful outputs
- Multiple output formats from same source data
- Run multiple times without re-collection
- Rapid iteration on output formats

## Architecture Overview

```
┌─────────────────┐
│   Archive.org   │
│     API         │
└─────────┬───────┘
          │ HTTP requests
          │ (rate limited)
          ▼
┌─────────────────┐    ┌──────────────────────┐
│  STAGE 1:       │    │ scripts/shared/      │
│  COLLECTION     │◄───┤ models.py            │
│                 │    │ (shared dataclasses) │
└─────────┬───────┘    └──────────────────────┘
          │
          │ Individual recording
          │ JSON files
          ▼
┌─────────────────────────────────┐
│ stage01-collected-data/archive/ │
│ ├── gd1977-05-08.*.json        │
│ ├── gd1977-05-09.*.json        │
│ └── ... (17,790+ files)        │
└─────────────┬───────────────────┘
              │
              │ Read cached data
              ▼
┌─────────────────┐    ┌──────────────────────┐
│  STAGE 2:       │    │ scripts/shared/      │
│  GENERATION     │◄───┤ models.py            │
│                 │    │ (shared dataclasses) │
└─────────┬───────┘    └──────────────────────┘
          │
          │ Processed outputs
          ▼
┌─────────────────────────────────┐
│ stage02-generated-data/         │
│ ├── shows/                     │
│ │   ├── 1977-05-08_*.json      │
│ │   └── ...                    │
│ ├── ratings.json               │
│ └── ratings.zip                │
└─────────────────────────────────┘
```

## Directory Structure

```
scripts/
├── shared/
│   └── models.py                           # Shared data models
├── 01-collect-data/
│   └── collect_archive_metadata.py         # Archive.org collection script
├── 02-generate-data/
│   └── generate_archive_products.py        # Process cached data into outputs
└── [existing scripts unchanged]

# Project root stage directories
stage01-collected-data/
└── archive/                                # Individual recording cache
    ├── gd1977-05-08.sbd.*.json            # ~17,790 recording files
    └── progress.json                       # Collection progress state

stage02-generated-data/                     # NEW directory
├── shows/                                  # Show-level aggregations
│   ├── 1977-05-08_Cornell_University.json
│   └── ...
└── ratings.json                            # App-ready ratings
```

## Shared Data Models

### Location: `scripts/shared/models.py`

All dataclasses extracted from original `generate_metadata.py` to ensure consistency:

```python
@dataclass
class ReviewData:
    """Individual review data"""
    stars: float
    review_text: str
    date: str

@dataclass
class RecordingMetadata:
    """Complete metadata for a single recording"""
    identifier: str
    title: str
    date: str
    venue: str
    location: str
    source_type: str
    lineage: str
    taper: str
    description: str
    files: List[Dict[str, Any]]
    reviews: List[ReviewData]
    rating: float                             # Weighted rating
    review_count: int
    confidence: float
    collection_timestamp: str
    # Additional rating analysis fields...

@dataclass
class ShowMetadata:
    """Aggregated metadata for an entire show"""
    show_key: str
    date: str
    venue: str
    location: str
    recordings: List[str]
    best_recording: str
    avg_rating: float
    confidence: float
    recording_count: int
    collection_timestamp: str

@dataclass
class ProgressState:
    """Collection progress tracking"""
    collection_started: str
    last_updated: str
    status: str
    total_recordings: int
    processed_recordings: int
    failed_recordings: int
    current_batch: int
    last_processed: str
    failed_identifiers: List[str]
    performance_stats: Dict[str, Any]
```

### Import Strategy

Both scripts import from the shared module:

```python
# Collection script
from shared.models import ReviewData, RecordingMetadata, ProgressState

# Generation script  
from shared.models import RecordingMetadata, ShowMetadata
```

## Stage 1: Collection Script

### File: `scripts/01-collect-data/collect_archive_metadata.py`

**Purpose**: Pure Archive.org API data collection with caching and progress tracking.

### Core Features

- **Archive.org Search**: Intelligent pagination handling (10k limit workaround)
- **Rate Limiting**: Respectful 0.25s delays between API calls
- **Smart Caching**: Skip existing files unless `--force` specified
- **Progress Tracking**: Resumable collections with detailed statistics
- **Batch Processing**: Process recordings in configurable batches
- **Error Handling**: Graceful failure with retry logic

### Default Behavior

- **Output Directory**: `stage01-collected-data/archive/`
- **Non-Destructive**: Won't overwrite existing cached files
- **Progress File**: `{output_dir}/progress.json` for resume capability
- **Logging**: Combined file and console output

### CLI Interface

```bash
# Default full collection
python scripts/01-collect-data/collect_archive_metadata.py --mode full

# Custom output directory
python scripts/01-collect-data/collect_archive_metadata.py --output-dir /custom/path --mode full

# Test with limited recordings
python scripts/01-collect-data/collect_archive_metadata.py --mode test --max-recordings 10

# Force overwrite existing files
python scripts/01-collect-data/collect_archive_metadata.py --force --mode full

# Resume interrupted collection
python scripts/01-collect-data/collect_archive_metadata.py --resume

# Year-specific collection
python scripts/01-collect-data/collect_archive_metadata.py --year 1977 --mode full

# Custom rate limiting
python scripts/01-collect-data/collect_archive_metadata.py --delay 0.5 --mode full
```

### Core Class: `ArchiveMetadataCollector`

**Extracted Methods** (from original `GratefulDeadMetadataCollector`):
- `get_grateful_dead_recordings()` - Search with intelligent pagination
- `_get_recordings_by_month()` / `_get_recordings_by_week()` - High-volume year handling
- `fetch_recording_metadata()` / `fetch_recording_reviews()` - API calls
- `process_recording()` - Individual recording processing and caching
- `collect_all_metadata()` - Main orchestration with batch processing
- `rate_limit()` - API respectful delays
- `save_progress()` / `load_progress()` - Resume capability

**Responsibilities**:
- ✅ Archive.org API interactions
- ✅ Individual recording caching
- ✅ Progress tracking and resume
- ✅ Rate limiting and error handling
- ❌ Show aggregation (moved to generation)
- ❌ Ratings output (moved to generation)

### Output Structure

```
stage01-collected-data/archive/
├── gd1977-05-08.sbd.miller.*.json         # Individual recordings
├── gd1977-05-09.sbd.berger.*.json
├── ...                                     # ~17,790 total files
├── progress.json                           # Collection progress
└── collection.log                          # Detailed logging
```

Each recording file contains complete `RecordingMetadata` with reviews, ratings, and source analysis.

## Stage 2: Generation Script

### File: `scripts/02-generate-data/generate_archive_products.py`

**Purpose**: Process cached recording data into useful outputs for apps and analysis.

### Core Features

- **Input Validation**: Fail clearly if cache directory missing or empty
- **Show Aggregation**: Group recordings by show, select best recording
- **Rating Generation**: Create simplified ratings for app consumption
- **JSON Output**: Clean, structured ratings data
- **Statistics Reporting**: Show what was processed and created

### Default Behavior

- **Input Directory**: `stage01-collected-data/archive/`
- **Output Directory**: `stage02-generated-data/`
- **Shows Output**: `stage02-generated-data/shows/`
- **Ratings Output**: `stage02-generated-data/ratings.json` + `.zip`

### CLI Interface

```bash
# Default processing (all products)
python scripts/02-generate-data/generate_archive_products.py

# Custom input directory (if collection used custom path)
python scripts/02-generate-data/generate_archive_products.py --input-dir /custom/cache

# Custom output directory
python scripts/02-generate-data/generate_archive_products.py --output-dir /custom/output

# Generate only ratings (skip show aggregation)
python scripts/02-generate-data/generate_archive_products.py --ratings-only

# Generate only show metadata
python scripts/02-generate-data/generate_archive_products.py --shows-only

# Custom output paths
python scripts/02-generate-data/generate_archive_products.py \
    --shows-dir stage02-generated-data/shows \
    --ratings-output stage02-generated-data/ratings.json
```

### Core Class: `ArchiveDataProcessor`

**Extracted Methods** (from original `GratefulDeadMetadataCollector`):
- `generate_show_metadata()` - Group recordings by show, compute show ratings
- `generate_ratings_json()` - Create simplified app-ready ratings
- `_validate_input_data()` - Ensure cache exists and has data
- `_create_output_directories()` - Setup output structure
- `_generate_statistics()` - Report processing results

**Responsibilities**:
- ✅ Read cached recording data
- ✅ Generate show-level aggregations
- ✅ Create app-ready ratings JSON
- ✅ Input validation and error reporting
- ❌ API calls (collection handled separately)
- ❌ Progress tracking (processing is fast)

### Output Products

#### Show Metadata (`stage02-generated-data/shows/`)
Individual JSON files for each show with aggregated data:

```json
{
  "show_key": "1977-05-08_Cornell_University",
  "date": "1977-05-08",
  "venue": "Cornell University",
  "location": "Ithaca, NY",
  "recordings": ["gd1977-05-08.sbd.miller.*", "..."],
  "best_recording": "gd1977-05-08.sbd.miller.*",
  "avg_rating": 4.8,
  "confidence": 0.95,
  "recording_count": 12,
  "collection_timestamp": "2024-01-15T10:30:00"
}
```

#### Ratings JSON (`stage02-generated-data/ratings.json`)
Simplified structure for app consumption:

```json
{
  "metadata": {
    "generated_at": "2024-01-15T10:30:00",
    "version": "2.0.0", 
    "total_recordings": 17790,
    "total_shows": 2200
  },
  "recording_ratings": {
    "gd1977-05-08.sbd.miller.*": {
      "rating": 4.8,
      "review_count": 45,
      "source_type": "SBD",
      "confidence": 0.95
    }
  },
  "show_ratings": {
    "1977-05-08_Cornell_University": {
      "date": "1977-05-08",
      "venue": "Cornell University",
      "rating": 4.8,
      "confidence": 0.95,
      "best_recording": "gd1977-05-08.sbd.miller.*",
      "recording_count": 12
    }
  }
}
```

## Data Flow & Dependencies

### Collection Flow
```
1. Archive.org API search → Recording identifiers
2. For each identifier:
   - Fetch metadata API call
   - Fetch reviews API call  
   - Process and compute ratings
   - Cache to individual JSON file
3. Save progress state
4. Resume capability from progress file
```

### Generation Flow
```
1. Validate input: stage01-collected-data/archive/ exists
2. Read all cached recording JSON files
3. Group recordings by show (date + venue)
4. For each show:
   - Select best recording (SBD preference, rating, review count)
   - Compute show-level aggregated rating
   - Save show metadata JSON
5. Create simplified ratings structure
6. Output ratings JSON
```

### Dependency Chain
```
Archive.org API → Collection Script → Cached Data → Generation Script → App Products
```

## Error Handling & Validation

### Collection Script Errors

**Network Issues**:
- API unavailable → Retry with exponential backoff
- Rate limit exceeded → Respect server delays
- Individual recording failure → Log and continue

**Progress Tracking**:
- Interrupted collection → Resume from progress file
- Corrupted progress → Start fresh with user confirmation
- Disk space issues → Clear error message

### Generation Script Errors

**Input Validation**:
- Missing cache directory → "Run collection script first"
- Empty cache directory → "No recordings found in cache"
- Corrupted cache files → Skip with warning, report statistics

**Output Issues**:
- Cannot create output directory → Permission error with suggestion
- Disk space → Clear error with space requirements
- Partial processing → Report what succeeded vs failed

## Usage Examples

### Development Workflow

```bash
# 1. Collect test dataset
python scripts/01-collect-data/collect_archive_metadata.py --mode test --max-recordings 50

# 2. Generate products from test data
python scripts/02-generate-data/generate_archive_products.py

# 3. Iterate on output formats (fast, no re-collection needed)
python scripts/02-generate-data/generate_archive_products.py --ratings-only
```

### Production Deployment

```bash
# 1. Full collection (2-3 hours)
python scripts/01-collect-data/collect_archive_metadata.py --mode full

# 2. Generate all products
python scripts/02-generate-data/generate_archive_products.py

# 3. Update app data (ratings.json is ready for deployment)
cp stage02-generated-data/ratings.json /path/to/app/deployment/
```

### Custom Paths

```bash
# Collection to custom location
python scripts/01-collect-data/collect_archive_metadata.py \
    --output-dir /fast-storage/archive-cache --mode full

# Generation from custom location
python scripts/02-generate-data/generate_archive_products.py \
    --input-dir /fast-storage/archive-cache \
    --output-dir /app-data/ratings
```

## Integration with Existing Pipeline

### Stage Alignment

This architecture aligns with the existing 4-stage pipeline:

**Stage 1 - Data Collection**: 
- ✅ `stage01-collected-data/archive/` (Archive.org)
- ✅ `stage01-collected-data/cmu/` (CMU setlists)
- ✅ `stage01-collected-data/gdsets/` (GDSets data)

**Stage 2 - Data Generation**:
- 🆕 `stage02-generated-data/shows/` (Show aggregations)
- 🆕 `stage02-generated-data/ratings.json` (App ratings)
- Future: `stage02-generated-data/venues.json`, `songs.json`

### Future Integration Points

**Stage 3 - Data Integration**:
- Combine Archive ratings with setlist data
- Link shows with venue and song IDs
- Create unified show records

**Stage 4 - Deployment**:
- Package all Stage 2 + Stage 3 products
- Create compressed app bundles
- Generate API-ready formats

## Migration Guide

### From Monolithic `generate_metadata.py`

1. **Backup Current State**:
   ```bash
   cp scripts/generate_metadata.py scripts/generate_metadata.py.backup
   ```

2. **Create New Directory Structure**:
   ```bash
   mkdir -p scripts/shared
   mkdir -p scripts/01-collect-data  
   mkdir -p scripts/02-generate-data
   ```

3. **Extract and Test**:
   - Create `scripts/shared/models.py`
   - Create collection script, test with small dataset
   - Create generation script, test with cached data
   - Verify outputs match original script

4. **Update Build System**:
   - Update Makefile targets
   - Update documentation
   - Add new stage directories to `.gitignore` if needed

### Backward Compatibility

- Original `generate_metadata.py` remains functional during transition
- New scripts use same output formats
- Existing downstream scripts continue to work
- Stage directories follow established patterns

## Technical Specifications

### API Rate Limiting
- **Default delay**: 0.25 seconds between Archive.org API calls
- **Batch processing**: 100 recordings per batch with optional breaks
- **High-volume handling**: Monthly/weekly breakdown for years with >10k recordings
- **Respectful usage**: User-Agent identification and timeout handling

### File Formats
- **Cached recordings**: Individual JSON files with complete `RecordingMetadata`
- **Progress tracking**: JSON with collection state and performance statistics  
- **Show metadata**: Individual JSON files per show
- **Ratings output**: JSON for app deployment

### Performance Characteristics
- **Collection**: 2-3 hours for full Archive.org dataset (17,790+ recordings)
- **Generation**: 1-5 minutes for complete processing of cached data
- **Storage**: ~500MB cache, 2-5MB final outputs
- **Resume**: Collection can resume from any point using progress files

### Error Recovery
- **Network failures**: Automatic retry with exponential backoff
- **Partial failures**: Continue processing, report failed items
- **Corrupted data**: Skip bad files, warn user, continue processing
- **Resource constraints**: Clear error messages with suggested solutions

This architecture provides a robust, maintainable foundation for Archive.org data collection and processing while maintaining compatibility with the existing pipeline ecosystem.