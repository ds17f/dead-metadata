#!/usr/bin/env python3
"""
Test Source Type Improvements

Tests how many UNKNOWN recordings could be improved by our enhanced
source type detection logic without actually regenerating files.
"""

import json
import sys
from pathlib import Path
from collections import Counter

# Add shared module to path
sys.path.append('scripts')
from scripts.shared.recording_utils import improve_source_type_detection

class TestRecording:
    """Minimal recording object for testing."""
    def __init__(self, data):
        self.identifier = data['identifier']
        self.raw_metadata = data
    
    @property
    def title(self): return self.raw_metadata.get('title', '')
    @property 
    def description(self): return self.raw_metadata.get('description', '')
    @property
    def source(self): return self.raw_metadata.get('source', '')

def test_improvements(recordings_dir: str = "stage02-generated-data/recordings", max_files: int = None):
    """Test how many UNKNOWN recordings could be improved."""
    
    recordings_path = Path(recordings_dir)
    if not recordings_path.exists():
        print(f"❌ Recordings directory not found: {recordings_path}")
        return
    
    # Counters
    total_tested = 0
    unknown_tested = 0
    improvements = Counter()
    sample_improvements = []
    
    print(f"🧪 Testing source type improvements...")
    if max_files:
        print(f"📝 Testing first {max_files:,} files only")
    print("=" * 70)
    
    # Test files
    json_files = list(recordings_path.glob("*.json"))
    if max_files:
        json_files = json_files[:max_files]
    
    for json_file in json_files:
        total_tested += 1
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            current_type = data.get('source_type', 'MISSING')
            
            # Only test UNKNOWN recordings
            if current_type == 'UNKNOWN':
                unknown_tested += 1
                recording = TestRecording(data)
                new_type = improve_source_type_detection(recording)
                
                if new_type != 'UNKNOWN':
                    improvements[new_type] += 1
                    
                    # Collect samples for display
                    if len(sample_improvements) < 10:
                        sample_improvements.append({
                            'identifier': data['identifier'][:50],
                            'old_type': current_type,
                            'new_type': new_type,
                            'source': data.get('source', '')[:60]
                        })
                
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            continue
    
    # Display results
    print(f"\n📊 Test Results ({total_tested:,} files tested)")
    print("=" * 70)
    print(f"🔍 UNKNOWN recordings tested: {unknown_tested:,}")
    
    total_improvements = sum(improvements.values())
    if total_improvements > 0:
        improvement_rate = (total_improvements / unknown_tested) * 100 if unknown_tested > 0 else 0
        print(f"✅ Could be improved: {total_improvements:,} ({improvement_rate:.1f}%)")
        print(f"\n🎯 Improvement breakdown:")
        for new_type, count in improvements.most_common():
            percentage = (count / total_improvements) * 100 if total_improvements > 0 else 0
            print(f"  UNKNOWN -> {new_type}: {count:,} ({percentage:.1f}%)")
        
        print(f"\n📝 Sample improvements:")
        for sample in sample_improvements:
            print(f"  {sample['identifier']:<50} | {sample['old_type']} -> {sample['new_type']}")
    else:
        print("❌ No improvements found")
    
    if max_files and max_files < len(list(recordings_path.glob("*.json"))):
        total_files = len(list(recordings_path.glob("*.json")))
        estimated_total = int((total_improvements / max_files) * total_files)
        print(f"\n🔮 Estimated total improvements: ~{estimated_total:,}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test source type improvements')
    parser.add_argument('--dir', default='stage02-generated-data/recordings',
                       help='Directory containing recording JSON files')
    parser.add_argument('--max-files', type=int, default=1000,
                       help='Maximum number of files to test (default: 1000)')
    parser.add_argument('--all', action='store_true',
                       help='Test all files (may take a while)')
    
    args = parser.parse_args()
    
    max_files = None if args.all else args.max_files
    test_improvements(args.dir, max_files)

if __name__ == "__main__":
    main()