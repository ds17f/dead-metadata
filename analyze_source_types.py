#!/usr/bin/env python3
"""
Source Type Analysis Script

Analyzes all recording JSON files and provides counts by source type.
Can be used to measure improvements in source type classification.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

def analyze_source_types(recordings_dir: str = "stage02-generated-data/recordings"):
    """Analyze source types from all recording JSON files."""
    
    recordings_path = Path(recordings_dir)
    if not recordings_path.exists():
        print(f"❌ Recordings directory not found: {recordings_path}")
        return
    
    # Count source types
    source_type_counts = Counter()
    total_files = 0
    error_files = 0
    
    print(f"🔍 Analyzing recordings in: {recordings_path}")
    print("=" * 60)
    
    # Process all JSON files
    for json_file in recordings_path.glob("*.json"):
        total_files += 1
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                source_type = data.get('source_type', 'MISSING')
                source_type_counts[source_type] += 1
                
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            error_files += 1
            if error_files <= 5:  # Show first few errors
                print(f"⚠️  Error reading {json_file.name}: {e}")
    
    # Display results
    print(f"\n📊 Source Type Distribution ({total_files:,} recordings)")
    print("=" * 60)
    
    # Sort by count (descending)
    for source_type, count in source_type_counts.most_common():
        percentage = (count / total_files) * 100 if total_files > 0 else 0
        print(f"{source_type:>10}: {count:>6,} ({percentage:5.1f}%)")
    
    if error_files > 0:
        print(f"\n⚠️  {error_files} files had errors")
    
    print("\n" + "=" * 60)
    print(f"📈 Total recordings analyzed: {total_files:,}")
    
    # Show improvement potential for UNKNOWN recordings
    unknown_count = source_type_counts.get('UNKNOWN', 0)
    if unknown_count > 0:
        print(f"🎯 UNKNOWN recordings to potentially improve: {unknown_count:,}")
        improvement_potential = (unknown_count / total_files) * 100 if total_files > 0 else 0
        print(f"🎯 Improvement potential: {improvement_potential:.1f}% of total")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze source types in recording JSON files')
    parser.add_argument('--dir', default='stage02-generated-data/recordings',
                       help='Directory containing recording JSON files')
    
    args = parser.parse_args()
    
    analyze_source_types(args.dir)

if __name__ == "__main__":
    main()