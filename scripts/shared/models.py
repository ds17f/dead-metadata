#!/usr/bin/env python3
"""
Shared Data Models for Dead Archive Pipeline

This module contains all dataclasses used across the collection and generation
stages of the Dead Archive metadata pipeline. These models ensure consistency
and type safety across all pipeline components.

Used by:
- scripts/01-collect-data/collect_archive_metadata.py
- scripts/02-generate-data/generate_archive_products.py
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any


@dataclass
class ReviewData:
    """Individual review data from Archive.org"""
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
    rating: float                             # Weighted rating (for internal ranking)
    review_count: int
    confidence: float
    collection_timestamp: str
    raw_rating: float = 0.0                  # Simple average (for display)
    distribution: Dict[int, int] = None      # Star rating distribution {1: 7, 2: 6, ...}
    high_ratings: int = 0                    # Count of 4-5★ reviews
    low_ratings: int = 0                     # Count of 1-2★ reviews
    
    def __post_init__(self):
        if self.distribution is None:
            self.distribution = {}


@dataclass
class ShowMetadata:
    """Aggregated metadata for an entire show"""
    show_key: str
    date: str
    venue: str
    location: str
    recordings: List[str]  # List of recording identifiers
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


def recording_to_dict(recording: RecordingMetadata) -> Dict[str, Any]:
    """Convert RecordingMetadata to dictionary, handling nested objects"""
    return asdict(recording)


def show_to_dict(show: ShowMetadata) -> Dict[str, Any]:
    """Convert ShowMetadata to dictionary"""
    return asdict(show)


def progress_to_dict(progress: ProgressState) -> Dict[str, Any]:
    """Convert ProgressState to dictionary"""
    return asdict(progress)