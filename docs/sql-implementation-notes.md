# SQL Database Implementation Notes

This document provides guidance for implementing a SQL database schema based on the Grateful Dead metadata pipeline data structures. It complements the main pipeline documentation with database-specific implementation details.

## Overview

The pipeline generates structured JSON data that maps well to a relational database schema. The data follows a clear hierarchy: Shows contain Setlists and Lineups, while being enriched with Archive.org recording metadata.

## Core Schema Design

### Primary Tables

#### Shows Table
The central entity representing individual Grateful Dead concerts.

```sql
CREATE TABLE shows (
    show_id VARCHAR(255) PRIMARY KEY,  -- e.g., "1977-05-08-barton-hall-cornell-u-ithaca-ny-usa"
    url TEXT,                          -- JerryGarcia.com source URL
    band VARCHAR(100) DEFAULT 'Grateful Dead',
    venue TEXT NOT NULL,
    location_raw TEXT,                 -- Original location string from source
    city VARCHAR(100),
    state VARCHAR(10),
    country VARCHAR(10) DEFAULT 'USA',
    date DATE NOT NULL,
    show_time VARCHAR(20),             -- "early", "late", or null for single shows
    
    -- Data completeness flags
    setlist_status VARCHAR(20),        -- "found", "missing"
    lineup_status VARCHAR(20),         -- "found", "missing"  
    supporting_acts_status VARCHAR(20), -- "found", "missing"
    
    -- Archive.org recording metrics
    avg_rating DECIMAL(10,8),          -- Weighted rating (0-5 scale)
    raw_rating DECIMAL(10,8),          -- Simple average rating (0-5 scale)
    recording_count INTEGER DEFAULT 0,
    confidence DECIMAL(3,2),           -- Rating confidence (0.0-1.0)
    best_recording VARCHAR(255),       -- Archive.org identifier of highest-rated recording
    total_high_ratings INTEGER DEFAULT 0,  -- Count of 4-5★ reviews
    total_low_ratings INTEGER DEFAULT 0,   -- Count of 1-2★ reviews
    
    -- Processing metadata
    matching_method VARCHAR(50),       -- "date_only", "date_venue", etc.
    filtering_applied JSON,            -- Array of filters applied during processing
    collection_timestamp TIMESTAMP,
    
    -- Indexes for common queries
    INDEX idx_date (date),
    INDEX idx_venue (venue),
    INDEX idx_city (city),
    INDEX idx_rating (avg_rating),
    INDEX idx_year_month (YEAR(date), MONTH(date))
);
```

#### Setlists Tables
Represents the structured song performance data.

```sql
CREATE TABLE setlists (
    id SERIAL PRIMARY KEY,
    show_id VARCHAR(255) NOT NULL,
    set_name VARCHAR(50) NOT NULL,     -- "Set 1", "Set 2", "Encore"
    set_order INTEGER NOT NULL,       -- Order of sets within show
    
    FOREIGN KEY (show_id) REFERENCES shows(show_id) ON DELETE CASCADE,
    INDEX idx_show_id (show_id)
);

CREATE TABLE setlist_songs (
    id SERIAL PRIMARY KEY,
    setlist_id INTEGER NOT NULL,
    song_name VARCHAR(255) NOT NULL,
    song_url TEXT,                     -- JerryGarcia.com song URL (may be null)
    position INTEGER NOT NULL,         -- Song order within set (1-based)
    segue_into_next BOOLEAN DEFAULT false, -- True if song segues into next
    
    FOREIGN KEY (setlist_id) REFERENCES setlists(id) ON DELETE CASCADE,
    INDEX idx_setlist_id (setlist_id),
    INDEX idx_song_name (song_name),
    INDEX idx_show_song (setlist_id, song_name) -- For song-in-show queries
);
```

#### Band Lineups
Represents band member participation in shows.

```sql
CREATE TABLE show_lineups (
    id SERIAL PRIMARY KEY,
    show_id VARCHAR(255) NOT NULL,
    member_name VARCHAR(100) NOT NULL,
    instruments TEXT,                  -- e.g., "guitar, vocals"
    image_url TEXT,                    -- JerryGarcia.com profile image
    
    FOREIGN KEY (show_id) REFERENCES shows(show_id) ON DELETE CASCADE,
    INDEX idx_show_id (show_id),
    INDEX idx_member (member_name),
    UNIQUE KEY unique_show_member (show_id, member_name)
);
```

#### Archive.org Recordings
Individual recording metadata linked to shows.

```sql
CREATE TABLE recordings (
    identifier VARCHAR(255) PRIMARY KEY, -- Archive.org unique identifier
    show_id VARCHAR(255) NOT NULL,
    title TEXT,
    source_type VARCHAR(20),           -- "SBD", "AUD", "FM", "MATRIX", "REMASTER"
    lineage TEXT,                      -- Recording chain information
    taper VARCHAR(255),                -- Person who recorded/transferred
    description TEXT,                  -- Archive.org description
    
    -- Quality metrics
    rating DECIMAL(10,8),              -- Weighted rating for internal ranking
    raw_rating DECIMAL(10,8),          -- Simple average for display
    review_count INTEGER DEFAULT 0,
    confidence DECIMAL(3,2),           -- Rating confidence (0.0-1.0)
    
    collection_timestamp TIMESTAMP,
    
    FOREIGN KEY (show_id) REFERENCES shows(show_id) ON DELETE CASCADE,
    INDEX idx_show_id (show_id),
    INDEX idx_source_type (source_type),
    INDEX idx_rating (rating)
);

-- Source type distribution per show (from JSON source_types field)
CREATE TABLE recording_source_counts (
    show_id VARCHAR(255) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    count INTEGER NOT NULL,
    
    FOREIGN KEY (show_id) REFERENCES shows(show_id) ON DELETE CASCADE,
    PRIMARY KEY (show_id, source_type)
);
```

### Supporting Acts (Optional)
If supporting acts data is present:

```sql
CREATE TABLE supporting_acts (
    id SERIAL PRIMARY KEY,
    show_id VARCHAR(255) NOT NULL,
    act_name VARCHAR(255) NOT NULL,
    act_order INTEGER,                 -- Opening act order
    
    FOREIGN KEY (show_id) REFERENCES shows(show_id) ON DELETE CASCADE,
    INDEX idx_show_id (show_id)
);
```

## Search Optimization Tables

Based on the Stage 3 search tables, create materialized views or denormalized tables:

### Song Search Table
```sql
CREATE TABLE song_search (
    song_key VARCHAR(255) NOT NULL,    -- Normalized song name (e.g., "dark-star")
    song_name VARCHAR(255) NOT NULL,   -- Display name (e.g., "Dark Star")
    show_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    venue TEXT NOT NULL,
    location VARCHAR(255) NOT NULL,    -- "City, State, Country"
    set_name VARCHAR(50),
    position INTEGER,
    segue_into_next BOOLEAN,
    rating DECIMAL(10,8),
    raw_rating DECIMAL(10,8),
    
    INDEX idx_song_key (song_key),
    INDEX idx_song_name (song_name),
    INDEX idx_date (date),
    FULLTEXT idx_song_search (song_name, song_key)
);
```

### Venue Search Table
```sql
CREATE TABLE venue_search (
    venue_key VARCHAR(255) NOT NULL,   -- Normalized venue name
    venue_name TEXT NOT NULL,          -- Display name
    location VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(10),
    country VARCHAR(10),
    show_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    rating DECIMAL(10,8),
    raw_rating DECIMAL(10,8),
    recording_count INTEGER,
    
    INDEX idx_venue_key (venue_key),
    INDEX idx_city (city),
    INDEX idx_state (state),
    FULLTEXT idx_venue_search (venue_name, city)
);
```

### Member Search Table
```sql
CREATE TABLE member_search (
    member_key VARCHAR(255) NOT NULL,  -- Normalized member name
    member_name VARCHAR(100) NOT NULL, -- Display name
    show_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    venue TEXT NOT NULL,
    instruments TEXT,
    rating DECIMAL(10,8),
    
    INDEX idx_member_key (member_key),
    INDEX idx_member_name (member_name),
    INDEX idx_date (date),
    FULLTEXT idx_member_search (member_name, instruments)
);
```

## Data Import Strategy

### JSON to SQL Mapping

1. **Shows**: Direct mapping from `stage02-generated-data/shows/*.json`
2. **Search Tables**: Import from `stage03-search-data/*.json` files
3. **Batch Processing**: Process shows in chronological order for better locality

### Sample Import Logic

```sql
-- Example for importing a show file
INSERT INTO shows (
    show_id, url, band, venue, city, state, country, date,
    setlist_status, lineup_status, avg_rating, raw_rating,
    recording_count, best_recording, collection_timestamp
) VALUES (
    JSON_UNQUOTE(JSON_EXTRACT(show_json, '$.show_id')),
    JSON_UNQUOTE(JSON_EXTRACT(show_json, '$.url')),
    -- ... continue for all fields
);

-- Import setlist data
INSERT INTO setlists (show_id, set_name, set_order)
SELECT 
    show_id,
    JSON_UNQUOTE(JSON_EXTRACT(setlist_item, '$.set_name')),
    setlist_index
FROM shows s
JOIN JSON_TABLE(s.setlist_json, '$[*]' 
    COLUMNS (
        setlist_index FOR ORDINALITY,
        setlist_item JSON PATH '$'
    )
) jt;
```

## Business Rules and Constraints

### Data Validation
```sql
-- Date range validation (Grateful Dead performing years)
ALTER TABLE shows ADD CONSTRAINT valid_date_range 
CHECK (date BETWEEN '1965-01-01' AND '1995-12-31');

-- Rating constraints
ALTER TABLE shows ADD CONSTRAINT valid_rating_range
CHECK (avg_rating IS NULL OR (avg_rating >= 0 AND avg_rating <= 5));

ALTER TABLE shows ADD CONSTRAINT valid_confidence
CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1));

-- Recording count consistency
ALTER TABLE shows ADD CONSTRAINT valid_recording_count
CHECK (recording_count >= 0);

-- Required fields
ALTER TABLE shows ALTER COLUMN venue SET NOT NULL;
ALTER TABLE shows ALTER COLUMN date SET NOT NULL;

-- Show ID format validation (basic)
ALTER TABLE shows ADD CONSTRAINT valid_show_id_format
CHECK (show_id REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}-.+');
```

### Referential Integrity
```sql
-- Ensure best_recording exists in recordings table
ALTER TABLE shows ADD CONSTRAINT fk_best_recording
FOREIGN KEY (best_recording) REFERENCES recordings(identifier);

-- Ensure setlist songs reference valid setlists
ALTER TABLE setlist_songs ADD CONSTRAINT fk_setlist
FOREIGN KEY (setlist_id) REFERENCES setlists(id) ON DELETE CASCADE;
```

## Performance Optimization

### Recommended Indexes
```sql
-- Core performance indexes
CREATE INDEX idx_shows_date_rating ON shows(date, avg_rating DESC);
CREATE INDEX idx_shows_venue_date ON shows(venue, date);
CREATE INDEX idx_songs_performance ON setlist_songs(song_name, setlist_id);

-- Search indexes
CREATE FULLTEXT INDEX idx_shows_search ON shows(venue, city);
CREATE FULLTEXT INDEX idx_songs_fulltext ON setlist_songs(song_name);

-- Composite indexes for common queries
CREATE INDEX idx_show_year_state ON shows(YEAR(date), state);
CREATE INDEX idx_recording_source_rating ON recordings(source_type, rating DESC);
```

### Query Optimization Hints

```sql
-- Find all shows in 1977 with Dark Star
SELECT DISTINCT s.show_id, s.date, s.venue, s.avg_rating
FROM shows s
JOIN setlists sl ON s.show_id = sl.show_id
JOIN setlist_songs ss ON sl.id = ss.setlist_id
WHERE YEAR(s.date) = 1977 
  AND ss.song_name LIKE '%Dark Star%'
ORDER BY s.date;

-- Top-rated shows at the Fillmore
SELECT show_id, date, avg_rating, recording_count
FROM shows 
WHERE venue LIKE '%Fillmore%' 
  AND avg_rating IS NOT NULL
ORDER BY avg_rating DESC, recording_count DESC
LIMIT 20;
```

## Data Statistics

Based on the pipeline output:

- **Shows**: ~2,313 total (1965-1995)
- **Venues**: ~484 unique venues
- **Songs**: ~550 unique songs with aliases
- **Recordings**: 17,790+ Archive.org recordings
- **Members**: ~20+ band members across all eras
- **Geographic Distribution**: Primarily USA with some Canada shows

### Storage Estimates
- **Shows table**: ~500KB (2,313 rows × ~200 bytes avg)
- **Setlist_songs table**: ~2MB (estimated 40,000+ song performances)
- **Recordings table**: ~15MB (17,790 rows × ~800 bytes avg)
- **Search tables**: ~5MB total (denormalized data)

**Total estimated database size**: 25-30MB for core data, plus indexes.

## Integration Notes

### Pipeline Integration
- Run database import after Stage 3 (search data generation)
- Use `collection_timestamp` fields to track data freshness
- Consider incremental updates for new shows/recordings

### API Considerations
- Search tables enable fast mobile app queries
- Core show data provides complete details for individual views
- Recording data supports quality-based filtering

### Backup Strategy
- Regular backups of core shows/setlists (relatively static)
- More frequent backups of recordings table (may grow with new Archive.org discoveries)
- Version control for schema changes as pipeline evolves

---

**Note**: This schema is based on analysis of the actual JSON output from the Grateful Dead metadata pipeline as of August 2025. Adjust field sizes and constraints based on your specific requirements and data distribution.