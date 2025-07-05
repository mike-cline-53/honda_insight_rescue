#!/usr/bin/env python3

import re
from bs4 import BeautifulSoup
from typing import List, Optional
import logging
from .base_scraper import BaseScraper, Vehicle

logger = logging.getLogger(__name__)

class UPullMScraper(BaseScraper):
    """Scraper for U-Pull-M Honda Insight listings."""
    
    def __init__(self):
        super().__init__("U-Pull-M")
        self.base_url = "https://route34upullm.com/inventory/"
        self.search_url = "https://route34upullm.com/inventory/"
        
    def scrape_listings(self) -> List[Vehicle]:
        """Scrape Honda Insight listings from U-Pull-M."""
        logger.info("Starting U-Pull-M scraping for Honda Insight")
        
        # First get the search page
        response = self._make_request(self.search_url)
        if not response:
            return []
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for a search form
            search_form = soup.find('form') or soup.find('input', {'type': 'search'})
            
            if search_form:
                # Try to submit a search for 'insight'
                vehicles = self._search_for_insights(soup)
            else:
                # If no search form, just parse the current page
                vehicles = self._parse_current_page(response.text, soup)
            
            logger.info(f"Found {len(vehicles)} Honda Insight listings on U-Pull-M")
            return vehicles
            
        except Exception as e:
            logger.error(f"Error parsing U-Pull-M page: {e}")
            return []
    
    def _search_for_insights(self, soup: BeautifulSoup) -> List[Vehicle]:
        """Submit a search for Honda Insight vehicles."""
        try:
            # Look for search forms or input fields
            search_inputs = soup.find_all('input', {'type': ['search', 'text']})
            
            if not search_inputs:
                logger.warning("No search inputs found, parsing current page")
                return self._parse_current_page(str(soup), soup)
            
            # Try to submit a POST request with search terms
            search_data = {
                'search': 'insight',
                'q': 'honda insight',
                'query': 'insight',
                'make': 'honda',
                'model': 'insight'
            }
            
            # Try different common search parameter names
            for input_field in search_inputs:
                field_name = input_field.get('name', '')
                if field_name:
                    search_data[field_name] = 'insight'
            
            # Submit the search
            response = self._make_request(self.search_url, data=search_data)
            if response:
                return self._parse_current_page(response.text, BeautifulSoup(response.text, 'html.parser'))
            
        except Exception as e:
            logger.error(f"Error submitting search: {e}")
        
        return []
    
    def _parse_current_page(self, html_content: str, soup: BeautifulSoup) -> List[Vehicle]:
        """Parse the current page for Honda Insight listings."""
        vehicles = []
        
        # Extract VINs from the page
        vins = self._extract_honda_insight_vins(html_content)
        
        for vin in vins:
            vehicle = self._extract_vehicle_details(vin, html_content, soup)
            if vehicle:
                vehicles.append(vehicle)
        
        return vehicles
    
    def _extract_vehicle_details(self, vin: str, html_content: str, soup: BeautifulSoup) -> Optional[Vehicle]:
        """Extract detailed information for a specific VIN."""
        try:
            # Create a large context window around the VIN
            context_pattern = f'.{{0,1000}}{re.escape(vin)}.{{0,1000}}'
            matches = re.findall(context_pattern, html_content, re.DOTALL)
            
            if not matches:
                logger.warning(f"No context found for VIN: {vin}")
                return None
            
            context = matches[0]
            
            # Extract year from VIN
            year = self._decode_year_from_vin(vin)
            
            # Extract location - U-Pull-M location
            location = self._extract_upullm_location(context)
            
            # Extract yard/facility information
            yard = self._extract_yard_info(context)
            
            # Extract date information
            date_added = self._extract_date_from_context(context)
            
            # Extract price if available
            price = self._extract_price_from_context(context)
            
            # Create vehicle object
            vehicle = Vehicle(
                vin=vin,
                year=year,
                make="Honda",
                model="Insight",
                location=location,
                yard=yard,
                date_added=date_added,
                source_url=self.search_url,
                price=price
            )
            
            logger.debug(f"Extracted vehicle: {vehicle}")
            return vehicle
            
        except Exception as e:
            logger.error(f"Error extracting details for VIN {vin}: {e}")
            return None
    
    def _extract_upullm_location(self, context: str) -> Optional[str]:
        """Extract location information specific to U-Pull-M."""
        # U-Pull-M is Route 34 U-Pull-M, likely in Connecticut/New York area
        upullm_patterns = [
            r'Route\s*34\s*U-Pull-M\s*-?\s*([A-Za-z\s]+)',
            r'U-Pull-M\s*-?\s*([A-Za-z\s]+)',
            r'Location\s*:?\s*([A-Za-z\s,]+)',
            r'Address\s*:?\s*([A-Za-z\s,]+)'
        ]
        
        for pattern in upullm_patterns:
            location_match = re.search(pattern, context, re.IGNORECASE)
            if location_match:
                return location_match.group(1).strip()
        
        # Default to Route 34 area (Connecticut)
        if 'route 34' in context.lower():
            return "Route 34, CT"
        
        # Fallback to generic location extraction
        return self._extract_location_from_context(context)
    
    def _extract_yard_info(self, context: str) -> Optional[str]:
        """Extract yard/facility information."""
        yard_patterns = [
            r'Route\s*34\s*U-Pull-M\s*-?\s*([A-Za-z\s]+)',
            r'(Route\s*34\s*U-Pull-M)',
            r'(U-Pull-M)',
            r'Yard\s*:?\s*([A-Za-z0-9\s]+)'
        ]
        
        for pattern in yard_patterns:
            yard_match = re.search(pattern, context, re.IGNORECASE)
            if yard_match:
                return yard_match.group(1).strip()
        
        return "Route 34 U-Pull-M" 