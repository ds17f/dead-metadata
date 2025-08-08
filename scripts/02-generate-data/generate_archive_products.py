#!/usr/bin/env python3
"""
Archive Data Products Generation Script

This script processes cached Archive.org recording metadata into useful outputs
including show-level aggregations and app-ready ratings. It focuses solely on 
data processing without any API calls.

Architecture:
- Reads cached recording metadata from Stage 1 collection
- Generates show-level aggregations with best recording selection
- Creates simplified ratings JSON and compressed ZIP for app consumption
- Validates input data exists before processing
- Fast local processing of cached data

Usage:
    # Default processing (all products)
    python scripts/02-generate-data/generate_archive_products.py
    
    # Custom input directory
    python scripts/02-generate-data/generate_archive_products.py --input-dir /path/to/cache
    
    # Custom output directory
    python scripts/02-generate-data/generate_archive_products.py --output-dir /path/to/output
    
    # Generate only specific products
    python scripts/02-generate-data/generate_archive_products.py --ratings-only
    python scripts/02-generate-data/generate_archive_products.py --shows-only
"""

import json
import os
import zipfile
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional
import argparse
import logging

# Add shared module to path
sys.path.append(str(Path(__file__).parent.parent))
from shared.models import RecordingMetadata, ShowMetadata, show_to_dict


class ArchiveDataProcessor:
    """
    Processor for cached Archive.org data, generating useful products.
    """
    
    def __init__(self, input_dir: str = "stage01-collected-data/archive",
                 output_dir: str = "stage02-generated-data"):
        """Initialize the processor with input and output directories."""
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.shows_dir = self.output_dir / "shows"
        
        # Source weighting for best recording selection
        self.source_weights = {
            'SBD': 1.0,
            'MATRIX': 0.9,
            'AUD': 0.7,
            'FM': 0.8,
            'REMASTER': 1.0,
        }
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging with console output."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handler
        self.logger.addHandler(console_handler)
    
    def validate_input_data(self) -> bool:
        """Validate that input data exists and is usable."""
        if not self.input_dir.exists():
            self.logger.error(f"❌ Input directory does not exist: {self.input_dir}")
            self.logger.error("Please run the collection script first:")
            self.logger.error(f"  python scripts/01-collect-data/collect_archive_metadata.py")
            return False
        
        # Count cached recording files
        recording_files = list(self.input_dir.glob("*.json"))
        # Exclude progress.json and logs
        recording_files = [f for f in recording_files if not f.name.startswith(('progress', 'collection'))]
        
        if len(recording_files) == 0:
            self.logger.error(f"❌ No recording metadata found in: {self.input_dir}")
            self.logger.error("Please run the collection script first to populate the cache.")
            return False
        
        self.logger.info(f"✅ Found {len(recording_files)} cached recording files")
        
        # Test read one file to validate format
        try:
            test_file = recording_files[0]
            with open(test_file, 'r') as f:
                data = json.load(f)
            # Try to create RecordingMetadata to validate structure
            RecordingMetadata(**data)
            self.logger.info("✅ Cached data format validation passed")
        except Exception as e:
            self.logger.error(f"❌ Cached data format validation failed: {e}")
            self.logger.error(f"Problem file: {test_file}")
            return False
        
        return True
    
    def create_output_directories(self):
        """Create output directories."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.shows_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directories created: {self.output_dir}")
    
    def load_cached_recordings(self) -> List[RecordingMetadata]:
        """Load all cached recording metadata."""
        recordings = []
        recording_files = list(self.input_dir.glob("*.json"))
        # Exclude progress.json and collection.log
        recording_files = [f for f in recording_files if not f.name.startswith(('progress', 'collection'))]
        
        self.logger.info(f"Loading {len(recording_files)} cached recordings...")
        
        for cache_file in recording_files:
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                recording_meta = RecordingMetadata(**data)
                recordings.append(recording_meta)
            except Exception as e:
                self.logger.warning(f"Skipping corrupted cache file {cache_file}: {e}")
                continue
        
        self.logger.info(f"Successfully loaded {len(recordings)} recordings")
        return recordings
    
    def generate_show_metadata(self, recordings: List[RecordingMetadata]) -> Dict[str, ShowMetadata]:
        """Generate show-level metadata from recording cache."""
        self.logger.info("Generating show-level metadata...")
        
        shows_data = defaultdict(list)
        
        # Group recordings by show
        for recording_meta in recordings:
            # Create show key from date and venue
            show_key = f"{recording_meta.date}_{recording_meta.venue.replace(' ', '_')}"
            shows_data[show_key].append(recording_meta)
        
        shows = {}
        
        # Generate show metadata
        for show_key, show_recordings in shows_data.items():
            if len(show_recordings) == 0:
                continue
                
            # Sort recordings by preference (SBD > others, then by rating)
            show_recordings.sort(key=lambda r: (
                r.source_type == 'SBD' and r.review_count >= 3,
                r.review_count >= 5,
                r.rating,
                r.review_count
            ), reverse=True)
            
            best_recording = show_recordings[0]
            
            # Compute show-level rating
            total_weight = 0
            weighted_sum = 0
            
            for recording in show_recordings:
                weight = recording.review_count * self.source_weights.get(recording.source_type, 0.5)
                weighted_sum += recording.rating * weight
                total_weight += weight
            
            show_avg_rating = weighted_sum / total_weight if total_weight > 0 else 0
            total_reviews = sum(r.review_count for r in show_recordings)
            confidence = min(total_reviews / 10.0, 1.0)
            
            show_meta = ShowMetadata(
                show_key=show_key,
                date=best_recording.date,
                venue=best_recording.venue,
                location=best_recording.location,
                recordings=[r.identifier for r in show_recordings],
                best_recording=best_recording.identifier,
                avg_rating=show_avg_rating,
                confidence=confidence,
                recording_count=len(show_recordings),
                collection_timestamp=datetime.now().isoformat()
            )
            
            shows[show_key] = show_meta
            
            # Save individual show metadata
            show_file = self.shows_dir / f"{show_key}.json"
            with open(show_file, 'w') as f:
                json.dump(show_to_dict(show_meta), f, indent=2, default=str)
        
        self.logger.info(f"Generated metadata for {len(shows)} shows")
        return shows
    
    def generate_ratings_json(self, recordings: List[RecordingMetadata], 
                            shows: Dict[str, ShowMetadata], output_file: str):
        """Generate simplified ratings.json for app bundle."""
        self.logger.info("Generating simplified ratings products...")
        
        recording_ratings = {}
        show_ratings = {}
        
        # Collect recording ratings
        for recording_meta in recordings:
            recording_ratings[recording_meta.identifier] = {
                "rating": recording_meta.rating,
                "review_count": recording_meta.review_count,
                "source_type": recording_meta.source_type,
                "confidence": recording_meta.confidence
            }
        
        # Collect show ratings  
        for show_key, show_meta in shows.items():
            show_ratings[show_key] = {
                "date": show_meta.date,
                "venue": show_meta.venue,
                "rating": show_meta.avg_rating,
                "confidence": show_meta.confidence,
                "best_recording": show_meta.best_recording,
                "recording_count": show_meta.recording_count
            }
        
        # Create simplified structure
        ratings_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "version": "2.0.0",
                "total_recordings": len(recording_ratings),
                "total_shows": len(show_ratings)
            },
            "recording_ratings": recording_ratings,
            "show_ratings": show_ratings
        }
        
        # Write JSON file
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(ratings_data, f, indent=2, sort_keys=True)
        
        # Create compressed version
        zip_file = str(output_path).replace('.json', '.zip')
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write JSON directly to ZIP
            zf.writestr('ratings.json', json.dumps(ratings_data, indent=2, sort_keys=True))
        
        # Get file sizes
        json_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        zip_size = os.path.getsize(zip_file) / (1024 * 1024)  # MB
        
        self.logger.info(f"Generated ratings.json: {json_size:.1f}MB")
        self.logger.info(f"Generated ratings.zip: {zip_size:.1f}MB ({zip_size/json_size*100:.1f}% of original)")
        self.logger.info(f"Products contain {len(recording_ratings)} recordings and {len(show_ratings)} shows")
    
    def process_all_products(self, ratings_only: bool = False, shows_only: bool = False, 
                           custom_ratings_output: Optional[str] = None):
        """Process all products from cached data."""
        start_time = datetime.now()
        
        # Load cached recordings
        recordings = self.load_cached_recordings()
        if not recordings:
            self.logger.error("No recordings loaded. Cannot proceed.")
            return False
        
        # Generate shows (unless ratings_only)
        shows = {}
        if not ratings_only:
            shows = self.generate_show_metadata(recordings)
        
        # Generate ratings (unless shows_only)
        if not shows_only:
            # If we skipped shows generation, we need to create empty dict
            if ratings_only:
                shows = {}
            
            ratings_output = custom_ratings_output or str(self.output_dir / "ratings.json")
            self.generate_ratings_json(recordings, shows, ratings_output)
        
        # Report processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"✅ Processing completed in {processing_time:.1f} seconds")
        
        # Summary
        self.logger.info("=== Generation Summary ===")
        self.logger.info(f"Input recordings: {len(recordings)}")
        if shows:
            self.logger.info(f"Shows generated: {len(shows)}")
        if not shows_only:
            self.logger.info(f"Ratings output: {custom_ratings_output or str(self.output_dir / 'ratings.json')}")
        self.logger.info(f"Output directory: {self.output_dir}")
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate products from cached Archive.org data')
    parser.add_argument('--input-dir', default='stage01-collected-data/archive', 
                       help='Input directory with cached recordings')
    parser.add_argument('--output-dir', default='stage02-generated-data',
                       help='Output directory for generated products')
    parser.add_argument('--ratings-output', 
                       help='Custom output path for ratings.json')
    parser.add_argument('--ratings-only', action='store_true',
                       help='Generate only ratings products (skip shows)')
    parser.add_argument('--shows-only', action='store_true',
                       help='Generate only show metadata (skip ratings)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.ratings_only and args.shows_only:
        print("❌ Cannot specify both --ratings-only and --shows-only")
        return 1
    
    processor = ArchiveDataProcessor(
        input_dir=args.input_dir,
        output_dir=args.output_dir
    )
    
    # Validate input
    if not processor.validate_input_data():
        return 1
    
    # Create output directories
    processor.create_output_directories()
    
    # Process all products
    success = processor.process_all_products(
        ratings_only=args.ratings_only,
        shows_only=args.shows_only,
        custom_ratings_output=args.ratings_output
    )
    
    if success:
        print(f"✅ Generation complete! Output: {args.output_dir}")
        return 0
    else:
        print("❌ Generation failed. Check logs for details.")
        return 1


if __name__ == '__main__':
    exit(main())