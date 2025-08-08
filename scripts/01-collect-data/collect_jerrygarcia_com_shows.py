#!/usr/bin/env python3
"""
Complete Grateful Dead Show Collection Script

This script collects comprehensive show data from jerrygarcia.com, building complete JSON objects
for each show including setlists, band lineups, venue information, and supporting acts.

Features:
- Page range collection (e.g., pages 30-40)
- Individual page processing with complete show details
- Resilient parsing with graceful failure handling
- Venue/location parsing (city, state extraction)
- Configurable delays for respectful crawling
- Progress tracking and resume capability

Usage:
    # Collect shows from specific page range
    python scripts/01-collect-data/collect_complete_shows.py --start-page 30 --end-page 40 --delay 3.0
    
    # Process single page with all show details
    python scripts/01-collect-data/collect_complete_shows.py --start-page 50 --max-pages 1 --delay 2.0
    
    # Resume interrupted collection
    python scripts/01-collect-data/collect_complete_shows.py --resume --delay 2.0
"""

import json
import os
import sys
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import argparse
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Add shared module to path
sys.path.append(str(Path(__file__).parent.parent))


class CompleteShowCollector:
    """
    Collector for complete Grateful Dead show data with detailed parsing.
    """
    
    def __init__(self, output_dir: str = "stage01-collected-data/jerrygarcia", 
                 delay: float = 2.0, force_overwrite: bool = False):
        """Initialize the collector."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DeadShow-CompleteCollector/1.0 (Educational Research)'
        })
        
        self.base_url = "https://jerrygarcia.com"
        self.shows_url = "https://jerrygarcia.com/shows/?srt=DO&kw=&bid%5B3588%5D=on&sd=&ed=&reg=&stat=&ec=&octy=&cty="
        
        # Rate limiting and performance
        self.delay = delay
        self.last_request = 0
        self.force_overwrite = force_overwrite
        
        # Output directories
        self.output_dir = Path(output_dir)
        self.shows_dir = self.output_dir / "shows"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.shows_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress tracking
        self.progress_file = self.output_dir / "collection_progress.json"
        self.failed_urls_file = self.output_dir / "failed_urls.json"
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'no_setlist': 0,
            'empty_setlist': 0,
            'start_time': time.time()
        }
        
        # Failure tracking
        self.failed_urls = []
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging with file and console handlers."""
        log_file = self.output_dir / "collection.log"
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def record_failed_url(self, url: str, error: str, url_type: str = "unknown"):
        """Record a failed URL for later retry."""
        failure_record = {
            'url': url,
            'error': error,
            'url_type': url_type,  # 'page_listing' or 'show_detail'
            'timestamp': datetime.now().isoformat(),
            'retry_count': 0
        }
        self.failed_urls.append(failure_record)
        
    def save_failed_urls(self):
        """Save failed URLs to file for later retry."""
        if self.failed_urls:
            with open(self.failed_urls_file, 'w') as f:
                json.dump(self.failed_urls, f, indent=2)
            self.logger.info(f"Saved {len(self.failed_urls)} failed URLs to: {self.failed_urls_file}")
    
    def load_failed_urls(self) -> List[Dict]:
        """Load failed URLs from previous runs."""
        if self.failed_urls_file.exists():
            try:
                with open(self.failed_urls_file, 'r') as f:
                    failed_urls = json.load(f)
                self.logger.info(f"Loaded {len(failed_urls)} failed URLs from previous runs")
                return failed_urls
            except Exception as e:
                self.logger.warning(f"Failed to load failed URLs: {e}")
        return []
    
    def rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request
        if elapsed < self.delay:
            sleep_time = self.delay - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self.last_request = time.time()
    
    def fetch_page(self, url: str, url_type: str = "unknown") -> Optional[BeautifulSoup]:
        """Fetch and parse a web page with error handling."""
        self.rate_limit()
        
        try:
            self.logger.debug(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except Exception as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            # Track failed URL with type information
            self.record_failed_url(url, str(e), url_type)
            return None
    
    def parse_venue_location(self, location_text: str) -> Dict[str, Optional[str]]:
        """Parse venue location into city, state, country components."""
        if not location_text:
            return {'city': None, 'state': None, 'country': None}
        
        location_text = location_text.strip()
        
        # Handle various location formats
        # "San Francisco, CA", "Vancouver, British Columbia", "New York, NY", etc.
        parts = [part.strip() for part in location_text.split(',')]
        
        if len(parts) >= 2:
            city = parts[0]
            state_country = parts[1]
            
            # Check if last part looks like a country
            if len(parts) == 3:
                country = parts[2]
                state = state_country
            else:
                # Determine if state_country is US state or international
                us_states = {
                    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
                    'DC'
                }
                
                if state_country in us_states:
                    state = state_country
                    country = 'USA'
                else:
                    # Likely international
                    state = state_country if state_country not in ['Canada', 'UK', 'Germany'] else None
                    country = state_country if state_country in ['Canada', 'UK', 'Germany'] else None
        else:
            # Single part location
            city = location_text
            state = None
            country = None
        
        return {
            'city': city,
            'state': state,
            'country': country
        }
    
    def parse_show_from_listing(self, show_item) -> Optional[Dict]:
        """Parse basic show info from a listing page item."""
        try:
            show_link = show_item.find('a', class_='data-display')
            if not show_link:
                return None
            
            show_url = show_link.get('href', '')
            if not show_url:
                return None
            
            # Extract basic show info
            band_elem = show_item.find('h5', class_='subhead-bn')
            venue_elem = show_item.find('h1', class_='subhead-vn')
            location_elem = show_item.find('h3', class_='subhead-mdy-lg')
            date_elem = show_item.find('h4', class_='subhead-mdy-lg')
            
            # Handle mobile layout
            if not location_elem or not date_elem:
                mobile_elem = show_item.find('h4', class_='subhead-mdy')
                if mobile_elem:
                    mobile_text = mobile_elem.get_text().strip()
                    if '|' in mobile_text:
                        location_text, date_text = mobile_text.split('|', 1)
                        location_text = location_text.strip()
                        date_text = date_text.strip()
                    else:
                        location_text = mobile_text
                        date_text = ""
                else:
                    location_text = ""
                    date_text = ""
            else:
                location_text = location_elem.get_text().strip() if location_elem else ""
                date_text = date_elem.get_text().strip() if date_elem else ""
            
            # Parse venue location
            venue_location = self.parse_venue_location(location_text)
            
            show_data = {
                'url': show_url,
                'show_id': show_url.split('/')[-2] if show_url.split('/') else "",
                'band': band_elem.get_text().strip() if band_elem else "",
                'venue': venue_elem.get_text().strip() if venue_elem else "",
                'location_raw': location_text,
                'city': venue_location['city'],
                'state': venue_location['state'], 
                'country': venue_location['country'],
                'date': date_text,
                # Placeholders for detailed data
                'setlist_status': None,  # Will be 'found', 'empty', or 'missing'
                'setlist': None,
                'lineup_status': None,
                'lineup': None,
                'supporting_acts_status': None,
                'supporting_acts': None,
                'collection_timestamp': datetime.now().isoformat()
            }
            
            return show_data
            
        except Exception as e:
            self.logger.warning(f"Failed to parse show listing item: {e}")
            return None
    
    def fetch_show_details(self, show_data: Dict) -> Dict:
        """Fetch and parse detailed information for a show."""
        show_url = show_data['url']
        
        soup = self.fetch_page(show_url, "show_detail")
        if not soup:
            show_data['setlist_status'] = 'missing'
            show_data['lineup_status'] = 'missing'
            show_data['supporting_acts_status'] = 'missing'
            return show_data
        
        try:
            # Extract setlist
            setlist = self._extract_setlist(soup)
            if setlist is None:
                show_data['setlist_status'] = 'missing'
                show_data['setlist'] = None
            elif len(setlist) == 0:
                show_data['setlist_status'] = 'empty'
                show_data['setlist'] = []
            else:
                show_data['setlist_status'] = 'found'
                show_data['setlist'] = setlist
            
            # Extract lineup
            lineup = self._extract_lineup(soup)
            if lineup is None:
                show_data['lineup_status'] = 'missing'
                show_data['lineup'] = None
            elif len(lineup) == 0:
                show_data['lineup_status'] = 'empty'
                show_data['lineup'] = []
            else:
                show_data['lineup_status'] = 'found'
                show_data['lineup'] = lineup
            
            # Extract supporting acts
            supporting_acts = self._extract_supporting_acts(soup)
            if supporting_acts is None:
                show_data['supporting_acts_status'] = 'missing'
                show_data['supporting_acts'] = None
            elif len(supporting_acts) == 0:
                show_data['supporting_acts_status'] = 'empty'
                show_data['supporting_acts'] = []
            else:
                show_data['supporting_acts_status'] = 'found'
                show_data['supporting_acts'] = supporting_acts
            
            # Update collection timestamp
            show_data['collection_timestamp'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Failed to parse show details for {show_url}: {e}")
            show_data['setlist_status'] = 'error'
            show_data['lineup_status'] = 'error' 
            show_data['supporting_acts_status'] = 'error'
        
        return show_data
    
    def _extract_setlist(self, soup: BeautifulSoup) -> Optional[List[Dict]]:
        """Extract setlist information from show page."""
        try:
            setlist = []
            
            # Find all set sections
            set_sections = soup.find_all('h3', class_='set-title')
            
            if not set_sections:
                return None  # No setlist structure found
            
            for set_section in set_sections:
                set_name = set_section.get_text().strip()
                
                # Find the corresponding song list
                song_list = set_section.find_next('ol', class_='comp-set-list')
                if not song_list:
                    continue
                
                songs = []
                song_items = song_list.find_all('li')
                
                for song_item in song_items:
                    song_data = {}
                    
                    # Check if song has a link
                    song_link = song_item.find('a')
                    if song_link:
                        song_data['name'] = song_link.get_text().strip()
                        song_data['url'] = song_link.get('href', '')
                    else:
                        song_data['name'] = song_item.get_text().strip()
                        song_data['url'] = None
                    
                    # Check for segue notation
                    song_text = song_item.get_text().strip()
                    if song_text.endswith(' > ') or song_text.endswith('>'):
                        song_data['segue_into_next'] = True
                    else:
                        song_data['segue_into_next'] = False
                    
                    # Clean up song name
                    song_data['name'] = song_data['name'].rstrip(' >').rstrip('>')
                    
                    if song_data['name']:  # Only add non-empty songs
                        songs.append(song_data)
                
                if songs:
                    setlist.append({
                        'set_name': set_name,
                        'songs': songs
                    })
            
            return setlist
            
        except Exception as e:
            self.logger.debug(f"Error extracting setlist: {e}")
            return None
    
    def _extract_lineup(self, soup: BeautifulSoup) -> Optional[List[Dict]]:
        """Extract band lineup information from show page."""
        try:
            lineup = []
            
            lineup_list = soup.find('ul', class_='lineup-list')
            if not lineup_list:
                return None
            
            artist_items = lineup_list.find_all('li', class_='artist-info')
            
            for artist_item in artist_items:
                artist_data = {}
                
                # Extract artist name
                name_link = artist_item.find('a', class_='name')
                if name_link:
                    artist_data['name'] = name_link.get_text().strip()
                else:
                    name_bold = artist_item.find('b')
                    if name_bold:
                        artist_data['name'] = name_bold.get_text().strip()
                    else:
                        paragraph = artist_item.find('p')
                        if paragraph:
                            name_text = paragraph.get_text().split('\n')[0].strip()
                            artist_data['name'] = name_text
                
                # Extract instruments
                span_element = artist_item.find('span')
                if span_element:
                    artist_data['instruments'] = span_element.get_text().strip()
                else:
                    paragraph = artist_item.find('p')
                    if paragraph:
                        full_text = paragraph.get_text()
                        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                        if len(lines) > 1:
                            artist_data['instruments'] = lines[1]
                
                # Extract image URL
                img = artist_item.find('img')
                if img:
                    artist_data['image_url'] = img.get('src', '')
                
                if artist_data.get('name'):
                    lineup.append(artist_data)
            
            return lineup
            
        except Exception as e:
            self.logger.debug(f"Error extracting lineup: {e}")
            return None
    
    def _extract_supporting_acts(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """Extract supporting acts from show page."""
        try:
            supporting_acts = []
            
            supporting_section = soup.find('ul', class_='supporting-acts')
            if not supporting_section:
                return None
            
            act_items = supporting_section.find_all('li')
            for act_item in act_items:
                act_name = act_item.get_text().strip()
                if act_name:
                    supporting_acts.append(act_name)
            
            return supporting_acts
            
        except Exception as e:
            self.logger.debug(f"Error extracting supporting acts: {e}")
            return None
    
    def get_total_pages(self, soup: BeautifulSoup) -> int:
        """Extract total number of pages from pagination."""
        try:
            pagination_input = soup.find('input', {'data-total': True})
            if pagination_input:
                return int(pagination_input.get('data-total', 1))
            
            total_link = soup.find('li', class_='total')
            if total_link:
                total_text = total_link.get_text().strip()
                if total_text.isdigit():
                    return int(total_text)
            
            return 1
        except (ValueError, AttributeError):
            return 1
    
    def collect_shows_from_page(self, page_num: int) -> List[Dict]:
        """Collect all shows from a single page with complete details."""
        self.logger.info(f"Processing page {page_num}")
        
        # Construct page URL
        if page_num == 1:
            page_url = self.shows_url
        else:
            page_url = f"{self.base_url}/shows/page/{page_num}/?bid%5B3588%5D=on&kw&sd&ed&reg&stat&cty&ec&octy&srt=DO"
        
        # Fetch the listing page
        soup = self.fetch_page(page_url, "page_listing")
        if not soup:
            self.logger.error(f"Failed to fetch page {page_num}")
            return []
        
        # Parse show listings
        show_items = soup.find_all('li', class_='show-info')
        self.logger.info(f"Found {len(show_items)} shows on page {page_num}")
        
        complete_shows = []
        
        for i, show_item in enumerate(show_items, 1):
            try:
                # Parse basic show info from listing
                show_data = self.parse_show_from_listing(show_item)
                if not show_data:
                    self.logger.warning(f"Failed to parse show {i} on page {page_num}")
                    self.stats['failed'] += 1
                    continue
                
                show_id = show_data['show_id']
                
                # Check if already exists (unless force overwrite)
                show_file = self.shows_dir / f"{show_id}.json"
                if show_file.exists() and not self.force_overwrite:
                    self.logger.debug(f"Skipping existing show: {show_id}")
                    # Load existing data to include in results
                    try:
                        with open(show_file, 'r') as f:
                            existing_show = json.load(f)
                        complete_shows.append(existing_show)
                        self.stats['successful'] += 1
                        continue
                    except Exception as e:
                        self.logger.warning(f"Failed to load existing show {show_id}: {e}")
                
                self.logger.info(f"Collecting details for show {i}/{len(show_items)}: {show_data['venue']} ({show_data['date']})")
                
                # Fetch detailed information
                complete_show = self.fetch_show_details(show_data)
                
                # Update statistics
                self.stats['total_processed'] += 1
                if complete_show['setlist_status'] == 'found':
                    self.stats['successful'] += 1
                elif complete_show['setlist_status'] == 'empty':
                    self.stats['empty_setlist'] += 1
                elif complete_show['setlist_status'] in ['missing', 'error']:
                    self.stats['no_setlist'] += 1
                else:
                    self.stats['failed'] += 1
                
                # Save individual show
                with open(show_file, 'w') as f:
                    json.dump(complete_show, f, indent=2)
                
                complete_shows.append(complete_show)
                
                # Log progress
                if i % 5 == 0:
                    elapsed = time.time() - self.stats['start_time']
                    rate = self.stats['total_processed'] / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Progress: {i}/{len(show_items)} shows processed. Rate: {rate:.1f}/min")
                
            except Exception as e:
                self.logger.error(f"Error processing show {i} on page {page_num}: {e}")
                self.stats['failed'] += 1
                continue
        
        return complete_shows
    
    def collect_page_range(self, start_page: int, end_page: int) -> List[Dict]:
        """Collect complete shows from a range of pages."""
        self.logger.info(f"Starting collection from pages {start_page} to {end_page}")
        
        all_shows = []
        
        for page_num in range(start_page, end_page + 1):
            try:
                page_shows = self.collect_shows_from_page(page_num)
                all_shows.extend(page_shows)
                
                self.logger.info(f"Page {page_num} complete: {len(page_shows)} shows collected")
                
                # Save progress
                self.save_progress(page_num, start_page, end_page)
                
            except Exception as e:
                self.logger.error(f"Failed to process page {page_num}: {e}")
                continue
        
        # Save failed URLs for retry
        self.save_failed_urls()
        
        # Save complete collection summary
        self.save_collection_summary(all_shows, start_page, end_page)
        
        return all_shows
    
    def save_progress(self, current_page: int, start_page: int, end_page: int):
        """Save collection progress."""
        progress_data = {
            'current_page': current_page,
            'start_page': start_page,
            'end_page': end_page,
            'stats': self.stats,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    
    def save_collection_summary(self, shows: List[Dict], start_page: int, end_page: int):
        """Save collection summary."""
        summary_file = self.output_dir / f"collection_summary_pages_{start_page}_to_{end_page}.json"
        
        summary = {
            'collection_info': {
                'start_page': start_page,
                'end_page': end_page,
                'total_pages': end_page - start_page + 1,
                'collection_timestamp': datetime.now().isoformat(),
                'delay_seconds': self.delay
            },
            'statistics': self.stats,
            'shows': shows
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Collection summary saved to: {summary_file}")
    
    def retry_failed_urls(self, max_retries: int = 3) -> List[Dict]:
        """Retry previously failed URLs."""
        failed_urls = self.load_failed_urls()
        if not failed_urls:
            self.logger.info("No failed URLs to retry")
            return []
        
        self.logger.info(f"Starting retry of {len(failed_urls)} failed URLs (max {max_retries} attempts each)")
        
        completed_shows = []
        remaining_failures = []
        
        for failure_record in failed_urls:
            url = failure_record['url']
            url_type = failure_record['url_type']
            retry_count = failure_record.get('retry_count', 0)
            
            # Skip if already exceeded max retries
            if retry_count >= max_retries:
                self.logger.debug(f"Skipping {url} - exceeded max retries ({retry_count})")
                remaining_failures.append(failure_record)
                continue
            
            self.logger.info(f"Retrying {url_type}: {url} (attempt {retry_count + 1}/{max_retries})")
            
            try:
                if url_type == "show_detail":
                    # Retry show detail fetch
                    show_id = url.split('/')[-2] if url.split('/') else "unknown"
                    show_file = self.shows_dir / f"{show_id}.json"
                    
                    if show_file.exists() and not self.force_overwrite:
                        self.logger.debug(f"Show {show_id} already exists, skipping retry")
                        continue
                    
                    # Create basic show data structure for retry
                    show_data = {
                        'url': url,
                        'show_id': show_id,
                        'band': 'Grateful Dead',  # Default assumption
                        'venue': 'Unknown',
                        'location_raw': 'Unknown',
                        'city': None,
                        'state': None,
                        'country': None,
                        'date': 'Unknown',
                        'setlist_status': None,
                        'setlist': None,
                        'lineup_status': None,
                        'lineup': None,
                        'supporting_acts_status': None,
                        'supporting_acts': None,
                        'collection_timestamp': datetime.now().isoformat()
                    }
                    
                    # Attempt to fetch details
                    complete_show = self.fetch_show_details(show_data)
                    
                    if complete_show['setlist_status'] not in ['missing', 'error']:
                        # Success - save the show
                        with open(show_file, 'w') as f:
                            json.dump(complete_show, f, indent=2)
                        completed_shows.append(complete_show)
                        self.logger.info(f"✅ Successfully retried show: {show_id}")
                    else:
                        # Still failed - increment retry count
                        failure_record['retry_count'] = retry_count + 1
                        failure_record['last_retry'] = datetime.now().isoformat()
                        remaining_failures.append(failure_record)
                        self.logger.warning(f"❌ Retry failed for show: {show_id}")
                
                elif url_type == "page_listing":
                    # For page listing failures, we'd need more complex logic
                    # For now, just increment retry count
                    failure_record['retry_count'] = retry_count + 1
                    failure_record['last_retry'] = datetime.now().isoformat()
                    remaining_failures.append(failure_record)
                    self.logger.warning(f"❌ Page listing retry not yet implemented: {url}")
                
                else:
                    # Unknown URL type
                    self.logger.warning(f"Unknown URL type for retry: {url_type}")
                    remaining_failures.append(failure_record)
                    
            except Exception as e:
                self.logger.error(f"Error during retry of {url}: {e}")
                failure_record['retry_count'] = retry_count + 1
                failure_record['last_retry'] = datetime.now().isoformat()
                failure_record['last_error'] = str(e)
                remaining_failures.append(failure_record)
        
        # Update failed URLs file with remaining failures
        self.failed_urls = remaining_failures
        self.save_failed_urls()
        
        self.logger.info(f"Retry complete: {len(completed_shows)} recovered, {len(remaining_failures)} still failed")
        
        return completed_shows


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Collect complete Grateful Dead show data from jerrygarcia.com')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Starting page number')
    parser.add_argument('--end-page', type=int,
                       help='Ending page number (if not specified, processes only start-page)')
    parser.add_argument('--max-pages', type=int,
                       help='Maximum number of pages to process from start-page')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between requests in seconds')
    parser.add_argument('--output-dir', default='stage01-collected-data/jerrygarcia',
                       help='Output directory for collected shows')
    parser.add_argument('--force', action='store_true',
                       help='Force overwrite existing show files')
    parser.add_argument('--retry-failed', action='store_true',
                       help='Retry previously failed URLs')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='Maximum retry attempts per failed URL')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Calculate end page
    if args.end_page:
        end_page = args.end_page
    elif args.max_pages:
        end_page = args.start_page + args.max_pages - 1
    else:
        end_page = args.start_page  # Just process one page
    
    collector = CompleteShowCollector(
        output_dir=args.output_dir,
        delay=args.delay,
        force_overwrite=args.force
    )
    
    try:
        if args.retry_failed:
            # Retry failed URLs mode
            shows = collector.retry_failed_urls(max_retries=args.max_retries)
            
            print(f"\n✅ Retry complete!")
            print(f"📊 Results:")
            print(f"  Recovered shows: {len(shows)}")
            print(f"  Still failed: {len(collector.failed_urls)}")
            print(f"📁 Output: {args.output_dir}")
            
            return 0
        else:
            # Normal collection mode
            shows = collector.collect_page_range(args.start_page, end_page)
        
            # Print final statistics
            stats = collector.stats
            elapsed = time.time() - stats['start_time']
            
            print(f"\n✅ Collection complete!")
            print(f"📊 Statistics:")
            print(f"  Total processed: {stats['total_processed']}")
            print(f"  Successful (with setlist): {stats['successful']}")
            print(f"  Empty setlist: {stats['empty_setlist']}")
            print(f"  No setlist found: {stats['no_setlist']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Failed URLs logged: {len(collector.failed_urls)}")
            print(f"  Time elapsed: {elapsed/60:.1f} minutes")
            print(f"  Rate: {stats['total_processed']/elapsed*60:.1f} shows/hour")
            print(f"📁 Output: {args.output_dir}")
            if len(collector.failed_urls) > 0:
                print(f"🔄 To retry failed URLs, run with: --retry-failed")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ Collection interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())