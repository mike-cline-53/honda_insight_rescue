#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import logging
from typing import List, Dict, Optional
from .base_scraper import BaseScraper, Vehicle

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Row52Scraper(BaseScraper):
    """Scraper for Row52.com Honda Insight listings."""
    
    def __init__(self):
        super().__init__("Row52")
        self.base_url = "https://www.row52.com"
        self.search_url = f"{self.base_url}/Search/?YMMorVin=YMM&Year=1999-2006&V1=&V2=&V3=&V4=&V5=&V6=&V7=&V8=&V9=&V10=&V11=&V12=&V13=&V14=&V15=&V16=&V17=&ZipCode=&Page=1&ModelId=2466&MakeId=145&LocationId=&IsVin=false&Distance=50"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def scrape_listings(self) -> List[Vehicle]:
        """Scrape Honda Insight listings from Row52."""
        logger.info("Starting Row52 scraping for Honda Insight 1999-2006")
        
        try:
            # Fetch the page
            response = requests.get(self.search_url, headers=self.headers)
            response.raise_for_status()
            
            logger.info(f"Successfully fetched page. Status: {response.status_code}, Length: {len(response.text)}")
            
            # Extract vehicle data
            vehicles = self._extract_vehicles(response.text)
            
            logger.info(f"Found {len(vehicles)} Honda Insight listings")
            return vehicles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Row52 page: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
            return []
    
    def _extract_vehicles(self, html_content: str) -> List[Vehicle]:
        """Extract vehicle data from HTML content."""
        vehicles = []
        
        # Honda Insight VIN patterns (starts with JHMZE)
        vin_pattern = r'JHMZE[A-HJ-NPR-Z0-9]{12}'
        found_vins = re.findall(vin_pattern, html_content)
        
        # Remove duplicates while preserving order
        unique_vins = list(dict.fromkeys(found_vins))
        
        logger.info(f"Found {len(found_vins)} VINs total, {len(unique_vins)} unique Honda Insight VINs")
        
        for vin in unique_vins:
            # Validate VIN before processing
            if not self._is_valid_honda_insight_vin(vin):
                logger.warning(f"Invalid Honda Insight VIN found: {vin}")
                continue
                
            vehicle = self._extract_vehicle_details(vin, html_content)
            if vehicle:
                vehicles.append(vehicle)
        
        return vehicles
    
    def _expand_truncated_location(self, location: str) -> str:
        """Expand truncated location names to their full names."""
        truncation_mapping = {
            'Arlingto': 'Arlington',
            'Vancouve': 'Vancouver',
            'Fairfiel': 'Fairfield',
            'Rancho C': 'Rancho Cordova',
            'Sacram': 'Sacramento',
            'Portlan': 'Portland',
            'Seattl': 'Seattle'
        }
        
        return truncation_mapping.get(location, location)
    
    def _extract_vehicle_details(self, vin: str, html_content: str) -> Optional[Vehicle]:
        """Extract detailed information for a specific VIN."""
        try:
            # Create a large context window around the VIN
            context_pattern = f'.{{0,1000}}{re.escape(vin)}.{{0,1000}}'
            matches = re.findall(context_pattern, html_content, re.DOTALL)
            
            if not matches:
                logger.warning(f"No context found for VIN: {vin}")
                return None
            
            context = matches[0]
            
            # Extract year from VIN (10th character indicates year)
            year = self._decode_year_from_vin(vin)
            
            # Extract location information
            location_patterns = [
                # Exact full city names (keep existing)
                r'(Fresno|Arlington|Tacoma|Vancouver|Fairfield|Rancho Cordova|Sacramento|Portland|Seattle|San Francisco)',
                # Partial city names (handle truncation)
                r'(Arlingto|Vancouve|Fairfiel|Rancho C|Sacram|Portlan|Seattl)',
                # Generic city patterns
                r'([A-Z][a-z]{4,})\s*(?:,\s*[A-Z]{2})?',  # City names with optional state
                r'([A-Z][a-z]+,\s*[A-Z]{2})'  # City, State format
            ]
            
            location = None
            for pattern in location_patterns:
                location_match = re.search(pattern, context)
                if location_match:
                    location = location_match.group(1)
                    # Expand truncated location names
                    location = self._expand_truncated_location(location)
                    break
            
            # Extract yard information
            yard_patterns = [
                r'PICK-n-PULL\s+([A-Za-z\s]+)',
                r'(PICK-n-PULL\s+[A-Za-z\s]+)',
                # Handle truncated yard names
                r'(Arlingto|Vancouve|Fairfiel|Rancho C|Sacram|Portlan|Seattl|Fresno|Tacoma)'
            ]
            
            yard = None
            for pattern in yard_patterns:
                yard_match = re.search(pattern, context)
                if yard_match:
                    yard = yard_match.group(1).strip()
                    # Expand truncated yard names
                    yard = self._expand_truncated_location(yard)
                    break
            
            # Extract row information
            row_match = re.search(r'Row\s*(\d+)', context)
            row = row_match.group(1) if row_match else None
            
            # Extract date information
            date_patterns = [
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}',
                r'\d{1,2}\/\d{1,2}\/\d{4}',
                r'\d{4}-\d{2}-\d{2}'
            ]
            
            date_added = None
            for pattern in date_patterns:
                date_match = re.search(pattern, context)
                if date_match:
                    date_added = date_match.group(0)
                    break
            
            # Create vehicle object
            vehicle = Vehicle(
                vin=vin,
                year=year,
                make="Honda",
                model="Insight",
                location=location,
                yard=yard,
                row=row,
                date_added=date_added,
                source_url=self.search_url
            )
            
            logger.debug(f"Extracted vehicle: {vehicle}")
            return vehicle
            
        except Exception as e:
            logger.error(f"Error extracting details for VIN {vin}: {e}")
            return None
    
    def _decode_year_from_vin(self, vin: str) -> Optional[str]:
        """Decode year from VIN (10th character)."""
        if len(vin) < 10:
            return None
        
        year_char = vin[9]  # 10th character (0-indexed)
        
        # Year encoding for 2000-2006
        year_mapping = {
            'Y': '2000',
            '1': '2001',
            '2': '2002',
            '3': '2003',
            '4': '2004',
            '5': '2005',
            '6': '2006'
        }
        
        decoded_year = year_mapping.get(year_char)
        logger.debug(f"VIN {vin} -> Year char: {year_char} -> Year: {decoded_year}")
        return decoded_year
    
    def get_vehicle_details_url(self, vin: str) -> str:
        """Get detailed URL for a specific vehicle."""
        return f"{self.base_url}/Vehicle/{vin}"
    
    def scrape_detailed_listing(self, vin: str) -> Optional[Dict]:
        """Scrape detailed information for a specific vehicle."""
        detail_url = self.get_vehicle_details_url(vin)
        
        try:
            response = requests.get(detail_url, headers=self.headers)
            response.raise_for_status()
            
            # Parse additional details from vehicle detail page
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract additional information if available
            details = {
                'detail_url': detail_url,
                'additional_info': self._extract_additional_details(soup)
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error fetching detailed listing for VIN {vin}: {e}")
            return None
    
    def _extract_additional_details(self, soup: BeautifulSoup) -> Dict:
        """Extract additional details from vehicle detail page."""
        details = {}
        
        # This would be implemented based on the specific structure
        # of the Row52 vehicle detail pages
        # For now, return empty dict
        
        return details

# Usage example
if __name__ == "__main__":
    scraper = Row52Scraper()
    vehicles = scraper.scrape_listings()
    
    print(f"Found {len(vehicles)} Honda Insight listings:")
    for vehicle in vehicles:
        print(f"  {vehicle.year} {vehicle.make} {vehicle.model} - VIN: {vehicle.vin}")
        if vehicle.location:
            print(f"    Location: {vehicle.location}")
        if vehicle.row:
            print(f"    Row: {vehicle.row}")
        if vehicle.date_added:
            print(f"    Date Added: {vehicle.date_added}")
        print() 