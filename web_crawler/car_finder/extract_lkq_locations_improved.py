#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import re
import time
import logging
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LKQLocationExtractorImproved:
    """Extract all LKQ Pick Your Part location URLs by parsing the location dropdown and patterns."""
    
    def __init__(self):
        self.base_url = "https://www.lkqpickyourpart.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
    def extract_all_locations(self) -> List[str]:
        """Extract all LKQ locations from the website."""
        logger.info("Starting LKQ location extraction...")
        
        # Use the known working URL
        url = "https://www.lkqpickyourpart.com/parts/monrovia-1281/?year=2005&make=HONDA&model=INSIGHT&part="
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract dropdown options
            dropdown_data = self._extract_dropdown_data(soup)
            
            # Extract location patterns from HTML
            location_patterns = self._extract_location_patterns(response.text)
            
            # Map dropdown values to location patterns
            location_urls = self._map_dropdown_to_patterns(dropdown_data, location_patterns)
            
            logger.info(f"Successfully extracted {len(location_urls)} LKQ locations")
            return location_urls
            
        except Exception as e:
            logger.error(f"Error extracting LKQ locations: {e}")
            return []
    
    def _extract_dropdown_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract location dropdown data (value -> city name)."""
        dropdown_data = {}
        
        # Find the location dropdown
        location_select = soup.find('select', {'id': 'locationBox'})
        
        if location_select:
            options = location_select.find_all('option')
            
            for option in options:
                value = option.get('value', '')
                text = option.get_text(strip=True)
                
                # Skip the placeholder option
                if value and value != '0' and text and text != 'Please Select A Location':
                    dropdown_data[value] = text
            
            logger.info(f"Found {len(dropdown_data)} locations in dropdown")
        
        return dropdown_data
    
    def _extract_location_patterns(self, html_content: str) -> List[str]:
        """Extract location patterns from HTML content."""
        # Look for patterns like "city-1234" in the HTML
        location_patterns = re.findall(r'([a-zA-Z\s\-]+-\d{4})', html_content)
        
        # Clean up and deduplicate
        unique_patterns = []
        seen = set()
        
        for pattern in location_patterns:
            # Clean up the pattern (remove extra spaces, normalize dashes)
            cleaned_pattern = re.sub(r'\s+', '-', pattern.strip().lower())
            if cleaned_pattern not in seen and re.match(r'^[a-zA-Z\-]+-\d{4}$', cleaned_pattern):
                unique_patterns.append(cleaned_pattern)
                seen.add(cleaned_pattern)
        
        logger.info(f"Found {len(unique_patterns)} unique location patterns")
        return unique_patterns
    
    def _map_dropdown_to_patterns(self, dropdown_data: Dict[str, str], location_patterns: List[str]) -> List[str]:
        """Map dropdown values to location patterns and generate URLs."""
        location_urls = []
        
        # Create a mapping of location IDs to patterns
        pattern_map = {}
        for pattern in location_patterns:
            # Extract the ID from the pattern (e.g., "monrovia-1281" -> "1281")
            match = re.search(r'-(\d{4})$', pattern)
            if match:
                location_id = match.group(1)
                pattern_map[location_id] = pattern
        
        # Generate URLs for each dropdown option
        for location_id, city_name in dropdown_data.items():
            if location_id in pattern_map:
                # Use the pattern from the HTML
                pattern = pattern_map[location_id]
                url = f"{self.base_url}/parts/{pattern}/?year=2005&make=HONDA&model=INSIGHT&part="
                location_urls.append(url)
                logger.debug(f"Mapped {city_name} ({location_id}) -> {pattern}")
            else:
                # Try to guess the pattern from the city name
                city_slug = self._city_to_slug(city_name)
                guessed_pattern = f"{city_slug}-{location_id}"
                url = f"{self.base_url}/parts/{guessed_pattern}/?year=2005&make=HONDA&model=INSIGHT&part="
                location_urls.append(url)
                logger.debug(f"Guessed pattern for {city_name} ({location_id}) -> {guessed_pattern}")
        
        return location_urls
    
    def _city_to_slug(self, city_name: str) -> str:
        """Convert city name to URL-friendly slug."""
        # Convert to lowercase and replace spaces with dashes
        slug = city_name.lower().replace(' ', '-')
        
        # Remove special characters except dashes
        slug = re.sub(r'[^a-zA-Z0-9\-]', '', slug)
        
        # Remove multiple consecutive dashes
        slug = re.sub(r'-+', '-', slug)
        
        # Remove leading/trailing dashes
        slug = slug.strip('-')
        
        return slug
    
    def validate_locations(self, locations: List[str]) -> List[str]:
        """Validate that the extracted locations are actually working."""
        valid_locations = []
        
        logger.info(f"Validating {len(locations)} locations...")
        
        for i, url in enumerate(locations):
            if i > 0 and i % 10 == 0:
                logger.info(f"Validated {i}/{len(locations)} locations...")
                time.sleep(1)  # Be respectful to the server
            
            try:
                response = requests.get(url, headers=self.headers, timeout=5)
                if response.status_code == 200:
                    valid_locations.append(url)
                    logger.debug(f"Valid location: {url}")
                else:
                    logger.debug(f"Invalid location: {url} (status: {response.status_code})")
                    
            except Exception as e:
                logger.debug(f"Error validating location {url}: {e}")
                continue
        
        logger.info(f"Found {len(valid_locations)} valid locations out of {len(locations)} total")
        return valid_locations
    
    def save_locations(self, locations: List[str], filename: str = "lkq_locations_complete.txt"):
        """Save the extracted locations to a file."""
        try:
            with open(filename, 'w') as f:
                f.write("# LKQ Pick Your Part Location URLs\n")
                f.write("# Auto-extracted from https://www.lkqpickyourpart.com\n")
                f.write(f"# Total locations found: {len(locations)}\n\n")
                
                for url in sorted(locations):
                    f.write(f"{url}\n")
            
            logger.info(f"Saved {len(locations)} locations to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving locations to file: {e}")
    
    def display_results(self, locations: List[str]):
        """Display the extracted locations in a readable format."""
        print(f"\n{'='*80}")
        print(f"EXTRACTED LKQ LOCATIONS ({len(locations)} total)")
        print(f"{'='*80}")
        
        for i, url in enumerate(sorted(locations), 1):
            # Extract location name from URL
            match = re.search(r'/parts/([^/]+)/', url)
            location_name = match.group(1) if match else "unknown"
            print(f"{i:2d}. {location_name:<25} -> {url}")
        
        print(f"{'='*80}")

def main():
    """Main function to extract and save LKQ locations."""
    extractor = LKQLocationExtractorImproved()
    
    # Extract all locations
    locations = extractor.extract_all_locations()
    
    if locations:
        # Display results
        extractor.display_results(locations)
        
        # Ask if user wants to validate
        print(f"\nFound {len(locations)} unique locations.")
        validate = input("Would you like to validate these locations? (y/n): ").lower().strip()
        
        if validate == 'y':
            validated_locations = extractor.validate_locations(locations)
            extractor.save_locations(validated_locations)
            print(f"\nValidated and saved {len(validated_locations)} working locations.")
        else:
            extractor.save_locations(locations)
            print(f"\nSaved {len(locations)} locations (unvalidated).")
    else:
        logger.error("No locations found!")

if __name__ == "__main__":
    main() 