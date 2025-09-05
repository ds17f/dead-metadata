#!/usr/bin/env python3
"""
Shared Recording Utilities

Common functions for processing Archive.org recording data across multiple scripts.
This module contains reusable logic for source type detection, rating calculations,
and other recording-related operations.
"""

from typing import Optional
from .models import RecordingMetadata


def improve_source_type_detection(recording) -> str:
    """
    Improve source type detection by analyzing identifier, metadata, and source lineage.
    
    This function examines the recording identifier, title, description, and most importantly
    the source lineage field to determine the most likely source type, which is more accurate
    than relying solely on the source_type field from Archive.org.
    
    Args:
        recording: RecordingMetadata or ProcessedRecordingMetadata object to analyze
        
    Returns:
        Improved source type string: 'SBD', 'MATRIX', 'AUD', 'FM', 'REMASTER', or 'UNKNOWN'
    """
    identifier = recording.identifier.upper()
    
    # Handle both RecordingMetadata (properties) and ProcessedRecordingMetadata (fields)
    if hasattr(recording, 'title') and callable(getattr(recording, 'title', None)):
        # RecordingMetadata with properties
        title = recording.title.upper() if recording.title else ""
        description = recording.description.upper() if recording.description else ""
        source_lineage = recording.source.upper() if recording.source else ""
    else:
        # ProcessedRecordingMetadata with fields
        title = getattr(recording, 'title', '').upper() if getattr(recording, 'title', '') else ""
        description = getattr(recording, 'description', '').upper() if getattr(recording, 'description', '') else ""
        source_lineage = getattr(recording, 'source', '').upper() if getattr(recording, 'source', '') else ""
    
    # Primary analysis: Check source lineage first (most reliable)
    if source_lineage:
        if source_lineage.startswith('SBD'):
            return 'SBD'
        elif source_lineage.startswith('AUD'):
            return 'AUD'
        elif 'MATRIX' in source_lineage:
            return 'MATRIX'
        elif source_lineage.startswith('FM') or 'FM ' in source_lineage or source_lineage.startswith('BROADCAST'):
            return 'FM'
        # Check for microphone indicators (suggests audience recording)
        elif any(mic in source_lineage for mic in ['MICROPHONE', 'SENNHEISER', 'AKG', 'NEUMANN', 'SONY', 'MIC']):
            return 'AUD'
    
    # Secondary analysis: Check identifier patterns  
    if '.SBD.' in identifier or '.SOUNDBOARD.' in identifier or identifier.endswith('.SBD'):
        return 'SBD'
    elif '.MTX.' in identifier or '.MATRIX.' in identifier:
        return 'MATRIX'  
    elif '.AUD.' in identifier or '.AUDIENCE.' in identifier or identifier.endswith('.AUD'):
        return 'AUD'
    elif '.FM.' in identifier or '.BROADCAST.' in identifier or identifier.endswith('.FM'):
        return 'FM'
    elif '.REMASTER.' in identifier:
        return 'REMASTER'
    
    # Tertiary analysis: Check all text for keywords
    text = f"{identifier} {title} {description} {source_lineage}"
    
    if 'SBD' in text or 'SOUNDBOARD' in text:
        return 'SBD'
    elif 'MATRIX' in text:
        return 'MATRIX'  
    elif 'AUD' in text or 'AUDIENCE' in text:
        return 'AUD'
    elif 'FM' in text or 'BROADCAST' in text or 'RADIO' in text:
        return 'FM'
    elif 'REMASTER' in text:
        return 'REMASTER'
    else:
        return 'UNKNOWN'


def detect_recording_time(identifier: str) -> Optional[str]:
    """
    Detect show time from recording identifier.
    
    Many recordings include time indicators in their identifiers to distinguish
    between early and late shows on the same date.
    
    Args:
        identifier: Recording identifier string to analyze
        
    Returns:
        Show time indicator: "early", "late", "early-late", or None
        
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


def normalize_venue_name(venue: str) -> str:
    """
    Normalize venue name for better matching between different data sources.
    
    This function standardizes common venue name variations to improve
    matching accuracy when combining data from different sources.
    
    Args:
        venue: Raw venue name string
        
    Returns:
        Normalized venue name string
    """
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


def calculate_venue_similarity(venue1: str, venue2: str) -> float:
    """
    Calculate similarity score between two venue names.
    
    This function uses various heuristics to determine how similar two venue
    names are, which is useful for matching recordings to shows when venue
    names might be slightly different between data sources.
    
    Args:
        venue1: First venue name to compare
        venue2: Second venue name to compare
        
    Returns:
        Similarity score between 0.0 (no match) and 1.0 (perfect match)
    """
    norm1 = normalize_venue_name(venue1)
    norm2 = normalize_venue_name(venue2)
    
    # Exact match
    if norm1 == norm2:
        return 1.0
    
    # Check if one contains the other (partial match)
    if norm1 in norm2 or norm2 in norm1:
        return 0.8
    
    # Check for key word matches
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    if not words1 or not words2:
        return 0.0
    
    # Calculate word overlap
    common_words = words1.intersection(words2)
    total_words = words1.union(words2)
    
    if len(total_words) == 0:
        return 0.0
        
    similarity = len(common_words) / len(total_words)
    
    # Boost score if multiple important words match
    if len(common_words) >= 2:
        similarity = min(1.0, similarity + 0.2)
    
    return similarity