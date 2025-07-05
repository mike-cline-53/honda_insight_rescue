#!/usr/bin/env python3

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base_scraper import BaseScraper, Vehicle

logger = logging.getLogger(__name__)

class LKQScraper(BaseScraper):
    """Scraper for LKQ Pick Your Part Honda Insight listings."""
    
    def __init__(self):
        super().__init__("LKQ Pick Your Part")
        self.base_url = "https://www.lkqpickyourpart.com"
        # Load all locations from the auto-extracted file
        self.location_urls = self._load_locations_from_file()
        self.years = ['1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006']
        
    def _load_locations_from_file(self) -> List[str]:
        """Load LKQ locations from the auto-extracted file."""
        import os
        
        # Look for the locations file in the current directory or parent directories
        possible_paths = [
            'lkq_locations_complete.txt',
            '../lkq_locations_complete.txt',
            '../../lkq_locations_complete.txt',
            os.path.join(os.path.dirname(__file__), '..', 'lkq_locations_complete.txt'),
        ]
        
        for file_path in possible_paths:
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        locations = []
                        for line in f:
                            line = line.strip()
                            # Skip comments and empty lines
                            if line and not line.startswith('#'):
                                locations.append(line)
                        
                        logger.info(f"Loaded {len(locations)} LKQ locations from {file_path}")
                        return locations
            except Exception as e:
                logger.error(f"Error reading locations file {file_path}: {e}")
                continue
        
        logger.warning("Could not find lkq_locations_complete.txt file. Using fallback locations.")
        # Fallback to a few known locations if file not found
        return [
            "https://www.lkqpickyourpart.com/parts/huntsville-1223/?year=2005&make=HONDA&model=INSIGHT&part=",
            "https://www.lkqpickyourpart.com/parts/monrovia-1281/?year=2005&make=HONDA&model=INSIGHT&part=",
            "https://www.lkqpickyourpart.com/parts/anaheim-1265/?year=2005&make=HONDA&model=INSIGHT&part=",
        ]
        
    def scrape_listings(self) -> List[Vehicle]:
        """Scrape Honda Insight listings from LKQ Pick Your Part."""
        logger.info("Starting LKQ Pick Your Part scraping for Honda Insight (1999-2006)")
        
        all_vehicles = []
        
        # Use the pre-loaded locations
        if not self.location_urls:
            logger.error("No LKQ locations loaded. Please ensure lkq_locations_complete.txt exists.")
            return []
        
        logger.info(f"Searching {len(self.location_urls)} LKQ locations across {len(self.years)} years...")
        
        # Build all URL combinations for parallel processing
        url_combinations = []
        for base_location_url in self.location_urls:
            for year in self.years:
                inventory_url = self._convert_to_inventory_search_url(base_location_url, year)
                url_combinations.append(inventory_url)
        
        logger.info(f"Processing {len(url_combinations)} URL combinations in parallel...")
        
        # Process all location/year combinations in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all scraping tasks
            future_to_url = {
                executor.submit(self._scrape_location, url): url
                for url in url_combinations
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    vehicles = future.result()
                    all_vehicles.extend(vehicles)
                    if vehicles:
                        logger.info(f"Found {len(vehicles)} vehicles from {url}")
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    continue
        
        logger.info(f"Found {len(all_vehicles)} Honda Insight listings across all LKQ locations and years")
        return all_vehicles
    

    def _scrape_location(self, url: str) -> List[Vehicle]:
        """Scrape a specific LKQ location."""
        logger.info(f"Scraping LKQ location: {url}")
        
        response = self._make_request(url)
        if not response:
            return []
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            vehicles = []
            
            # Extract vehicles from the inventory search page
            vehicles = self._extract_vehicles_from_inventory_search(soup, url)
            
            logger.info(f"Found {len(vehicles)} Honda Insight listings at this LKQ location")
            return vehicles
            
        except Exception as e:
            logger.error(f"Error parsing LKQ location page: {e}")
            return []
    
    def _convert_to_inventory_search_url(self, url: str, year: str) -> str:
        """Convert parts URL to inventory URL with search parameter."""
        # Example: https://www.lkqpickyourpart.com/parts/monrovia-1281/?year=2005&make=HONDA&model=INSIGHT&part=
        # Becomes: https://www.lkqpickyourpart.com/inventory/monrovia-1281/?search=2005+honda+insight
        
        # Extract location from URL
        location_match = re.search(r'/parts/([^/]+)/', url)
        if location_match:
            location_part = location_match.group(1)
            base_url = "https://www.lkqpickyourpart.com"
            # Build search query for Honda Insight
            search_query = f"{year}+honda+insight"
            inventory_url = f"{base_url}/inventory/{location_part}/?search={search_query}"
            return inventory_url
        
        # If can't convert, return original URL
        return url
    
    def _convert_to_inventory_url(self, url: str) -> str:
        """Convert parts search URL to inventory URL."""
        # Example: https://www.lkqpickyourpart.com/parts/monrovia-1281/?year=2006&make=HONDA&model=CIVIC&part=
        # Becomes: https://www.lkqpickyourpart.com/inventory/monrovia-1281/
        
        # Extract location from URL
        location_match = re.search(r'/parts/([^/]+)/', url)
        if location_match:
            location_part = location_match.group(1)
            base_url = "https://www.lkqpickyourpart.com"
            inventory_url = f"{base_url}/inventory/{location_part}/"
            return inventory_url
        
        # If can't convert, return original URL
        return url
    
    def _extract_vehicles_from_inventory_search(self, soup: BeautifulSoup, source_url: str) -> List[Vehicle]:
        """Extract vehicles from LKQ inventory search page."""
        vehicles = []
        
        try:
            # Extract location from URL
            location = self._extract_lkq_location(source_url, "")
            
            # Extract year from search URL
            year_match = re.search(r'search=(\d{4})', source_url)
            target_year = year_match.group(1) if year_match else None
            
            # Check if page shows "We don't see any" message
            page_text = soup.get_text()
            if "don't see any" in page_text.lower() or "no vehicles" in page_text.lower():
                logger.info(f"No Honda Insight vehicles found at {location} for year {target_year}")
                return []
            
            # Look for vehicle result rows in inventory search page
            # LKQ inventory search uses: <div class="pypvi_resultRow" id="1281-159500">
            vehicle_rows = soup.find_all('div', class_='pypvi_resultRow')
            
            for row in vehicle_rows:
                try:
                    # Extract vehicle details from each row
                    vehicle = self._extract_vehicle_from_row(row, location, source_url)
                    if vehicle:
                        # Since we're using search URL, results should already be filtered
                        # But let's double-check for Honda Insight
                        if (vehicle.make.lower() == 'honda' and 
                            'insight' in vehicle.model.lower() and
                            target_year and vehicle.year == target_year):
                            vehicles.append(vehicle)
                except Exception as e:
                    logger.warning(f"Error extracting vehicle from row: {e}")
                    continue
            
            return vehicles
            
        except Exception as e:
            logger.error(f"Error extracting vehicles from inventory search: {e}")
            return []
    
    def _extract_vehicles_from_inventory(self, soup: BeautifulSoup, source_url: str) -> List[Vehicle]:
        """Extract vehicles from LKQ inventory page."""
        vehicles = []
        
        try:
            # Extract location from URL
            location = self._extract_lkq_location(source_url, "")
            
            # Look for vehicle result rows in inventory page
            # LKQ inventory uses: <div class="pypvi_resultRow" id="1281-159500">
            vehicle_rows = soup.find_all('div', class_='pypvi_resultRow')
            
            for row in vehicle_rows:
                try:
                    # Extract vehicle details from each row
                    vehicle = self._extract_vehicle_from_row(row, location, source_url)
                    if vehicle:
                        vehicles.append(vehicle)
                except Exception as e:
                    logger.warning(f"Error extracting vehicle from row: {e}")
                    continue
            
            # Filter for Honda Insight vehicles only (1999-2006)
            honda_vehicles = [v for v in vehicles if v.make.lower() == 'honda']
            
            # For Honda Insight specifically, filter further
            insight_vehicles = [v for v in honda_vehicles if 'insight' in v.model.lower()]
            
            # Additional year filter to ensure we only get 1999-2006 Honda Insight
            filtered_insights = []
            for vehicle in insight_vehicles:
                try:
                    year_int = int(vehicle.year)
                    if 1999 <= year_int <= 2006:
                        filtered_insights.append(vehicle)
                except (ValueError, TypeError):
                    # Skip vehicles with invalid year data
                    continue
            
            # Return only Honda Insight vehicles from 1999-2006
            return filtered_insights
            
        except Exception as e:
            logger.error(f"Error extracting vehicles from inventory: {e}")
            return []
    
    def _extract_vehicle_from_row(self, row_div, location: str, source_url: str) -> Optional[Vehicle]:
        """Extract vehicle details from a single inventory row."""
        try:
            # Extract year, make, model from the pypvi_ymm link
            ymm_link = row_div.find('a', class_='pypvi_ymm')
            if not ymm_link:
                return None
                
            ymm_text = ymm_link.get_text(strip=True)
            # Format: "2002LEXUSRX300" (no spaces)
            
            if len(ymm_text) < 5:  # Must have at least year + some text
                return None
            
            # Extract year (first 4 characters)
            year = ymm_text[:4]
            
            # Extract make and model from remaining text
            remaining_text = ymm_text[4:]  # Everything after year
            
            # Try to identify common makes
            make = None
            model = None
            
            # List of common makes to look for
            common_makes = ['HONDA', 'TOYOTA', 'FORD', 'CHEVROLET', 'CHEVY', 'NISSAN', 'LEXUS', 
                          'BMW', 'MERCEDES', 'AUDI', 'VOLKSWAGEN', 'VW', 'HYUNDAI', 'KIA',
                          'SUBARU', 'MAZDA', 'MITSUBISHI', 'ACURA', 'INFINITI', 'CADILLAC',
                          'BUICK', 'GMC', 'DODGE', 'CHRYSLER', 'JEEP', 'RAM']
            
            # Find which make is at the beginning of remaining_text
            for potential_make in common_makes:
                if remaining_text.startswith(potential_make):
                    make = potential_make
                    model = remaining_text[len(potential_make):]  # Everything after the make
                    break
            
            # If no make found, split at common patterns
            if not make:
                # Fallback: try to guess based on capitalization or common patterns
                # For now, assume first word-like chunk is make, rest is model
                import re
                match = re.match(r'^([A-Z]+)([A-Z0-9]+)$', remaining_text)
                if match:
                    make = match.group(1)
                    model = match.group(2)
                else:
                    # Last resort: split at midpoint
                    mid = len(remaining_text) // 2
                    make = remaining_text[:mid]
                    model = remaining_text[mid:]
            
            # Clean up model name
            if model and len(model) > 20:  # If model seems too long, truncate
                model = model[:20]
            
            # Extract availability date
            date_added = None
            time_elem = row_div.find('time')
            if time_elem and time_elem.get('datetime'):
                date_added = time_elem.get('datetime')
            
            # Extract individual vehicle URL
            vehicle_url = ymm_link.get('href') if ymm_link else None
            if vehicle_url and not vehicle_url.startswith('http'):
                vehicle_url = f"https://www.lkqpickyourpart.com{vehicle_url}"
            
            # Create unique VIN from the row ID
            row_id = row_div.get('id', '')
            vin = f"LKQ_{row_id}" if row_id else f"LKQ_{location}_{year}_{make}_{model}"
            
            # Create vehicle object
            vehicle = Vehicle(
                vin=vin,
                year=year,
                make=make,
                model=model,
                location=location,
                yard="LKQ Pick Your Part",
                date_added=date_added,
                source_url=vehicle_url or source_url,
                price=None  # Price not available on inventory page
            )
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Error extracting vehicle from row: {e}")
            return None

    def _extract_vehicles_from_page(self, html_content: str, soup: BeautifulSoup, source_url: str) -> List[Vehicle]:
        """Extract all Honda Insight vehicles from the page structure."""
        vehicles = []
        
        try:
            # Extract year from URL
            year_match = re.search(r'year=(\d{4})', source_url)
            year = year_match.group(1) if year_match else None
            
            # Extract location from URL
            location = self._extract_lkq_location(source_url, "")
            
            # Look for vehicle listings in common HTML patterns
            # LKQ typically shows vehicle listings in tables, divs, or lists
            
            # Pattern 1: Look for vehicle tables or rows
            vehicle_rows = soup.find_all(['tr', 'div', 'li'], class_=re.compile(r'vehicle|result|listing|row', re.I))
            
            # Pattern 2: Look for any elements containing VIN patterns
            all_text_elements = soup.find_all(text=re.compile(r'[A-HJ-NPR-Z0-9]{17}', re.I))
            
            # Pattern 3: Look for specific LKQ result patterns
            lkq_results = soup.find_all(['div', 'table', 'tbody'], class_=re.compile(r'result|inventory|vehicle', re.I))
            
            # Combine all potential vehicle containers
            potential_vehicles = set()
            
            # Check vehicle rows
            for row in vehicle_rows:
                row_text = row.get_text()
                if self._contains_vehicle_info(row_text):
                    potential_vehicles.add(row_text)
            
            # Check text elements with VINs
            for element in all_text_elements:
                parent = element.parent
                if parent:
                    parent_text = parent.get_text()
                    if self._contains_vehicle_info(parent_text):
                        potential_vehicles.add(parent_text)
            
            # Check LKQ specific results
            for result in lkq_results:
                result_text = result.get_text()
                if self._contains_vehicle_info(result_text):
                    potential_vehicles.add(result_text)
            
            # If we found potential vehicles, create Vehicle objects
            for vehicle_text in potential_vehicles:
                # Extract VIN from the text
                vin_match = re.search(r'([A-HJ-NPR-Z0-9]{17})', vehicle_text)
                vin = vin_match.group(1) if vin_match else f"LKQ_{len(vehicles)+1}"
                
                # Extract other details
                date_added = self._extract_date_from_context(vehicle_text)
                price = self._extract_price_from_context(vehicle_text)
                
                # Create vehicle object
                vehicle = Vehicle(
                    vin=vin,
                    year=year,
                    make="Honda",
                    model="Insight",
                    location=location,
                    yard="LKQ Pick Your Part",
                    date_added=date_added,
                    source_url=source_url,
                    price=price
                )
                
                vehicles.append(vehicle)
            
            # If no structured results found, but we have Honda/Insight mentions, create a basic entry
            if not vehicles and self._page_has_honda_insight_mentions(html_content):
                vehicle = Vehicle(
                    vin=f"LKQ_{location}_{year}",
                    year=year,
                    make="Honda",
                    model="Insight",
                    location=location,
                    yard="LKQ Pick Your Part",
                    date_added=None,
                    source_url=source_url,
                    price=None
                )
                vehicles.append(vehicle)
                
        except Exception as e:
            logger.error(f"Error extracting vehicles from page: {e}")
        
        return vehicles
    
    def _contains_vehicle_info(self, text: str) -> bool:
        """Check if text contains vehicle information."""
        text_lower = text.lower()
        
        # Look for Honda/Insight mentions
        honda_mentions = 'honda' in text_lower or 'insight' in text_lower
        
        # Look for year mentions
        year_mentions = any(year in text for year in ['1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006'])
        
        # Look for VIN patterns
        vin_pattern = bool(re.search(r'[A-HJ-NPR-Z0-9]{17}', text))
        
        # Look for price or date patterns
        price_pattern = bool(re.search(r'\$\d+', text))
        date_pattern = bool(re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', text))
        
        # Must have Honda/Insight mention plus at least one other indicator
        return honda_mentions and (year_mentions or vin_pattern or price_pattern or date_pattern)
    
    def _page_has_honda_insight_mentions(self, html_content: str) -> bool:
        """Check if the page mentions Honda Insight vehicles."""
        content_lower = html_content.lower()
        
        # Look for Honda Insight mentions
        honda_insight = 'honda' in content_lower and 'insight' in content_lower
        
        # Look for year range mentions
        year_mentions = any(year in content_lower for year in ['1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006'])
        
        return honda_insight and year_mentions
    
    def _extract_lkq_location(self, url: str, context: str) -> Optional[str]:
        """Extract location information from LKQ URL and context."""
        # Extract location from URL (handle both parts and inventory URLs)
        location_match = re.search(r'/(?:parts|inventory)/([^/]+)-\d+/', url)
        if location_match:
            location_name = location_match.group(1).replace('-', ' ').title()
            return location_name
        
        # Look for location in context
        lkq_patterns = [
            r'LKQ\s*Pick\s*Your\s*Part\s*-?\s*([A-Za-z\s]+)',
            r'Location\s*:?\s*([A-Za-z\s,]+)',
            r'Address\s*:?\s*([A-Za-z\s,]+)'
        ]
        
        for pattern in lkq_patterns:
            location_match = re.search(pattern, context, re.IGNORECASE)
            if location_match:
                return location_match.group(1).strip()
        
        return "LKQ Pick Your Part"
    
    def _extract_yard_info(self, context: str) -> Optional[str]:
        """Extract yard/facility information."""
        yard_patterns = [
            r'LKQ\s*Pick\s*Your\s*Part\s*-?\s*([A-Za-z\s]+)',
            r'(LKQ\s*Pick\s*Your\s*Part)',
            r'Yard\s*:?\s*([A-Za-z0-9\s]+)'
        ]
        
        for pattern in yard_patterns:
            yard_match = re.search(pattern, context, re.IGNORECASE)
            if yard_match:
                return yard_match.group(1).strip()
        
        return "LKQ Pick Your Part"
    

    
    def _extract_date_from_context(self, context: str) -> Optional[str]:
        """Extract date information from context."""
        # Look for date patterns
        date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}'
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, context, re.IGNORECASE)
            if date_match:
                return date_match.group(1)
        
        return None
    
    def _extract_price_from_context(self, context: str) -> Optional[str]:
        """Extract price information from context."""
        # Look for price patterns
        price_patterns = [
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',
            r'Price\s*:?\s*\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, context, re.IGNORECASE)
            if price_match:
                return f"${price_match.group(1)}"
        
        return None 