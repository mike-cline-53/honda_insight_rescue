#!/usr/bin/env python3

import re
from bs4 import BeautifulSoup
from typing import List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base_scraper import BaseScraper, Vehicle

logger = logging.getLogger(__name__)

class CarPartScraper(BaseScraper):
    """Scraper for Car-Part.com Honda Insight listings."""
    
    def __init__(self):
        super().__init__("Car-Part.com")
        self.base_url = "https://car-part.com/cgi-bin/search.cgi"
        self.search_url = "https://car-part.com/cgi-bin/search.cgi"
        
    def scrape_listings(self) -> List[Vehicle]:
        """Scrape Honda Insight listings from Car-Part.com."""
        logger.info("Starting Car-Part.com scraping for Honda Insight")
        
        # First get the search page
        response = self._make_request(self.search_url)
        if not response:
            return []
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to submit searches for Honda Insight across multiple years
            all_vehicles = []
            
            # Search for each year in parallel as Car-Part.com can be picky about search parameters
            years = ['1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006']
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Submit all year searches
                future_to_year = {
                    executor.submit(self._search_for_year, soup, year): year
                    for year in years
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_year):
                    year = future_to_year[future]
                    try:
                        vehicles = future.result()
                        all_vehicles.extend(vehicles)
                        if vehicles:
                            logger.info(f"Found {len(vehicles)} vehicles for year {year}")
                    except Exception as e:
                        logger.error(f"Error searching for year {year}: {e}")
                        continue
            
            logger.info(f"Found {len(all_vehicles)} Honda Insight listings on Car-Part.com")
            return all_vehicles
            
        except Exception as e:
            logger.error(f"Error parsing Car-Part.com page: {e}")
            return []
    
    def _search_for_year(self, soup: BeautifulSoup, year: str) -> List[Vehicle]:
        """Submit a search for Honda Insight vehicles for a specific year."""
        try:
            # Car-Part.com has a complex search form, try multiple approaches
            search_form = soup.find('form')
            
            if search_form:
                # Try to extract form action and method
                action = search_form.get('action', '')
                method = search_form.get('method', 'get').lower()
                
                # Build search URL
                if action:
                    search_url = action if action.startswith('http') else f"https://car-part.com{action}"
                else:
                    search_url = self.search_url
                
                # Car-Part.com specific search parameters
                form_data = {
                    'make': 'Honda',
                    'model': 'Insight',
                    'year': year,
                    'part': '',  # Search for any part
                    'yearend': year,
                    'userLocation': '',
                    'userRadius': '500',  # Search within 500 miles
                    'userZip': '10001',   # Default ZIP code
                    'color': '',
                    'miles': '',
                    'price': '',
                    'pricelow': '',
                    'pricehigh': '',
                    'description': '',
                    'sort': 'distance',
                    'new': 'N',
                    'used': 'Y',
                    'interchange': 'Y'
                }
                
                # Look for actual form fields and update accordingly
                inputs = search_form.find_all('input')
                selects = search_form.find_all('select')
                
                # Process select fields
                for select in selects:
                    field_name = select.get('name', '')
                    if field_name:
                        options = select.find_all('option')
                        for option in options:
                            option_value = option.get('value', '')
                            option_text = option.get_text().strip().lower()
                            
                            if 'make' in field_name.lower() and 'honda' in option_text:
                                form_data[field_name] = option_value
                            elif 'model' in field_name.lower() and 'insight' in option_text:
                                form_data[field_name] = option_value
                            elif 'year' in field_name.lower() and option_value == year:
                                form_data[field_name] = option_value
                
                # Process input fields
                for input_field in inputs:
                    field_name = input_field.get('name', '')
                    field_type = input_field.get('type', 'text')
                    
                    if field_name and field_type not in ['submit', 'button']:
                        if field_name in form_data:
                            continue  # Already set
                        elif 'make' in field_name.lower():
                            form_data[field_name] = 'Honda'
                        elif 'model' in field_name.lower():
                            form_data[field_name] = 'Insight'
                        elif 'year' in field_name.lower():
                            form_data[field_name] = year
                
                # Submit the search
                if method == 'post':
                    response = self._make_request(search_url, data=form_data)
                else:
                    response = self._make_request(search_url, params=form_data)
                
                if response:
                    return self._parse_search_results(response.text, BeautifulSoup(response.text, 'html.parser'))
            
            return []
            
        except Exception as e:
            logger.error(f"Error submitting search to Car-Part.com for year {year}: {e}")
            return []
    
    def _parse_search_results(self, html_content: str, soup: BeautifulSoup) -> List[Vehicle]:
        """Parse search results for Honda Insight listings."""
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
            
            # Extract location - Car-Part.com shows salvage yard locations
            location = self._extract_carpart_location(context)
            
            # Extract yard/facility information
            yard = self._extract_yard_info(context)
            
            # Extract date information
            date_added = self._extract_date_from_context(context)
            
            # Extract price if available
            price = self._extract_price_from_context(context)
            
            # Extract contact information
            contact_info = self._extract_contact_info(context)
            
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
                price=price,
                contact_info=contact_info
            )
            
            logger.debug(f"Extracted vehicle: {vehicle}")
            return vehicle
            
        except Exception as e:
            logger.error(f"Error extracting details for VIN {vin}: {e}")
            return None
    
    def _extract_carpart_location(self, context: str) -> Optional[str]:
        """Extract location information from Car-Part.com listings."""
        carpart_patterns = [
            r'([A-Z][a-z]+,\s*[A-Z]{2}\s+\d{5})',  # City, State ZIP
            r'([A-Z][a-z]+,\s*[A-Z]{2})',          # City, State
            r'Location\s*:?\s*([A-Za-z\s,]+)',
            r'Address\s*:?\s*([A-Za-z\s,]+)'
        ]
        
        for pattern in carpart_patterns:
            location_match = re.search(pattern, context, re.IGNORECASE)
            if location_match:
                return location_match.group(1).strip()
        
        # Fallback to generic location extraction
        return self._extract_location_from_context(context)
    
    def _extract_yard_info(self, context: str) -> Optional[str]:
        """Extract yard/facility information."""
        yard_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Auto\s+Parts)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Salvage)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Recycling)',
            r'Yard\s*:?\s*([A-Za-z0-9\s]+)'
        ]
        
        for pattern in yard_patterns:
            yard_match = re.search(pattern, context, re.IGNORECASE)
            if yard_match:
                return yard_match.group(1).strip()
        
        return None
    
    def _extract_contact_info(self, context: str) -> Optional[str]:
        """Extract contact information from Car-Part.com listings."""
        contact_patterns = [
            r'(\(\d{3}\)\s*\d{3}-\d{4})',  # Phone numbers
            r'(\d{3}-\d{3}-\d{4})',
            r'(\d{3}\.\d{3}\.\d{4})',
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'  # Email addresses
        ]
        
        for pattern in contact_patterns:
            contact_match = re.search(pattern, context)
            if contact_match:
                return contact_match.group(1).strip()
        
        return None 