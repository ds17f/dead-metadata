#!/usr/bin/env python3
"""
Generate pre-computed show ratings from Archive.org data.

This script fetches review data for Grateful Dead recordings and computes
show-level ratings using a MAX rating approach (not average) that prioritizes
SBD recordings and well-reviewed performances.

IMPORTANT: Uses MAX rating instead of average to avoid dilution by unrated recordings.
A show with one 4.5★ SBD + two unrated recordings gets 4.5★, not ~2.25★.

Usage:
    python scripts/generate_ratings.py --output scripts/metadata/ratings.json
"""

import json
import re
import requests
import time
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import argparse
import logging
from dataclasses import dataclass


@dataclass
class ReviewData:
    """Individual review data"""
    stars: float
    review_text: str
    date: str
    
@dataclass
class RecordingRating:
    """Aggregated rating for a single recording"""
    identifier: str
    avg_rating: float        # Weighted/computed rating (for internal ranking)
    raw_rating: float        # Simple average of all reviews (for display)
    review_count: int
    source_type: str         # 'SBD', 'AUD', 'MATRIX', etc.
    reviews: List[ReviewData]
    distribution: Dict[int, int]  # Star rating distribution {1: 7, 2: 6, 3: 5, 4: 8, 5: 4}
    high_ratings: int        # Count of 4-5 star reviews  
    low_ratings: int         # Count of 1-2 star reviews

@dataclass 
class ShowRating:
    """Aggregated rating for an entire show"""
    date: str
    venue: str
    avg_rating: float         # Weighted rating (for ranking)
    raw_rating: float         # Simple average rating (for display)
    confidence_score: float   # 0-1 scale based on review count and source quality
    best_recording_id: str
    recording_ratings: List[RecordingRating]
    total_high_ratings: int   # Count of 4-5★ reviews across all recordings
    total_low_ratings: int    # Count of 1-2★ reviews across all recordings


class GratefulDeadRatingsGenerator:
    """
    Generates pre-computed show ratings for Grateful Dead performances.
    """
    
    def __init__(self):
        """Initialize the generator with configuration."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DeadArchive-RatingsGenerator/1.0 (Educational Use)'
        })
        
        # Rate limiting configuration
        self.api_delay = 1.0  # seconds between API calls
        self.last_api_call = 0
        
        # Rating aggregation weights
        self.source_weights = {
            'SBD': 1.0,      # Soundboard - highest quality
            'MATRIX': 0.9,   # Matrix mix - very good
            'AUD': 0.7,      # Audience recording - lower weight
            'FM': 0.8,       # FM broadcast - good quality
            'REMASTER': 1.0, # Remastered - high quality
        }
        
        # Minimum thresholds
        self.min_reviews_for_confidence = 3
        self.min_rating_for_inclusion = 2.5
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self.last_api_call
        if elapsed < self.api_delay:
            time.sleep(self.api_delay - elapsed)
        self.last_api_call = time.time()

    def normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normalize various date formats to YYYY-MM-DD.
        
        Archive.org uses inconsistent date formats:
        - "1977-05-08T00:00:00Z"
        - "1977-05-08" 
        - "1977-5-8"
        - "05/08/1977"
        """
        if not date_str:
            return None
            
        # Remove time component if present
        date_str = date_str.split('T')[0]
        
        # Handle YYYY-MM-DD (already normalized)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
            
        # Handle YYYY-M-D (pad with zeros)
        if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str):
            parts = date_str.split('-')
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            
        # Handle MM/DD/YYYY
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
            parts = date_str.split('/')
            return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            
        # Handle other formats as needed
        self.logger.warning(f"Unrecognized date format: {date_str}")
        return None

    def extract_source_type(self, title: str, description: str) -> str:
        """
        Extract recording source type from title and description.
        
        Common patterns:
        - "gd77-05-08.sbd.miller.89174.flac16" -> SBD
        - "gd1977-05-08.aud.vernon.32515.flac16" -> AUD  
        - "gd1977-05-08d1t01.matrix.flac16" -> MATRIX
        """
        text = f"{title} {description}".upper()
        
        if 'SBD' in text or 'SOUNDBOARD' in text:
            return 'SBD'
        elif 'MATRIX' in text:
            return 'MATRIX'  
        elif 'AUD' in text or 'AUDIENCE' in text:
            return 'AUD'
        elif 'FM' in text or 'BROADCAST' in text:
            return 'FM'
        elif 'REMASTER' in text:
            return 'REMASTER'
        else:
            return 'UNKNOWN'

    def fetch_recording_metadata(self, identifier: str) -> Optional[Dict]:
        """Fetch metadata for a single recording from Archive.org."""
        self.rate_limit()
        
        try:
            url = f"https://archive.org/metadata/{identifier}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch metadata for {identifier}: {e}")
            return None

    def fetch_recording_reviews(self, identifier: str) -> List[ReviewData]:
        """Fetch review data for a single recording."""
        self.rate_limit()
        
        try:
            url = f"https://archive.org/metadata/{identifier}/reviews"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            reviews_data = response.json()
            reviews = []
            
            for review in reviews_data.get('reviews', []):
                stars = float(review.get('stars', 0))
                if stars > 0:  # Only include reviews with ratings
                    reviews.append(ReviewData(
                        stars=stars,
                        review_text=review.get('reviewtitle', '') + ' ' + review.get('reviewbody', ''),
                        date=review.get('reviewdate', '')
                    ))
                    
            return reviews
            
        except Exception as e:
            self.logger.error(f"Failed to fetch reviews for {identifier}: {e}")
            return []

    def get_grateful_dead_recordings(self) -> List[str]:
        """
        Get list of Grateful Dead recording identifiers from Archive.org search.
        
        This uses the Archive.org search API to find all GD recordings.
        We'll limit to a manageable subset for initial implementation.
        """
        self.rate_limit()
        
        try:
            # Search for Grateful Dead recordings
            # Note: This is a simplified search - you may need to paginate for complete data
            search_url = "https://archive.org/advancedsearch.php"
            params = {
                'q': 'collection:GratefulDead AND mediatype:etree',
                'fl': 'identifier,date,title,venue',
                'sort[]': 'date asc',
                'rows': 1000,  # Limit for initial testing
                'output': 'json'
            }
            
            response = self.session.get(search_url, params=params, timeout=60)
            response.raise_for_status()
            
            search_results = response.json()
            identifiers = []
            
            for doc in search_results.get('response', {}).get('docs', []):
                identifier = doc.get('identifier')
                if identifier:
                    identifiers.append(identifier)
                    
            self.logger.info(f"Found {len(identifiers)} Grateful Dead recordings")
            return identifiers
            
        except Exception as e:
            self.logger.error(f"Failed to search for recordings: {e}")
            return []

    def compute_recording_rating(self, identifier: str, reviews: List[ReviewData], source_type: str) -> Optional[RecordingRating]:
        """
        Compute comprehensive rating data for a single recording.
        
        Returns both weighted (for ranking) and raw (for display) ratings,
        plus distribution and context data.
        """
        if not reviews:
            return None
            
        # Filter out very low ratings (likely spam/errors)
        valid_reviews = [r for r in reviews if r.stars >= 1.0]
        if not valid_reviews:
            return None
        
        # Compute raw average (for display) 
        raw_rating = sum(r.stars for r in valid_reviews) / len(valid_reviews)
        
        # Compute weighted rating (for internal ranking)
        source_weight = self.source_weights.get(source_type, 0.5)
        weighted_rating = raw_rating * source_weight
        
        # Confidence adjustment
        confidence_factor = min(len(valid_reviews) / 5.0, 1.0)
        final_weighted_rating = weighted_rating * (0.5 + 0.5 * confidence_factor)
        
        # Calculate rating distribution
        distribution = {}
        for star in range(1, 6):
            count = sum(1 for r in valid_reviews if int(r.stars) == star)
            if count > 0:
                distribution[star] = count
        
        # Count high and low ratings
        high_ratings = sum(1 for r in valid_reviews if r.stars >= 4.0)
        low_ratings = sum(1 for r in valid_reviews if r.stars <= 2.0)
        
        return RecordingRating(
            identifier=identifier,
            avg_rating=final_weighted_rating,  # Weighted rating for ranking
            raw_rating=raw_rating,             # Simple average for display  
            review_count=len(valid_reviews),
            source_type=source_type,
            reviews=valid_reviews,
            distribution=distribution,
            high_ratings=high_ratings,
            low_ratings=low_ratings
        )

    def compute_show_rating(self, recording_ratings: List[RecordingRating]) -> ShowRating:
        """
        Compute overall show rating from individual recording ratings.
        
        Uses MAX rating approach instead of average to avoid dilution by unrated recordings:
        1. Filter out recordings with no ratings (avg_rating = 0 or review_count = 0)
        2. Prefer SBD recordings with 3+ reviews
        3. Fall back to any well-reviewed recording (5+ reviews)
        4. Use the highest rated recording as the show rating
        """
        if not recording_ratings:
            return None
        
        # Filter out recordings with no ratings - these shouldn't dilute the show rating
        rated_recordings = [
            r for r in recording_ratings 
            if r.avg_rating > 0 and r.review_count > 0
        ]
        
        if not rated_recordings:
            return None  # No ratings available for this show
            
        # Sort by preference: SBD with reviews first, then by rating
        sorted_recordings = sorted(
            rated_recordings,
            key=lambda r: (
                r.source_type == 'SBD' and r.review_count >= 3,  # SBD with good reviews
                r.review_count >= 5,  # Well-reviewed regardless of source
                r.avg_rating,  # Rating quality
                r.review_count  # Review quantity
            ),
            reverse=True
        )
        
        best_recording = sorted_recordings[0]
        
        # Use the best recording's rating as the show rating (no averaging/dilution)
        show_avg_rating = best_recording.avg_rating
        show_raw_rating = best_recording.raw_rating
        
        # Compute confidence score based on the best recording's review count
        # but also consider total reviews across all rated recordings
        total_reviews = sum(r.review_count for r in rated_recordings)
        best_recording_reviews = best_recording.review_count
        
        # Confidence combines individual recording confidence with total show review activity
        individual_confidence = min(best_recording_reviews / 5.0, 1.0)  # Max confidence at 5+ reviews for best recording
        total_confidence = min(total_reviews / 10.0, 1.0)  # Bonus confidence for multiple rated recordings
        confidence_score = (individual_confidence + total_confidence) / 2.0  # Average of both factors
        
        # Aggregate high/low rating counts across all recordings
        total_high_ratings = sum(r.high_ratings for r in rated_recordings)
        total_low_ratings = sum(r.low_ratings for r in rated_recordings)
        
        # Extract show info from best recording (assuming consistent per show)
        # In real implementation, you'd get this from the recording metadata
        show_date = "1977-05-08"  # Placeholder - extract from metadata
        show_venue = "Barton Hall, Cornell University"  # Placeholder
        
        return ShowRating(
            date=show_date,
            venue=show_venue,
            avg_rating=show_avg_rating,
            raw_rating=show_raw_rating,
            confidence_score=confidence_score,
            best_recording_id=best_recording.identifier,
            recording_ratings=recording_ratings,
            total_high_ratings=total_high_ratings,
            total_low_ratings=total_low_ratings
        )

    def generate_ratings_data(self, max_recordings: int = 100) -> Dict:
        """
        Generate the complete ratings dataset.
        
        Args:
            max_recordings: Limit processing for testing (remove for production)
        """
        self.logger.info("Starting ratings generation process...")
        
        # Get list of recordings to process
        recording_ids = self.get_grateful_dead_recordings()
        if max_recordings:
            recording_ids = recording_ids[:max_recordings]
            
        self.logger.info(f"Processing {len(recording_ids)} recordings...")
        
        # Group recordings by show (date + venue)
        shows_data = defaultdict(list)
        recording_ratings_data = {}
        
        processed_count = 0
        
        for identifier in recording_ids:
            try:
                self.logger.info(f"Processing {identifier} ({processed_count + 1}/{len(recording_ids)})")
                
                # Fetch metadata and reviews
                metadata = self.fetch_recording_metadata(identifier)
                if not metadata:
                    continue
                    
                reviews = self.fetch_recording_reviews(identifier)
                if not reviews:
                    self.logger.info(f"No reviews found for {identifier}")
                    continue
                
                # Extract recording info
                title = metadata.get('metadata', {}).get('title', '')
                description = metadata.get('metadata', {}).get('description', '')
                date_str = metadata.get('metadata', {}).get('date', '')
                venue = metadata.get('metadata', {}).get('venue', '')
                
                normalized_date = self.normalize_date(date_str)
                if not normalized_date:
                    continue
                    
                source_type = self.extract_source_type(title, description)
                
                # Compute recording rating
                recording_rating = self.compute_recording_rating(identifier, reviews, source_type)
                
                # Skip recordings with no rating or very low ratings
                if recording_rating is None or recording_rating.avg_rating < self.min_rating_for_inclusion:
                    # Store recording with null rating for records
                    recording_ratings_data[identifier] = {
                        'rating': None,
                        'raw_rating': None,
                        'review_count': 0,
                        'source_type': source_type,
                        'confidence': None,
                        'distribution': {},
                        'high_ratings': 0,
                        'low_ratings': 0
                    }
                    continue
                
                # Store recording-level data with new comprehensive structure
                recording_ratings_data[identifier] = {
                    'rating': recording_rating.avg_rating,           # Weighted rating for ranking
                    'raw_rating': recording_rating.raw_rating,       # Simple average for display
                    'review_count': recording_rating.review_count,
                    'source_type': recording_rating.source_type,
                    'confidence': min(recording_rating.review_count / 5.0, 1.0),
                    'distribution': recording_rating.distribution,   # NEW: {1: 7, 2: 6, ...}
                    'high_ratings': recording_rating.high_ratings,   # NEW: Count of 4-5★
                    'low_ratings': recording_rating.low_ratings      # NEW: Count of 1-2★
                }
                
                # Group by show
                show_key = f"{normalized_date}_{venue.replace(' ', '_')}"
                shows_data[show_key].append(recording_rating)
                
                processed_count += 1
                
            except Exception as e:
                self.logger.error(f"Error processing {identifier}: {e}")
                continue
        
        # Compute show-level ratings
        self.logger.info("Computing show-level ratings...")
        show_ratings_data = {}
        top_shows = []
        
        for show_key, recordings in shows_data.items():
            try:
                show_rating = self.compute_show_rating(recordings)
                if show_rating and show_rating.avg_rating >= self.min_rating_for_inclusion:
                    show_ratings_data[show_key] = {
                        'date': show_rating.date,
                        'venue': show_rating.venue,
                        'rating': show_rating.avg_rating,      # Weighted rating for ranking
                        'raw_rating': show_rating.raw_rating,  # Simple average for display
                        'confidence': show_rating.confidence_score,
                        'best_recording': show_rating.best_recording_id,
                        'recording_count': len(recordings),
                        'high_ratings': show_rating.total_high_ratings,  # NEW: Total 4-5★ reviews
                        'low_ratings': show_rating.total_low_ratings     # NEW: Total 1-2★ reviews
                    }
                    
                    # Track top shows
                    if show_rating.confidence_score >= 0.7:  # High confidence only
                        top_shows.append({
                            'show_key': show_key,
                            'rating': show_rating.avg_rating,
                            'date': show_rating.date,
                            'venue': show_rating.venue
                        })
                        
            except Exception as e:
                self.logger.error(f"Error computing show rating for {show_key}: {e}")
                continue
        
        # Sort top shows by rating
        top_shows.sort(key=lambda x: x['rating'], reverse=True)
        
        # Compile final dataset
        ratings_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'total_recordings': len(recording_ratings_data),
                'total_shows': len(show_ratings_data),
                'processing_notes': f"Processed {processed_count} recordings with {len([r for r in recording_ratings_data.values() if r['review_count'] >= self.min_reviews_for_confidence])} well-reviewed"
            },
            'recording_ratings': recording_ratings_data,
            'show_ratings': show_ratings_data,
            'top_shows': top_shows[:100]  # Top 100 shows
        }
        
        self.logger.info(f"Generated ratings for {len(show_ratings_data)} shows from {len(recording_ratings_data)} recordings")
        return ratings_data

    def save_ratings_data(self, ratings_data: Dict, output_path: str):
        """Save the generated ratings data to JSON file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(ratings_data, f, indent=2, sort_keys=True)
            self.logger.info(f"Ratings data saved to {output_path}")
            
            # Print summary statistics
            metadata = ratings_data['metadata']
            self.logger.info(f"Summary:")
            self.logger.info(f"  - Total recordings: {metadata['total_recordings']}")
            self.logger.info(f"  - Total shows: {metadata['total_shows']}")
            self.logger.info(f"  - Top shows: {len(ratings_data['top_shows'])}")
            
        except Exception as e:
            self.logger.error(f"Failed to save ratings data: {e}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Generate pre-computed show ratings for Grateful Dead recordings')
    parser.add_argument('--output', default='scripts/metadata/ratings.json', 
                       help='Output path for ratings JSON file')
    parser.add_argument('--max-recordings', type=int, default=100,
                       help='Maximum recordings to process (for testing)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Generate ratings
    generator = GratefulDeadRatingsGenerator()
    ratings_data = generator.generate_ratings_data(max_recordings=args.max_recordings)
    
    # Save to file
    generator.save_ratings_data(ratings_data, args.output)
    
    print(f"✅ Ratings generation complete! Output saved to {args.output}")


if __name__ == '__main__':
    main()