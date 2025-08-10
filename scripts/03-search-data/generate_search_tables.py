#!/usr/bin/env python3
"""
Search Tables Generation Script

Processes show files into denormalized search tables for fast mobile app searches.
Uses hardcoded aliases based on Grateful Dead knowledge rather than data analysis.

Usage:
    python scripts/03-search-data/generate_search_tables.py --verbose

This is the production script - part of the automated pipeline.
"""

import argparse
import json
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path
import re


def load_show_files(shows_dir):
    """Load all show JSON files from the shows directory."""
    shows = []
    shows_path = Path(shows_dir)
    
    if not shows_path.exists():
        print(f"Error: Shows directory not found: {shows_dir}")
        return []
    
    for show_file in shows_path.glob("*.json"):
        try:
            with open(show_file, 'r', encoding='utf-8') as f:
                show_data = json.load(f)
                shows.append(show_data)
        except Exception as e:
            print(f"Warning: Could not load {show_file}: {e}")
    
    return shows


def normalize_search_key(text):
    """Convert text to normalized search key."""
    if not text:
        return ""
    
    # Convert to lowercase
    normalized = text.lower()
    
    # Remove punctuation except hyphens and apostrophes
    normalized = re.sub(r"[^\w\s\-']", '', normalized)
    
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Convert spaces to hyphens for keys
    normalized = normalized.replace(' ', '-')
    
    return normalized


def get_song_aliases():
    """Return hardcoded song aliases based on Grateful Dead knowledge."""
    return {
        # Common abbreviations and alternate names
        "dark-star": ["dark-star", "darkstar", "ds"],
        "playing-in-the-band": ["playing-in-the-band", "pitb", "playing"],
        "drums": ["drums", "drum-solo", "percussion"],
        "space": ["space", "lead-guitar-jam", "guitar-solo"],
        "not-fade-away": ["not-fade-away", "nfa"],
        "the-other-one": ["the-other-one", "too"],
        "uncle-johns-band": ["uncle-johns-band", "ujb"],
        "china-cat-sunflower": ["china-cat-sunflower", "china-cat"],
        "i-know-you-rider": ["i-know-you-rider", "rider"],
        "eyes-of-the-world": ["eyes-of-the-world", "eyes"],
        "estimated-prophet": ["estimated-prophet", "estimated"],
        "they-love-each-other": ["they-love-each-other", "tleo"],
        "wharf-rat": ["wharf-rat", "wharf"],
        "truckin": ["truckin", "trucking"],
        "ripple": ["ripple"],
        "friend-of-the-devil": ["friend-of-the-devil", "fotd"],
        "casey-jones": ["casey-jones", "casey"],
        "sugar-magnolia": ["sugar-magnolia", "sugar-mag"],
        "fire-on-the-mountain": ["fire-on-the-mountain", "fotm", "fire"],
        "scarlet-begonias": ["scarlet-begonias", "scarlet"],
        "saint-stephen": ["saint-stephen", "st-stephen"],
        "morning-dew": ["morning-dew", "dew"],
        "jack-straw": ["jack-straw"],
        "bertha": ["bertha"],
        "good-lovin": ["good-lovin", "good-loving"],
        "turn-on-your-love-light": ["turn-on-your-love-light", "love-light"],
        "going-down-the-road-feeling-bad": ["going-down-the-road-feeling-bad", "goin-down-the-road", "gdtrfb"],
        "johnny-b-goode": ["johnny-b-goode", "johnny-be-good"],
        "promised-land": ["promised-land"],
        "tennessee-jed": ["tennessee-jed", "jed"],
        "el-paso": ["el-paso"],
        "big-river": ["big-river"],
        "deal": ["deal"],
        "loser": ["loser"],
        "black-peter": ["black-peter"],
        "he-s-gone": ["he-s-gone", "hes-gone"],
        "stella-blue": ["stella-blue", "stella"],
        "ship-of-fools": ["ship-of-fools"],
        "touch-of-grey": ["touch-of-grey", "touch-of-gray"],
        "hell-in-a-bucket": ["hell-in-a-bucket"],
        "throwing-stones": ["throwing-stones"],
        "shakedown-street": ["shakedown-street", "shakedown"]
    }


def get_venue_aliases():
    """Return hardcoded venue aliases based on Grateful Dead knowledge."""
    return {
        "fillmore-auditorium": ["fillmore", "fillmore-auditorium", "sf-fillmore"],
        "fillmore-west": ["fillmore-west", "fillmore", "west-fillmore"],
        "fillmore-east": ["fillmore-east", "east-fillmore", "fe"],
        "winterland-arena": ["winterland", "winterland-arena"],
        "avalon-ballroom": ["avalon", "avalon-ballroom"],
        "carousel-ballroom": ["carousel", "carousel-ballroom"],
        "madison-square-garden": ["msg", "madison-square-garden", "garden"],
        "red-rocks-amphitheatre": ["red-rocks", "red-rocks-amphitheatre"],
        "barton-hall-cornell-university": ["barton-hall", "cornell", "cornell-university"],
        "greek-theatre": ["greek", "greek-theatre", "greek-theater"],
        "oakland-coliseum-arena": ["oakland", "oakland-coliseum"],
        "shoreline-amphitheatre": ["shoreline"],
        "hampton-coliseum": ["hampton"],
        "radio-city-music-hall": ["radio-city"],
        "boston-garden": ["boston-garden"],
        "philadelphia-spectrum": ["spectrum", "philadelphia-spectrum"],
        "capital-centre": ["capital-centre", "cap-centre"],
        "richfield-coliseum": ["richfield"],
        "pine-knob-music-theatre": ["pine-knob"],
        "merriweather-post-pavilion": ["merriweather"],
        "saratoga-performing-arts-center": ["saratoga", "spac"]
    }


def get_member_aliases():
    """Return hardcoded member aliases based on Grateful Dead knowledge."""
    return {
        "jerry-garcia": ["jerry", "garcia", "jerry-garcia", "captain-trips"],
        "bob-weir": ["bob", "weir", "bobby", "bob-weir"],
        "phil-lesh": ["phil", "lesh", "phil-lesh"],
        "bill-kreutzmann": ["billy", "kreutzmann", "bill-kreutzmann"],
        "mickey-hart": ["mickey", "hart", "mickey-hart"],
        "ron-pigpen-mckernan": ["pigpen", "pig", "ron-mckernan", "mckernan"],
        "keith-godchaux": ["keith", "godchaux", "keith-godchaux"],
        "donna-jean-godchaux": ["donna", "donna-jean", "donna-godchaux"],
        "brent-mydland": ["brent", "mydland", "brent-mydland"],
        "vince-welnick": ["vince", "welnick", "vince-welnick"],
        "bruce-hornsby": ["bruce", "hornsby", "bruce-hornsby"],
        "tom-constanten": ["tc", "tom-constanten", "constanten"],
        "john-perry-barlow": ["barlow", "john-barlow"],
        "robert-hunter": ["hunter", "robert-hunter"]
    }


def generate_songs_table(shows, verbose=False):
    """Generate the songs search table."""
    if verbose:
        print("🎵 Generating songs table...")
    
    song_aliases = get_song_aliases()
    songs_table = {}
    
    # Track song performance data
    song_performances = defaultdict(list)
    song_stats = defaultdict(lambda: {
        'first_performance': None,
        'last_performance': None,
        'total_performances': 0
    })
    
    for show in shows:
        if not show.get('setlist'):
            continue
            
        show_id = show.get('show_id')
        date = show.get('date')
        venue = show.get('venue', '')
        location = f"{show.get('city', '')}, {show.get('state', '')}, {show.get('country', '')}"
        location = location.strip(' ,')
        
        rating = show.get('avg_rating', 0)
        raw_rating = show.get('raw_rating', 0)
        
        for set_idx, set_info in enumerate(show['setlist']):
            set_name = set_info.get('set_name', f'Set {set_idx + 1}')
            
            if not set_info.get('songs'):
                continue
                
            for pos, song in enumerate(set_info['songs']):
                song_name = song.get('name', '').strip()
                if not song_name:
                    continue
                
                song_key = normalize_search_key(song_name)
                segue_into_next = song.get('segue_into_next', False)
                
                # Track performance
                performance = {
                    'show_id': show_id,
                    'date': date,
                    'venue': venue,
                    'location': location,
                    'set': set_name,
                    'position': pos + 1,
                    'segue_into_next': segue_into_next,
                    'rating': rating,
                    'raw_rating': raw_rating
                }
                
                song_performances[song_key].append(performance)
                
                # Update stats
                stats = song_stats[song_key]
                stats['total_performances'] += 1
                
                if stats['first_performance'] is None or date < stats['first_performance']:
                    stats['first_performance'] = date
                if stats['last_performance'] is None or date > stats['last_performance']:
                    stats['last_performance'] = date
    
    # Build final songs table
    for song_key, performances in song_performances.items():
        # Find the canonical song name (most common version)
        name_counter = Counter()
        for perf in performances:
            # Extract original name from the show data
            for show in shows:
                if show.get('show_id') == perf['show_id'] and show.get('setlist'):
                    for set_info in show['setlist']:
                        for song in set_info.get('songs', []):
                            if normalize_search_key(song.get('name', '')) == song_key:
                                name_counter[song.get('name', '')] += 1
                                break
        
        canonical_name = name_counter.most_common(1)[0][0] if name_counter else song_key
        stats = song_stats[song_key]
        
        # Get aliases (use predefined or generate basic ones)
        aliases = song_aliases.get(song_key, [song_key])
        
        # Sort performances by date
        performances.sort(key=lambda x: x['date'])
        
        songs_table[song_key] = {
            'name': canonical_name,
            'shows': performances,
            'total_performances': stats['total_performances'],
            'first_performance': stats['first_performance'],
            'last_performance': stats['last_performance'],
            'aliases': aliases
        }
    
    if verbose:
        print(f"   • {len(songs_table)} songs indexed")
        print(f"   • {sum(len(data['shows']) for data in songs_table.values())} total performances")
    
    return songs_table


def generate_venues_table(shows, verbose=False):
    """Generate the venues search table."""
    if verbose:
        print("🏛️ Generating venues table...")
    
    venue_aliases = get_venue_aliases()
    venues_table = {}
    
    # Track venue show data
    venue_shows = defaultdict(list)
    venue_info = {}
    
    for show in shows:
        venue_name = show.get('venue', '').strip()
        if not venue_name:
            continue
            
        venue_key = normalize_search_key(venue_name)
        show_id = show.get('show_id')
        date = show.get('date')
        
        city = show.get('city', '')
        state = show.get('state', '')
        country = show.get('country', '')
        location_raw = show.get('location_raw', '')
        
        rating = show.get('avg_rating', 0)
        raw_rating = show.get('raw_rating', 0)
        recording_count = show.get('recording_count', 0)
        
        # Store venue info
        if venue_key not in venue_info:
            venue_info[venue_key] = {
                'name': venue_name,
                'city': city,
                'state': state,
                'country': country,
                'location_raw': location_raw
            }
        
        # Track show
        show_data = {
            'show_id': show_id,
            'date': date,
            'rating': rating,
            'raw_rating': raw_rating,
            'recording_count': recording_count
        }
        
        venue_shows[venue_key].append(show_data)
    
    # Build final venues table
    for venue_key, shows_list in venue_shows.items():
        info = venue_info[venue_key]
        
        # Sort shows by date
        shows_list.sort(key=lambda x: x['date'])
        
        # Get aliases
        aliases = venue_aliases.get(venue_key, [venue_key])
        
        location = f"{info['city']}, {info['state']}, {info['country']}".strip(' ,')
        
        venues_table[venue_key] = {
            'name': info['name'],
            'location': location,
            'city': info['city'],
            'state': info['state'],
            'country': info['country'],
            'shows': shows_list,
            'total_shows': len(shows_list),
            'first_show': shows_list[0]['date'] if shows_list else None,
            'last_show': shows_list[-1]['date'] if shows_list else None,
            'aliases': aliases
        }
    
    if verbose:
        print(f"   • {len(venues_table)} venues indexed")
        print(f"   • {sum(len(data['shows']) for data in venues_table.values())} total shows")
    
    return venues_table


def generate_members_table(shows, verbose=False):
    """Generate the band members search table."""
    if verbose:
        print("🎸 Generating members table...")
    
    member_aliases = get_member_aliases()
    members_table = {}
    
    # Track member show data
    member_shows = defaultdict(list)
    member_instruments = defaultdict(set)
    
    for show in shows:
        if not show.get('lineup'):
            continue
            
        show_id = show.get('show_id')
        date = show.get('date')
        venue = show.get('venue', '')
        rating = show.get('avg_rating', 0)
        
        for member in show['lineup']:
            name = member.get('name', '').strip()
            if not name:
                continue
                
            member_key = normalize_search_key(name)
            instruments = member.get('instruments', '')
            
            # Track instruments
            if instruments:
                instruments_list = [inst.strip() for inst in instruments.split(',')]
                for instrument in instruments_list:
                    if instrument:
                        member_instruments[member_key].add(instrument)
            
            # Track show
            show_data = {
                'show_id': show_id,
                'date': date,
                'venue': venue,
                'instruments': instruments,
                'rating': rating
            }
            
            member_shows[member_key].append(show_data)
    
    # Build final members table
    for member_key, shows_list in member_shows.items():
        # Find canonical name
        name_counter = Counter()
        for show_data in shows_list:
            for show in shows:
                if show.get('show_id') == show_data['show_id'] and show.get('lineup'):
                    for member in show['lineup']:
                        if normalize_search_key(member.get('name', '')) == member_key:
                            name_counter[member.get('name', '')] += 1
                            break
        
        canonical_name = name_counter.most_common(1)[0][0] if name_counter else member_key
        
        # Sort shows by date
        shows_list.sort(key=lambda x: x['date'])
        
        # Get aliases
        aliases = member_aliases.get(member_key, [member_key])
        
        # Get primary instruments
        instruments_list = list(member_instruments[member_key])
        
        members_table[member_key] = {
            'name': canonical_name,
            'instruments': instruments_list,
            'shows': shows_list,
            'total_shows': len(shows_list),
            'first_show': shows_list[0]['date'] if shows_list else None,
            'last_show': shows_list[-1]['date'] if shows_list else None,
            'primary_instruments': instruments_list,
            'aliases': aliases
        }
    
    if verbose:
        print(f"   • {len(members_table)} members indexed")
        print(f"   • {sum(len(data['shows']) for data in members_table.values())} total appearances")
    
    return members_table


def generate_shows_index(shows, verbose=False):
    """Generate the shows search index."""
    if verbose:
        print("📅 Generating shows index...")
    
    shows_index = {}
    
    for show in shows:
        show_id = show.get('show_id')
        if not show_id:
            continue
            
        date = show.get('date', '')
        venue = show.get('venue', '')
        city = show.get('city', '')
        state = show.get('state', '')
        country = show.get('country', '')
        
        location = f"{city}, {state}, {country}".strip(' ,')
        
        # Parse date components
        year = month = day = None
        if date:
            try:
                parts = date.split('-')
                if len(parts) >= 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
            except (ValueError, IndexError):
                pass
        
        rating = show.get('avg_rating', 0)
        raw_rating = show.get('raw_rating', 0)
        recording_count = show.get('recording_count', 0)
        
        # Count songs
        song_count = 0
        has_setlist = bool(show.get('setlist'))
        if has_setlist:
            for set_info in show['setlist']:
                song_count += len(set_info.get('songs', []))
        
        # Create search text for full-text search
        search_terms = []
        if year:
            search_terms.append(str(year))
        if month:
            month_names = ['', 'january', 'february', 'march', 'april', 'may', 'june',
                          'july', 'august', 'september', 'october', 'november', 'december']
            if 1 <= month <= 12:
                search_terms.append(month_names[month])
        if venue:
            search_terms.extend(venue.lower().split())
        if city:
            search_terms.append(city.lower())
        if state:
            search_terms.append(state.lower())
        if country:
            search_terms.append(country.lower())
        search_terms.append('grateful dead')
        
        shows_index[show_id] = {
            'show_id': show_id,
            'date': date,
            'venue': venue,
            'location': location,
            'city': city,
            'state': state,
            'country': country,
            'band': 'Grateful Dead',
            'year': year,
            'month': month,
            'day': day,
            'rating': rating,
            'raw_rating': raw_rating,
            'recording_count': recording_count,
            'song_count': song_count,
            'has_setlist': has_setlist,
            'collections': show.get('collections', []),  # Add collection membership
            'search_text': ' '.join(search_terms)
        }
    
    if verbose:
        print(f"   • {len(shows_index)} shows indexed")
    
    return shows_index


def main():
    parser = argparse.ArgumentParser(description="Generate search tables for mobile app")
    parser.add_argument('--shows-dir', 
                       default='stage02-generated-data/shows',
                       help='Directory containing show JSON files')
    parser.add_argument('--output-dir', 
                       default='stage03-search-data',
                       help='Output directory for search tables')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        print("🔍 Starting search tables generation...")
        print(f"📁 Loading shows from: {args.shows_dir}")
    
    # Load all show files
    shows = load_show_files(args.shows_dir)
    
    if not shows:
        print("Error: No show files found!")
        sys.exit(1)
    
    if args.verbose:
        print(f"📊 Loaded {len(shows)} shows")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate search tables
    songs_table = generate_songs_table(shows, args.verbose)
    venues_table = generate_venues_table(shows, args.verbose)
    members_table = generate_members_table(shows, args.verbose)
    shows_index = generate_shows_index(shows, args.verbose)
    
    # Save search tables
    tables = {
        'songs.json': songs_table,
        'venues.json': venues_table,
        'members.json': members_table,
        'shows_index.json': shows_index
    }
    
    total_size = 0
    for filename, table_data in tables.items():
        output_path = output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(table_data, f, indent=2, ensure_ascii=False)
        
        file_size = output_path.stat().st_size
        total_size += file_size
        
        if args.verbose:
            print(f"💾 Saved {filename}: {file_size / 1024 / 1024:.1f}MB")
    
    if args.verbose:
        print(f"✅ Search tables generation complete!")
        print(f"📈 Total output size: {total_size / 1024 / 1024:.1f}MB")
        print(f"📂 Files saved to: {output_dir}")


if __name__ == "__main__":
    main()