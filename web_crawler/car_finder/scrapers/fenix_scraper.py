#!/usr/bin/env python3

import re
from bs4 import BeautifulSoup
from typing import List, Optional
import logging
from .base_scraper import BaseScraper, Vehicle

logger = logging.getLogger(__name__)

class FenixScraper(BaseScraper):
    """Scraper for Fenix U Pull Honda Insight listings."""
    
    def __init__(self):
        super().__init__("Fenix U Pull")
        self.search_url = "https://fenixupull.com/inventory/?location=elmira-ny%2Cbinghamton-ny%2Ceast-syracuse-ny%2Cmoultrie-ga&make=HONDA&model=INSIGHT"
        
    def scrape_listings(self) -> List[Vehicle]:
        """Scrape Honda Insight listings from Fenix U Pull."""
        logger.info("Starting Fenix U Pull scraping for Honda Insight")
        
        response = self._make_request(self.search_url)
        if not response:
            return []
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            vehicles = []
            
            # Extract VINs from the page
            vins = self._extract_honda_insight_vins(response.text)
            
            for vin in vins:
                vehicle = self._extract_vehicle_details(vin, response.text, soup)
                if vehicle:
                    vehicles.append(vehicle)
            
            logger.info(f"Found {len(vehicles)} Honda Insight listings on Fenix U Pull")
            return vehicles
            
        except Exception as e:
            logger.error(f"Error parsing Fenix U Pull page: {e}")
            return []
    
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
            
            # Extract location - Fenix has specific locations
            location = self._extract_fenix_location(context)
            
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
    
    def _extract_fenix_location(self, context: str) -> Optional[str]:
        """Extract location information specific to Fenix locations."""
        # Known Fenix locations from the URL
        fenix_locations = [
            'Elmira, NY',
            'Binghamton, NY', 
            'East Syracuse, NY',
            'Moultrie, GA'
        ]
        
        for location in fenix_locations:
            if location.lower() in context.lower():
                return location
        
        # Fallback to generic location extraction
        return self._extract_location_from_context(context)
    
    def _extract_yard_info(self, context: str) -> Optional[str]:
        """Extract yard/facility information."""
        yard_patterns = [
            r'Fenix\s+U\s+Pull\s*-?\s*([A-Za-z\s]+)',
            r'(Fenix\s+U\s+Pull)',
            r'Yard\s*:?\s*([A-Za-z0-9\s]+)',
            r'Location\s*:?\s*([A-Za-z\s]+)'
        ]
        
        for pattern in yard_patterns:
            yard_match = re.search(pattern, context, re.IGNORECASE)
            if yard_match:
                return yard_match.group(1).strip()
        
        return "Fenix U Pull" 