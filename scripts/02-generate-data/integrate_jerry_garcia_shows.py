#!/usr/bin/env python3
"""
JerryGarcia Show Integration Script

This script integrates JerryGarcia.com show data with Archive.org recording metadata
to create enhanced show data combining complete show information with recording quality data.

Architecture:
- JerryGarcia data provides authoritative show information (setlists, lineups, venues)
- Archive.org data provides recording quality metadata (ratings, source types)
- Date-based matching using normalized ISO dates
- Preserves all JerryGarcia fields with Archive recording enrichment

Usage:
    # Default processing
    python scripts/02-generate-data/integrate_jerry_garcia_shows.py
    
    # Custom directories
    python scripts/02-generate-data/integrate_jerry_garcia_shows.py \
        --jerrygarcia-dir stage01-collected-data/jerrygarcia/shows \
        --archive-dir stage01-collected-data/archive \
        --output-dir stage02-generated-data
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Any
import argparse
import logging

# Add shared module to path
sys.path.append(str(Path(__file__).parent.parent))
from shared.models import RecordingMetadata


class JerryGarciaShowIntegrator:
    """
    Integrator for JerryGarcia show data with Archive.org recording metadata.
    """
    
    def __init__(self, jerrygarcia_dir: str = "stage01-collected-data/jerrygarcia/shows",
                 archive_dir: str = "stage01-collected-data/archive",
                 output_dir: str = "stage02-generated-data"):
        """Initialize the integrator with input and output directories."""
        self.jerrygarcia_dir = Path(jerrygarcia_dir)
        self.archive_dir = Path(archive_dir) 
        self.output_dir = Path(output_dir)
        self.shows_dir = self.output_dir / "shows"
        
        # Source weighting for best recording selection
        self.source_weights = {
            'FM': 1.0,
            'SBD': 0.9,
            'MATRIX': 0.8,
            'AUD': 0.7,
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
        if not self.jerrygarcia_dir.exists():
            self.logger.error(f"❌ JerryGarcia directory does not exist: {self.jerrygarcia_dir}")
            return False
        
        if not self.archive_dir.exists():
            self.logger.error(f"❌ Archive directory does not exist: {self.archive_dir}")
            return False
        
        # Count show and recording files
        show_files = list(self.jerrygarcia_dir.glob("*.json"))
        recording_files = [f for f in self.archive_dir.glob("*.json") 
                          if not f.name.startswith(('progress', 'collection'))]
        
        if len(show_files) == 0:
            self.logger.error(f"❌ No JerryGarcia show files found in: {self.jerrygarcia_dir}")
            return False
            
        if len(recording_files) == 0:
            self.logger.error(f"❌ No Archive recording files found in: {self.archive_dir}")
            return False
        
        self.logger.info(f"✅ Found {len(show_files)} JerryGarcia shows")
        self.logger.info(f"✅ Found {len(recording_files)} Archive recordings")
        
        return True
    
    def create_output_directories(self):
        """Create output directories."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.shows_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directories created: {self.output_dir}")
    
    def parse_show_date_and_time(self, date_str: str) -> tuple:
        """
        Parse JerryGarcia date string to extract both date and show time modifier.
        Returns: (iso_date, show_time)
        Examples:
        - "2/13/1970 | Early Show" -> ("1970-02-13", "early")
        - "2/13/1970 | Late Show" -> ("1970-02-13", "late") 
        - "2/13/1970" -> ("1970-02-13", None)
        """
        try:
            # Clean the date string - remove tabs and extra spaces
            cleaned_date = date_str.strip()
            
            show_time = None
            
            # Check for show time modifier after |
            if '|' in cleaned_date:
                date_part, modifier_part = cleaned_date.split('|', 1)
                date_part = date_part.strip()
                modifier_part = modifier_part.strip().lower()
                
                if 'early' in modifier_part:
                    show_time = 'early'
                elif 'late' in modifier_part:
                    show_time = 'late'
            else:
                date_part = cleaned_date
            
            # Remove excessive whitespace and tabs from date part
            date_part = ' '.join(date_part.split())
            
            # Try parsing JerryGarcia format (M/D/YYYY)
            parsed_date = datetime.strptime(date_part, "%m/%d/%Y")
            iso_date = parsed_date.strftime("%Y-%m-%d")
            
            return iso_date, show_time
            
        except ValueError:
            # If that fails, assume it's already in ISO format or log warning
            self.logger.warning(f"Could not parse date: '{date_str}'")
            return date_str, None
    
    def normalize_date(self, date_str: str) -> str:
        """Backward compatibility - just return the date part."""
        iso_date, _ = self.parse_show_date_and_time(date_str)
        return iso_date
    
    def generate_show_id(self, date: str, venue: str, city: str, state: str, country: str, show_time: str = None) -> str:
        """
        Generate a normalized show_id from components.
        Format: YYYY-MM-DD-venue-city-state-country[-show-time]
        All components are lowercased and spaces/special chars converted to hyphens.
        """
        def normalize_component(text: str) -> str:
            if not text:
                return ""
            # Convert to lowercase
            normalized = text.lower()
            # Replace spaces and special characters with hyphens
            import re
            normalized = re.sub(r'[^\w]+', '-', normalized)
            # Remove leading/trailing hyphens
            normalized = normalized.strip('-')
            # Replace multiple consecutive hyphens with single hyphen
            normalized = re.sub(r'-+', '-', normalized)
            return normalized
        
        # Normalize all components
        components = [
            date,  # Already in YYYY-MM-DD format
            normalize_component(venue),
            normalize_component(city), 
            normalize_component(state),
            normalize_component(country)
        ]
        
        # Filter out empty components
        components = [c for c in components if c]
        
        # Add show time suffix if present
        if show_time:
            components.append(f"{show_time}-show")
        
        return '-'.join(components)
    
    def load_jerrygarcia_shows(self) -> Dict[str, Dict[str, Any]]:
        """Load all JerryGarcia show data."""
        shows = {}
        show_files = list(self.jerrygarcia_dir.glob("*.json"))
        
        self.logger.info(f"Loading {len(show_files)} JerryGarcia shows...")
        
        for show_file in show_files:
            try:
                with open(show_file, 'r') as f:
                    show_data = json.load(f)
                
                # Parse date and extract show time information
                if "date" in show_data:
                    iso_date, show_time = self.parse_show_date_and_time(show_data["date"])
                    show_data["date"] = iso_date
                    show_data["show_time"] = show_time
                    
                    # Check if show_id date matches actual date (only correct if mismatch)
                    original_show_id = show_data.get("show_id", "")
                    original_date_from_id = original_show_id.split('-')[:3]
                    original_date_from_id = '-'.join(original_date_from_id) if len(original_date_from_id) == 3 else ""
                    
                    if original_date_from_id != iso_date:
                        # Date mismatch detected - generate corrected show_id
                        corrected_show_id = self.generate_show_id(
                            date=iso_date,
                            venue=show_data.get("venue", ""),
                            city=show_data.get("city", ""),
                            state=show_data.get("state", ""), 
                            country=show_data.get("country", ""),
                            show_time=show_time
                        )
                        
                        self.logger.info(f"  Date mismatch correction: '{original_show_id}' → '{corrected_show_id}' (date: {original_date_from_id} → {iso_date})")
                        show_data["show_id"] = corrected_show_id
                
                # Use date as key for matching
                date_key = show_data.get("date")
                if date_key:
                    if date_key not in shows:
                        shows[date_key] = []
                    shows[date_key].append(show_data)
                
            except Exception as e:
                self.logger.warning(f"Skipping corrupted show file {show_file}: {e}")
                continue
        
        total_shows = sum(len(show_list) for show_list in shows.values())
        self.logger.info(f"Successfully loaded {total_shows} shows across {len(shows)} dates")
        return shows
    
    def load_archive_recordings(self) -> Dict[str, List[RecordingMetadata]]:
        """Load all Archive.org recording metadata grouped by date."""
        recordings_by_date = defaultdict(list)
        recording_files = [f for f in self.archive_dir.glob("*.json") 
                          if not f.name.startswith(('progress', 'collection'))]
        
        self.logger.info(f"Loading {len(recording_files)} Archive recordings...")
        
        for recording_file in recording_files:
            try:
                with open(recording_file, 'r') as f:
                    data = json.load(f)
                recording_meta = RecordingMetadata(**data)
                recordings_by_date[recording_meta.date].append(recording_meta)
            except Exception as e:
                self.logger.warning(f"Skipping corrupted recording file {recording_file}: {e}")
                continue
        
        total_recordings = sum(len(rec_list) for rec_list in recordings_by_date.values())
        self.logger.info(f"Successfully loaded {total_recordings} recordings across {len(recordings_by_date)} dates")
        return dict(recordings_by_date)
    
    def detect_recording_time(self, identifier: str) -> Optional[str]:
        """
        Detect show time from recording identifier.
        Returns: "early", "late", "early-late", or None
        Examples:
        - "gd1970-02-13.early.sbd.murphy..." -> "early"
        - "gd1970-02-13.lateshow.mtx..." -> "late"  
        - "gd70-02-13.early-late.sbd..." -> "early-late"
        - "gd1970-02-13.sbd.miller..." -> None
        """
        identifier_lower = identifier.lower()
        
        if 'early-late' in identifier_lower:
            return 'early-late'
        elif 'early' in identifier_lower:
            return 'early'
        elif 'late' in identifier_lower or 'lateshow' in identifier_lower:
            return 'late'
        else:
            return None
    
    def improve_source_type_detection(self, recording: RecordingMetadata) -> str:
        """Improve source type detection by checking identifier/filename as well."""
        identifier = recording.identifier.upper()
        title = recording.title.upper() if recording.title else ""
        description = recording.description.upper() if recording.description else ""
        
        text = f"{identifier} {title} {description}"
        
        if 'SBD' in text or 'SOUNDBOARD' in text:
            return 'SBD'
        elif 'MATRIX' in text:
            return 'MATRIX'  
        elif 'AUD' in text or 'AUDIENCE' in text or '.AUD.' in identifier:
            return 'AUD'
        elif 'FM' in text or 'BROADCAST' in text:
            return 'FM'
        elif 'REMASTER' in text:
            return 'REMASTER'
        else:
            return 'UNKNOWN'
    
    def filter_recordings_by_show_time(self, recordings: List[RecordingMetadata], 
                                     show_time: Optional[str]) -> List[RecordingMetadata]:
        """
        Filter recordings based on show time.
        Logic:
        - Early show: include 'early', 'early-late', and recordings with no time modifier
        - Late show: include 'late', 'early-late', and recordings with no time modifier
        - Regular show (no time): include all recordings
        """
        if show_time is None:
            # Regular show - include all recordings
            return recordings
        
        filtered_recordings = []
        
        for recording in recordings:
            recording_time = self.detect_recording_time(recording.identifier)
            
            if recording_time is None:
                # No time modifier - include in both early and late shows
                filtered_recordings.append(recording)
            elif recording_time == 'early-late':
                # Contains both shows - include in both early and late shows
                filtered_recordings.append(recording)
            elif show_time == 'early' and recording_time == 'early':
                # Early show gets early recordings
                filtered_recordings.append(recording)
            elif show_time == 'late' and recording_time == 'late':
                # Late show gets late recordings  
                filtered_recordings.append(recording)
        
        return filtered_recordings
    
    def normalize_venue_name(self, venue: str) -> str:
        """Normalize venue name for better matching."""
        if not venue:
            return ""
        
        # Convert to lowercase
        normalized = venue.lower().strip()
        
        # Common venue name normalizations
        normalized = normalized.replace('theatre', 'theater')
        normalized = normalized.replace('&', 'and')
        normalized = normalized.replace('univ.', 'university')
        normalized = normalized.replace('univ', 'university')
        normalized = normalized.replace('u.', 'university')
        normalized = normalized.replace('coll.', 'college')
        normalized = normalized.replace('coll', 'college')
        
        # Remove extra whitespace and punctuation
        normalized = ' '.join(normalized.split())  # normalize spaces
        normalized = normalized.replace(',', '').replace('.', '')
        
        return normalized
    
    def calculate_venue_similarity(self, archive_venue: str, jg_venue: str) -> float:
        """Calculate similarity score between venue names (0-1)."""
        arch_norm = self.normalize_venue_name(archive_venue)
        jg_norm = self.normalize_venue_name(jg_venue)
        
        # Exact match
        if arch_norm == jg_norm:
            return 1.0
        
        # Check if one contains the other (partial match)
        if arch_norm in jg_norm or jg_norm in arch_norm:
            return 0.8
        
        # Check for key word matches
        arch_words = set(arch_norm.split())
        jg_words = set(jg_norm.split())
        
        if not arch_words or not jg_words:
            return 0.0
        
        # Calculate word overlap
        common_words = arch_words.intersection(jg_words)
        total_words = arch_words.union(jg_words)
        
        if len(total_words) == 0:
            return 0.0
            
        similarity = len(common_words) / len(total_words)
        
        # Boost score if multiple important words match
        if len(common_words) >= 2:
            similarity = min(1.0, similarity + 0.2)
        
        return similarity
    
    def should_use_venue_matching(self, shows_on_date: List[Dict[str, Any]]) -> bool:
        """
        Determine if venue matching should be used.
        Conditions: Multiple shows, no early/late shows, different venues.
        """
        # Condition 1: Multiple shows
        if len(shows_on_date) <= 1:
            return False
        
        # Condition 2: No early/late shows 
        for show in shows_on_date:
            if show.get('show_time') is not None:
                return False  # Use time-based matching instead
        
        # Condition 3: Different venues
        venues = [show.get('venue', '') for show in shows_on_date]
        unique_venues = set(self.normalize_venue_name(v) for v in venues if v)
        if len(unique_venues) <= 1:
            return False  # Same venue, no need for venue matching
        
        return True
    
    def enrich_show_with_recordings(self, show_data: Dict[str, Any], 
                                   recordings: List[RecordingMetadata],
                                   all_shows_on_date: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enrich show data with Archive.org recording metadata."""
        # Initialize reporting fields
        matching_method = "date_only"
        filtering_applied = []
        
        if not recordings:
            # No recordings for this show
            show_data.update({
                "recordings": [],
                "best_recording": None,
                "avg_rating": 0.0,
                "recording_count": 0,
                "confidence": 0.0,
                "source_types": {},
                "matching_method": matching_method,
                "filtering_applied": filtering_applied
            })
            return show_data
        
        # Start with all recordings for this date
        filtered_recordings = recordings.copy()
        
        # Level 1: Filter by show time (early/late/regular)
        show_time = show_data.get("show_time")
        original_count = len(filtered_recordings)
        if show_time is not None:
            filtered_recordings = self.filter_recordings_by_show_time(filtered_recordings, show_time)
            matching_method = "time_based"
            filtering_applied.append(f"show_time: {show_time}")
            # Only log for early/late shows
            self.logger.info(f"  Time filtering ({show_time}): {original_count} → {len(filtered_recordings)} recordings for {show_data.get('show_id', 'unknown')}")
        
        # Level 2: Filter by venue (if conditions are met)
        if all_shows_on_date and self.should_use_venue_matching(all_shows_on_date):
            # Only log for venue-matched shows
            self.logger.info(f"  Venue matching enabled for date {show_data.get('date')} - {len(all_shows_on_date)} shows with different venues")
            venue_matched_recordings = []
            unmatched_recordings = []
            show_venue = show_data.get('venue', '')
            
            VENUE_MATCH_THRESHOLD = 0.7
            
            for recording in filtered_recordings:
                best_similarity = 0.0
                best_match_show = None
                
                # Check similarity with all shows on this date
                for show in all_shows_on_date:
                    similarity = self.calculate_venue_similarity(recording.venue, show.get('venue', ''))
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match_show = show
                
                if best_similarity >= VENUE_MATCH_THRESHOLD:
                    # Strong venue match - check if it matches THIS show
                    this_show_similarity = self.calculate_venue_similarity(recording.venue, show_venue)
                    if this_show_similarity >= VENUE_MATCH_THRESHOLD:
                        venue_matched_recordings.append(recording)
                        self.logger.debug(f"    Recording {recording.identifier}: '{recording.venue}' → '{show_venue}' (similarity: {this_show_similarity:.2f})")
                else:
                    # Weak venue match - include in all shows
                    unmatched_recordings.append(recording)
                    self.logger.debug(f"    Recording {recording.identifier}: weak venue match, included in all shows")
            
            # Use venue-filtered recordings
            pre_venue_count = len(filtered_recordings)
            filtered_recordings = venue_matched_recordings + unmatched_recordings
            matching_method = "venue_based"
            filtering_applied.append(f"venue_matching: {len(venue_matched_recordings)} matched, {len(unmatched_recordings)} unmatched")
            # Only log for venue-matched shows
            self.logger.info(f"  Venue filtering: {pre_venue_count} → {len(filtered_recordings)} recordings ({len(venue_matched_recordings)} venue-matched, {len(unmatched_recordings)} shared) for {show_data.get('show_id', 'unknown')}")
        
        if not filtered_recordings:
            # No recordings match this show after filtering
            show_data.update({
                "recordings": [],
                "best_recording": None,
                "avg_rating": 0.0,
                "recording_count": 0,
                "confidence": 0.0,
                "source_types": {},
                "matching_method": matching_method,
                "filtering_applied": filtering_applied
            })
            return show_data
        
        # Improve source type detection for all filtered recordings
        for recording in filtered_recordings:
            improved_source_type = self.improve_source_type_detection(recording)
            recording.source_type = improved_source_type
        
        # Sort recordings by preference (FM > SBD > MATRIX > others, then by rating)
        filtered_recordings.sort(key=lambda r: (
            r.source_type == 'FM' and r.review_count >= 3,
            r.source_type == 'FM',  # Prefer FM even with fewer reviews
            r.source_type == 'SBD' and r.review_count >= 3,
            r.source_type == 'SBD',  # Prefer SBD over MATRIX
            r.source_type == 'MATRIX' and r.review_count >= 3,
            r.source_type == 'MATRIX',  # Prefer MATRIX over AUD sources
            r.review_count >= 5,
            r.rating,
            r.review_count
        ), reverse=True)
        
        best_recording = filtered_recordings[0]
        
        # Calculate aggregate rating
        total_weight = 0
        weighted_sum = 0
        
        for recording in filtered_recordings:
            weight = recording.review_count * self.source_weights.get(recording.source_type, 0.5)
            weighted_sum += recording.rating * weight
            total_weight += weight
        
        avg_rating = weighted_sum / total_weight if total_weight > 0 else 0
        total_reviews = sum(r.review_count for r in filtered_recordings)
        confidence = min(total_reviews / 10.0, 1.0)
        
        # Count source types
        source_types = defaultdict(int)
        for recording in filtered_recordings:
            source_types[recording.source_type] += 1
        
        # Add recording enrichment to show data
        show_data.update({
            "recordings": [r.identifier for r in filtered_recordings],
            "best_recording": best_recording.identifier,
            "avg_rating": avg_rating,
            "recording_count": len(filtered_recordings),
            "confidence": confidence,
            "source_types": dict(source_types),
            "matching_method": matching_method,
            "filtering_applied": filtering_applied
        })
        
        # Summary logging - only for early/late or venue-based matching
        if matching_method in ["time_based", "venue_based"]:
            source_summary = ", ".join(f"{k}:{v}" for k, v in source_types.items())
            self.logger.info(f"  Final: {show_data.get('show_id', 'unknown')} → {len(filtered_recordings)} recordings ({source_summary}) | Method: {matching_method} | Best: {best_recording.source_type}")
        
        return show_data
    
    def integrate_all_shows(self) -> Dict[str, Any]:
        """Integrate all JerryGarcia shows with Archive recordings."""
        self.logger.info("Starting show integration...")
        
        # Load data
        shows_by_date = self.load_jerrygarcia_shows()
        recordings_by_date = self.load_archive_recordings()
        
        integrated_shows = {}
        total_shows = 0
        shows_with_recordings = 0
        
        # Integrate each show
        for date, show_list in shows_by_date.items():
            recordings = recordings_by_date.get(date, [])
            
            for show_data in show_list:
                # Enrich show with recording data (pass all shows on date for venue matching context)
                enriched_show = self.enrich_show_with_recordings(show_data.copy(), recordings, show_list)
                
                # Use show_id as key for output
                show_id = enriched_show.get("show_id", f"{date}-unknown")
                integrated_shows[show_id] = enriched_show
                
                total_shows += 1
                if recordings:
                    shows_with_recordings += 1
                
                # Save individual show file
                show_file = self.shows_dir / f"{show_id}.json"
                with open(show_file, 'w') as f:
                    json.dump(enriched_show, f, indent=2, default=str)
        
        self.logger.info(f"✅ Integrated {total_shows} shows")
        self.logger.info(f"✅ {shows_with_recordings} shows have Archive recordings")
        self.logger.info(f"✅ {total_shows - shows_with_recordings} shows have no recordings")
        
        return integrated_shows
    
    def process_integration(self) -> bool:
        """Process the complete integration."""
        start_time = datetime.now()
        
        # Integrate shows
        integrated_shows = self.integrate_all_shows()
        
        if not integrated_shows:
            self.logger.error("No shows integrated. Cannot proceed.")
            return False
        
        # Report processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"✅ Integration completed in {processing_time:.1f} seconds")
        
        # Summary
        self.logger.info("=== Integration Summary ===")
        self.logger.info(f"Total shows: {len(integrated_shows)}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Individual shows: {self.shows_dir}")
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Integrate JerryGarcia shows with Archive.org recordings')
    parser.add_argument('--jerrygarcia-dir', default='stage01-collected-data/jerrygarcia/shows', 
                       help='Directory with JerryGarcia show files')
    parser.add_argument('--archive-dir', default='stage01-collected-data/archive',
                       help='Directory with Archive.org recording files')
    parser.add_argument('--output-dir', default='stage02-generated-data',
                       help='Output directory for integrated shows')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    integrator = JerryGarciaShowIntegrator(
        jerrygarcia_dir=args.jerrygarcia_dir,
        archive_dir=args.archive_dir,
        output_dir=args.output_dir
    )
    
    # Validate input
    if not integrator.validate_input_data():
        return 1
    
    # Create output directories
    integrator.create_output_directories()
    
    # Process integration
    success = integrator.process_integration()
    
    if success:
        print(f"✅ Integration complete! Output: {args.output_dir}")
        return 0
    else:
        print("❌ Integration failed. Check logs for details.")
        return 1


if __name__ == '__main__':
    exit(main())