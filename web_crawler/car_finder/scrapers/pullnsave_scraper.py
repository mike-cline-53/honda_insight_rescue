#!/usr/bin/env python3

import re
from bs4 import BeautifulSoup
from typing import List, Optional
import logging
from .base_scraper import BaseScraper, Vehicle

logger = logging.getLogger(__name__)

class PullNSaveScraper(BaseScraper):
    """Scraper for Pull-N-Save Honda Insight listings."""
    
    def __init__(self):
        super().__init__("Pull-N-Save")
        self.base_url = "https://www.pullnsave.com/inventory/"
        self.search_url = "https://www.pullnsave.com/inventory/"
        
    def scrape_listings(self) -> List[Vehicle]:
        """Scrape Honda Insight listings from Pull-N-Save."""
        logger.info("Starting Pull-N-Save scraping for Honda Insight")
        
        # First get the search page
        response = self._make_request(self.search_url)
        if not response:
            return []
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to submit a search for Honda Insight
            vehicles = self._search_for_insights(soup)
            
            logger.info(f"Found {len(vehicles)} Honda Insight listings on Pull-N-Save")
            return vehicles
            
        except Exception as e:
            logger.error(f"Error parsing Pull-N-Save page: {e}")
            return []
    
    def _search_for_insights(self, soup: BeautifulSoup) -> List[Vehicle]:
        """Submit a search for Honda Insight vehicles."""
        try:
            # Look for the search form
            search_form = soup.find('form')
            
            if search_form:
                # Try to extract form action and method
                action = search_form.get('action', '')
                method = search_form.get('method', 'get').lower()
                
                # Build search URL
                if action:
                    search_url = action if action.startswith('http') else f"https://www.pullnsave.com{action}"
                else:
                    search_url = self.search_url
                
                form_data = {}
                
                # Look for dropdown select fields for make and model
                selects = search_form.find_all('select')
                
                for select in selects:
                    field_name = select.get('name', '')
                    if field_name:
                        options = select.find_all('option')
                        for option in options:
                            option_value = option.get('value', '')
                            option_text = option.get_text().strip().lower()
                            
                            # Look for Honda in make dropdown
                            if 'make' in field_name.lower():
                                if 'honda' in option_text:
                                    form_data[field_name] = option_value
                                    break
                            # Look for Insight in model dropdown
                            elif 'model' in field_name.lower():
                                if 'insight' in option_text:
                                    form_data[field_name] = option_value
                                    break
                            # Look for year dropdowns (1999-2006)
                            elif 'year' in field_name.lower():
                                if option_value in ['1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006']:
                                    form_data[field_name] = option_value
                                    break
                
                # Look for input fields
                inputs = search_form.find_all('input')
                for input_field in inputs:
                    field_name = input_field.get('name', '')
                    field_type = input_field.get('type', 'text')
                    
                    if field_name and field_type not in ['submit', 'button']:
                        if 'make' in field_name.lower():
                            form_data[field_name] = 'Honda'
                        elif 'model' in field_name.lower():
                            form_data[field_name] = 'Insight'
                        elif 'search' in field_name.lower():
                            form_data[field_name] = 'Honda Insight'
                
                # Submit the search
                if method == 'post':
                    response = self._make_request(search_url, data=form_data)
                else:
                    response = self._make_request(search_url, params=form_data)
                
                if response:
                    return self._parse_search_results(response.text, BeautifulSoup(response.text, 'html.parser'))
            
            # If no form found, parse current page
            return self._parse_search_results(str(soup), soup)
            
        except Exception as e:
            logger.error(f"Error submitting search to Pull-N-Save: {e}")
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
            
            # Extract location - Pull-N-Save locations
            location = self._extract_pullnsave_location(context)
            
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
    
    def _extract_pullnsave_location(self, context: str) -> Optional[str]:
        """Extract location information specific to Pull-N-Save."""
        pullnsave_patterns = [
            r'Pull-N-Save\s*-?\s*([A-Za-z\s]+)',
            r'Pull\s*N\s*Save\s*-?\s*([A-Za-z\s]+)',
            r'Location\s*:?\s*([A-Za-z\s,]+)',
            r'Address\s*:?\s*([A-Za-z\s,]+)'
        ]
        
        for pattern in pullnsave_patterns:
            location_match = re.search(pattern, context, re.IGNORECASE)
            if location_match:
                return location_match.group(1).strip()
        
        # Fallback to generic location extraction
        return self._extract_location_from_context(context)
    
    def _extract_yard_info(self, context: str) -> Optional[str]:
        """Extract yard/facility information."""
        yard_patterns = [
            r'Pull-N-Save\s*-?\s*([A-Za-z\s]+)',
            r'(Pull-N-Save)',
            r'(Pull\s*N\s*Save)',
            r'Yard\s*:?\s*([A-Za-z0-9\s]+)'
        ]
        
        for pattern in yard_patterns:
            yard_match = re.search(pattern, context, re.IGNORECASE)
            if yard_match:
                return yard_match.group(1).strip()
        
        return "Pull-N-Save" 