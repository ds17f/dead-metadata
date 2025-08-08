#!/usr/bin/env python3
"""
Jerry Garcia Show Database Collection Script

This script collects comprehensive Grateful Dead show data from jerrygarcia.com,
which provides a definitive list of shows that can be used to map recordings
to actual performances.

Usage:
    python scripts/01-collect-data/collect_jerrygarcia_shows.py --test
    python scripts/01-collect-data/collect_jerrygarcia_shows.py --output-dir stage01-collected-data/jerrygarcia
"""

import requests
import time
from bs4 import BeautifulSoup
from pathlib import Path
import json
import argparse
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import sys

class JerryGarciaShowCollector:
    """
    Collector for Grateful Dead show data from jerrygarcia.com
    """
    
    def __init__(self, output_dir: str = "stage01-collected-data/jerrygarcia", 
                 delay: float = 1.0):
        """Initialize the collector."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DeadShow-Collector/1.0 (Educational Research)'
        })
        
        self.base_url = "https://jerrygarcia.com"
        self.shows_url = "https://jerrygarcia.com/shows/?srt=DO&kw=&bid%5B3588%5D=on&sd=&ed=&reg=&stat=&ec=&octy=&cty="
        
        # Rate limiting
        self.delay = delay
        self.last_request = 0
        
        # Output directory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging with file and console handlers."""
        log_file = self.output_dir / "collection.log"
        
        # Create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
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
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request = time.time()
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page."""
        self.rate_limit()
        
        try:
            self.logger.debug(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except Exception as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def test_access(self) -> bool:
        """Test access to the Jerry Garcia show database."""
        self.logger.info("Testing access to Jerry Garcia show database...")
        
        soup = self.fetch_page(self.shows_url)
        if not soup:
            self.logger.error("❌ Failed to access Jerry Garcia show database")
            return False
        
        # Look for show listings
        self.logger.info("✅ Successfully accessed Jerry Garcia show database")
        
        # Basic page analysis
        title = soup.find('title')
        if title:
            self.logger.info(f"Page title: {title.get_text().strip()}")
        
        # Look for show data structures
        show_elements = soup.find_all('tr') # assuming table rows contain shows
        self.logger.info(f"Found {len(show_elements)} table rows on the page")
        
        # Look for links that might be individual show pages
        links = soup.find_all('a', href=True)
        show_links = [link for link in links if '/shows/' in link.get('href', '')]
        self.logger.info(f"Found {len(show_links)} potential show detail links")
        
        # Save raw HTML for analysis
        html_file = self.output_dir / "shows_list_raw.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        self.logger.info(f"Saved raw HTML to: {html_file}")
        
        return True
    
    def analyze_page_structure(self):
        """Analyze the structure of the shows page to understand the data format."""
        self.logger.info("Analyzing page structure...")
        
        soup = self.fetch_page(self.shows_url)
        if not soup:
            return False
        
        # Look for show items
        show_items = soup.find_all('li', class_='show-info')
        self.logger.info(f"Found {len(show_items)} show items")
        
        # Analyze first few shows
        for i, show_item in enumerate(show_items[:5]):
            show_link = show_item.find('a', class_='data-display')
            if show_link:
                href = show_link.get('href', '')
                self.logger.info(f"  Show {i+1}: {href}")
                
                # Extract show details
                band = show_item.find('h5', class_='subhead-bn')
                venue = show_item.find('h1', class_='subhead-vn') 
                location = show_item.find('h3', class_='subhead-mdy-lg')
                date = show_item.find('h4', class_='subhead-mdy-lg')
                
                if band and venue:
                    self.logger.info(f"    Band: {band.get_text().strip()}")
                    self.logger.info(f"    Venue: {venue.get_text().strip()}")
                    if location:
                        self.logger.info(f"    Location: {location.get_text().strip()}")
                    if date:
                        self.logger.info(f"    Date: {date.get_text().strip()}")
        
        # Look for pagination
        pagination_elements = soup.find_all(['a', 'span'], string=lambda text: text and ('next' in text.lower() or 'page' in text.lower() or text.isdigit()))
        if pagination_elements:
            self.logger.info(f"Found potential pagination: {[elem.get_text().strip() for elem in pagination_elements[:5]]}")
        
        return True
    
    def parse_shows_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse show data from a page."""
        shows = []
        show_items = soup.find_all('li', class_='show-info')
        
        for show_item in show_items:
            try:
                show_link = show_item.find('a', class_='data-display')
                if not show_link:
                    continue
                
                show_url = show_link.get('href', '')
                if not show_url:
                    continue
                
                # Extract basic show info
                band_elem = show_item.find('h5', class_='subhead-bn')
                venue_elem = show_item.find('h1', class_='subhead-vn')
                location_elem = show_item.find('h3', class_='subhead-mdy-lg')
                date_elem = show_item.find('h4', class_='subhead-mdy-lg')
                
                # Also check mobile layout
                if not location_elem or not date_elem:
                    mobile_elem = show_item.find('h4', class_='subhead-mdy')
                    if mobile_elem:
                        # Mobile format: "Location | Date"
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
                
                show_data = {
                    'url': show_url,
                    'band': band_elem.get_text().strip() if band_elem else "",
                    'venue': venue_elem.get_text().strip() if venue_elem else "",
                    'location': location_text,
                    'date': date_text,
                    # Extract show ID from URL for identification
                    'show_id': show_url.split('/')[-2] if show_url.split('/') else ""
                }
                
                shows.append(show_data)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse show item: {e}")
                continue
        
        return shows
    
    def get_total_pages(self, soup: BeautifulSoup) -> int:
        """Extract total number of pages from pagination."""
        try:
            # Look for pagination with data-total attribute
            pagination_input = soup.find('input', {'data-total': True})
            if pagination_input:
                total_pages = int(pagination_input.get('data-total', 1))
                return total_pages
            
            # Fallback: look for "111" link in pagination
            total_link = soup.find('li', class_='total')
            if total_link:
                total_text = total_link.get_text().strip()
                if total_text.isdigit():
                    return int(total_text)
            
            return 1
        except (ValueError, AttributeError):
            return 1
    
    def collect_show_list(self, max_pages: Optional[int] = None, start_page: int = 1) -> List[Dict]:
        """Collect the complete list of shows from all pages."""
        self.logger.info("Starting show list collection...")
        
        # First, get the first page to determine total pages
        soup = self.fetch_page(self.shows_url)
        if not soup:
            return []
        
        total_pages = self.get_total_pages(soup)
        self.logger.info(f"Found {total_pages} total pages")
        
        # Calculate end page
        end_page = total_pages
        if max_pages:
            end_page = min(start_page + max_pages - 1, total_pages)
            self.logger.info(f"Collecting pages {start_page} to {end_page} ({max_pages} pages)")
        else:
            self.logger.info(f"Collecting pages {start_page} to {end_page}")
        
        all_shows = []
        
        # Process pages from start_page to end_page
        for page_num in range(start_page, end_page + 1):
            if page_num == 1 and start_page == 1:
                # We already have the first page
                current_soup = soup
                current_url = self.shows_url
            else:
                # Construct URL for any page (including page 1 if start_page != 1)
                # Pattern: /shows/page/N/?bid%5B3588%5D=on&kw&sd&ed&reg&stat&cty&ec&octy&srt=DO
                current_url = f"{self.base_url}/shows/page/{page_num}/?bid%5B3588%5D=on&kw&sd&ed&reg&stat&cty&ec&octy&srt=DO"
                current_soup = self.fetch_page(current_url)
                
            if not current_soup:
                self.logger.warning(f"Failed to fetch page {page_num}, skipping")
                continue
            
            self.logger.info(f"Processing page {page_num}/{end_page}: {current_url}")
            
            # Parse shows from this page
            page_shows = self.parse_shows_from_page(current_soup)
            all_shows.extend(page_shows)
            
            self.logger.info(f"  Found {len(page_shows)} shows on page {page_num}")
            
            # Progress update every 10 pages
            if page_num % 10 == 0:
                self.logger.info(f"Progress: {page_num}/{end_page} pages ({len(all_shows)} shows collected)")
        
        pages_collected = end_page - start_page + 1
        self.logger.info(f"Collected {len(all_shows)} total shows from {pages_collected} pages")
        
        # Save show list
        shows_file = self.output_dir / "shows_list.json"
        with open(shows_file, 'w') as f:
            json.dump(all_shows, f, indent=2)
        
        self.logger.info(f"Saved show list to: {shows_file}")
        
        return all_shows
    
    def fetch_show_detail(self, show_url: str, save_html: bool = False) -> Optional[Dict]:
        """Fetch detailed information from a show page."""
        soup = self.fetch_page(show_url)
        if not soup:
            return None
        
        try:
            show_data = {'url': show_url}
            
            # Save raw HTML for analysis if requested
            if save_html:
                show_id = show_url.split('/')[-2] if show_url.split('/') else "unknown"
                html_file = self.output_dir / f"show_{show_id}_raw.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(str(soup))
                self.logger.info(f"Saved raw show HTML to: {html_file}")
            
            # Extract page title
            title = soup.find('title')
            if title:
                show_data['page_title'] = title.get_text().strip()
            
            # Extract setlist information
            show_data['setlist'] = self._extract_setlist(soup)
            
            # Extract band lineup
            show_data['lineup'] = self._extract_lineup(soup)
            
            # Extract supporting acts
            show_data['supporting_acts'] = self._extract_supporting_acts(soup)
            
            return show_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse show detail for {show_url}: {e}")
            return None
    
    def _extract_setlist(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract setlist information from show page."""
        setlist = []
        
        # Find all set sections
        set_sections = soup.find_all('h3', class_='set-title')
        
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
                
                # Check if song has a link (linked songs have individual pages)
                song_link = song_item.find('a')
                if song_link:
                    song_data['name'] = song_link.get_text().strip()
                    song_data['url'] = song_link.get('href', '')
                else:
                    song_data['name'] = song_item.get_text().strip()
                    song_data['url'] = None
                
                # Check for segue notation (>)
                song_text = song_item.get_text().strip()
                if song_text.endswith(' > ') or song_text.endswith('>'):
                    song_data['segue_into_next'] = True
                else:
                    song_data['segue_into_next'] = False
                
                # Clean up song name (remove > notation)
                song_data['name'] = song_data['name'].rstrip(' >').rstrip('>')
                
                songs.append(song_data)
            
            if songs:
                setlist.append({
                    'set_name': set_name,
                    'songs': songs
                })
        
        return setlist
    
    def _extract_lineup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract band lineup information from show page."""
        lineup = []
        
        # Find the lineup section
        lineup_list = soup.find('ul', class_='lineup-list')
        if not lineup_list:
            return lineup
        
        artist_items = lineup_list.find_all('li', class_='artist-info')
        
        for artist_item in artist_items:
            artist_data = {}
            
            # Extract artist name
            name_link = artist_item.find('a', class_='name')
            if name_link:
                artist_data['name'] = name_link.get_text().strip()
            else:
                # Fallback: look for <b> tag or just get text
                name_bold = artist_item.find('b')
                if name_bold:
                    artist_data['name'] = name_bold.get_text().strip()
                else:
                    # Extract from paragraph text
                    paragraph = artist_item.find('p')
                    if paragraph:
                        # Get first line before <br> or <span>
                        name_text = paragraph.get_text().split('\n')[0].strip()
                        artist_data['name'] = name_text
            
            # Extract instruments/role
            span_element = artist_item.find('span')
            if span_element:
                artist_data['instruments'] = span_element.get_text().strip()
            else:
                # Fallback: try to extract from paragraph after name
                paragraph = artist_item.find('p')
                if paragraph:
                    full_text = paragraph.get_text()
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    if len(lines) > 1:
                        artist_data['instruments'] = lines[1]
            
            # Extract image URL if available
            img = artist_item.find('img')
            if img:
                artist_data['image_url'] = img.get('src', '')
            
            if artist_data.get('name'):
                lineup.append(artist_data)
        
        return lineup
    
    def _extract_supporting_acts(self, soup: BeautifulSoup) -> List[str]:
        """Extract supporting acts from show page."""
        supporting_acts = []
        
        # Find supporting acts section
        supporting_section = soup.find('ul', class_='supporting-acts')
        if supporting_section:
            act_items = supporting_section.find_all('li')
            for act_item in act_items:
                act_name = act_item.get_text().strip()
                if act_name:
                    supporting_acts.append(act_name)
        
        return supporting_acts
    
    def test_show_detail(self, show_url: str):
        """Test fetching a single show detail page."""
        self.logger.info(f"Testing show detail fetch for: {show_url}")
        
        show_detail = self.fetch_show_detail(show_url, save_html=True)
        if show_detail:
            self.logger.info("Show detail fetch successful!")
            
            # Log basic info
            for key, value in show_detail.items():
                if key not in ['setlist', 'lineup', 'supporting_acts']:
                    self.logger.info(f"  {key}: {value}")
            
            # Log setlist
            if show_detail.get('setlist'):
                self.logger.info(f"  setlist: {len(show_detail['setlist'])} sets")
                for set_data in show_detail['setlist']:
                    self.logger.info(f"    {set_data['set_name']}: {len(set_data['songs'])} songs")
                    for song in set_data['songs'][:3]:  # Show first 3 songs
                        segue = " >" if song['segue_into_next'] else ""
                        self.logger.info(f"      - {song['name']}{segue}")
                    if len(set_data['songs']) > 3:
                        self.logger.info(f"      ... and {len(set_data['songs']) - 3} more")
            
            # Log lineup
            if show_detail.get('lineup'):
                self.logger.info(f"  lineup: {len(show_detail['lineup'])} members")
                for member in show_detail['lineup']:
                    self.logger.info(f"    - {member['name']}: {member.get('instruments', 'unknown')}")
            
            # Log supporting acts
            if show_detail.get('supporting_acts'):
                self.logger.info(f"  supporting_acts: {', '.join(show_detail['supporting_acts'])}")
            
            # Save detailed JSON for inspection
            show_id = show_url.split('/')[-2] if show_url.split('/') else "unknown"
            detail_file = self.output_dir / f"show_{show_id}_detail.json"
            with open(detail_file, 'w') as f:
                json.dump(show_detail, f, indent=2)
            self.logger.info(f"Saved detailed JSON to: {detail_file}")
            
            return True
        else:
            self.logger.error("Show detail fetch failed")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Collect Grateful Dead show data from jerrygarcia.com')
    parser.add_argument('--test', action='store_true',
                       help='Test access to the site and analyze structure')
    parser.add_argument('--collect', action='store_true',
                       help='Collect show list from all pages')
    parser.add_argument('--test-show-detail', type=str,
                       help='Test fetching detail for a specific show URL')
    parser.add_argument('--max-pages', type=int,
                       help='Maximum number of pages to collect (for testing)')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Page number to start collection from')
    parser.add_argument('--output-dir', default='stage01-collected-data/jerrygarcia',
                       help='Output directory for collected data')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between requests in seconds')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    collector = JerryGarciaShowCollector(
        output_dir=args.output_dir,
        delay=args.delay
    )
    
    if args.test:
        # Test access and analyze structure
        if collector.test_access():
            collector.analyze_page_structure()
            print(f"✅ Test complete! Check {args.output_dir}/collection.log and shows_list_raw.html for details")
            return 0
        else:
            print("❌ Test failed. Check logs for details.")
            return 1
    
    elif args.collect:
        # Collect show list
        try:
            shows = collector.collect_show_list(max_pages=args.max_pages, start_page=args.start_page)
            print(f"✅ Collected {len(shows)} shows! Check {args.output_dir}/shows_list.json")
            return 0
        except Exception as e:
            print(f"❌ Collection failed: {e}")
            return 1
    
    elif args.test_show_detail:
        # Test show detail fetching
        if collector.test_show_detail(args.test_show_detail):
            print(f"✅ Show detail test complete! Check {args.output_dir}/ for raw HTML")
            return 0
        else:
            print("❌ Show detail test failed. Check logs for details.")
            return 1
    
    print("Use --test to test access, --collect to collect show data, or --test-show-detail <url> to test show details")
    return 0


if __name__ == '__main__':
    exit(main())