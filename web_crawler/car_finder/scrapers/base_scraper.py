#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Vehicle:
    """Data class for vehicle listings."""
    vin: str  # Can be either a VIN or internal ID
    year: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    yard: Optional[str] = None
    row: Optional[str] = None
    date_added: Optional[str] = None
    source_url: Optional[str] = None
    price: Optional[str] = None
    contact_info: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'vin': self.vin,  # Keep as 'vin' for backward compatibility
            'year': self.year,
            'make': self.make,
            'model': self.model,
            'location': self.location,
            'yard': self.yard,
            'row': self.row,
            'date_added': self.date_added,
            'source_url': self.source_url,
            'price': self.price,
            'contact_info': self.contact_info,
            'scraped_at': datetime.now().isoformat()
        }

class BaseScraper(ABC):
    """Simplified base class for all scrapers - no VIN verification required."""
    
    def __init__(self, name: str, target_make: str = "HONDA", target_model: str = "INSIGHT"):
        self.name = name
        self.target_make = target_make
        self.target_model = target_model
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Create a session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    @abstractmethod
    def scrape_listings(self) -> List[Vehicle]:
        """Scrape vehicle listings. Must be implemented by subclasses."""
        pass
    
    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with error handling using session for connection pooling."""
        try:
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            logger.info(f"Successfully fetched {url}. Status: {response.status_code}")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def close_session(self):
        """Close the session to free up connections."""
        if hasattr(self, 'session'):
            self.session.close()
    
    def _is_valid_vin(self, vin: str) -> bool:
        """
        Validate if a VIN is properly formatted.
        
        Args:
            vin: VIN string to validate
            
        Returns:
            bool: True if VIN is valid, False otherwise
        """
        if not vin or not isinstance(vin, str):
            return False
            
        # Remove whitespace
        vin = vin.strip()
        
        # Check length (must be 17 characters)
        if len(vin) != 17:
            return False
            
        # Check if all characters are alphanumeric
        if not vin.isalnum():
            return False
            
        # Check for invalid characters (I, O, Q are not allowed in VINs)
        invalid_chars = set('IOQ')
        if any(char in invalid_chars for char in vin.upper()):
            return False
            
        # For Honda Insight, VIN should start with JHMZE
        if vin.upper().startswith('JHMZE'):
            return True
            
        # Accept other valid VIN patterns but log a warning
        logger.warning(f"VIN {vin} doesn't match Honda Insight pattern but appears valid")
        return True
    
    def _is_valid_honda_insight_vin(self, vin: str) -> bool:
        """
        Validate if a VIN is specifically for a Honda Insight.
        
        Args:
            vin: VIN string to validate
            
        Returns:
            bool: True if VIN is valid Honda Insight VIN, False otherwise
        """
        if not self._is_valid_vin(vin):
            return False
            
        # Honda Insight VINs should start with JHMZE
        return vin.upper().startswith('JHMZE')
    
    def _clean_price(self, price: str) -> Optional[str]:
        """
        Clean and validate price data.
        
        Args:
            price: Raw price string
            
        Returns:
            str: Cleaned price string or None if invalid
        """
        if not price or not isinstance(price, str):
            return None
            
        # Remove extra whitespace and newlines
        price = price.strip().replace('\n', ' ').replace('\r', '')
        
        # Remove obvious corrupted data patterns
        corrupted_patterns = [
            r'\d+kg',  # Weight data mixed in
            r'\d+\.\d+\s*hrs',  # Time data mixed in
            r'\s+\d+kg\s*$',  # Weight at end
            r'^\s*[A-Z]\s*$',  # Single letters
            r'^\s*[A-Z]\s*\d+\s*$',  # Single letter followed by number
        ]
        
        for pattern in corrupted_patterns:
            price = re.sub(pattern, '', price, flags=re.IGNORECASE)
        
        price = price.strip()
        
        # If empty after cleaning, return None
        if not price:
            return None
            
        # If it contains multiple price-like patterns, take the first valid one
        price_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # $1,234.56
            r'\$\d+(?:-\d+)?',  # $100 or $100-200
            r'\d+(?:,\d{3})*(?:\.\d{2})?\s*\$',  # 1234.56$
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, price)
            if match:
                return match.group(0)
        
        # If it's a common valid non-numeric price, keep it
        valid_non_numeric = ['Call', 'Contact', 'See website', 'N/A', 'TBD', 'Ask']
        for valid_price in valid_non_numeric:
            if valid_price.lower() in price.lower():
                return valid_price
        
        # If price looks corrupted, return None
        if len(price) > 50 or re.search(r'[^\w\s\$\.,\-]', price):
            logger.warning(f"Corrupted price data detected: {price}")
            return None
            
        return price

    def _clean_yard(self, yard: str) -> Optional[str]:
        """
        Clean and validate yard/business name data.
        
        Args:
            yard: Raw yard string
            
        Returns:
            str: Cleaned yard string or None if invalid
        """
        if not yard or not isinstance(yard, str):
            return None
            
        # Remove extra whitespace and newlines
        yard = yard.strip().replace('\n', ' ').replace('\r', '')
        
        # Remove obvious corrupted data patterns
        corrupted_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Price data mixed in
            r'\d+kg',  # Weight data mixed in
            r'\d+\.\d+\s*hrs',  # Time data mixed in
            r'^\s*[A-Z]\s*\d*\s*$',  # Single letters with optional numbers
        ]
        
        for pattern in corrupted_patterns:
            yard = re.sub(pattern, '', yard, flags=re.IGNORECASE)
        
        yard = yard.strip()
        
        # If empty after cleaning, return None
        if not yard:
            return None
            
        # If it's obviously a price, return None
        if yard.startswith('$') or yard.endswith('$'):
            logger.warning(f"Price data found in yard field: {yard}")
            return None
            
        # If yard name is too short or contains mostly numbers, likely corrupted
        if len(yard) < 3 or re.search(r'^\d+$', yard):
            logger.warning(f"Corrupted yard data detected: {yard}")
            return None
            
        return yard

    def _clean_location(self, location: str) -> Optional[str]:
        """
        Clean and validate location data.
        
        Args:
            location: Raw location string
            
        Returns:
            str: Cleaned location string or None if invalid
        """
        if not location or not isinstance(location, str):
            return None
            
        # Remove extra whitespace and newlines
        location = location.strip().replace('\n', ' ').replace('\r', '')
        
        # Remove obvious corrupted data patterns
        corrupted_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Price data mixed in
            r'\d+kg',  # Weight data mixed in
            r'\d+\.\d+\s*hrs',  # Time data mixed in
        ]
        
        for pattern in corrupted_patterns:
            location = re.sub(pattern, '', location, flags=re.IGNORECASE)
        
        location = location.strip()
        
        # If empty after cleaning, return None
        if not location:
            return None
            
        # If location is too short, likely corrupted
        if len(location) < 2:
            logger.warning(f"Corrupted location data detected: {location}")
            return None
            
        return location

    def _extract_vehicle_info_from_listing(self, listing_element, source_url: str) -> Optional[Vehicle]:
        """
        Extract vehicle information from a listing element.
        This is a simplified approach that looks for any vehicle information.
        """
        try:
            # Look for any VIN-like patterns (17 characters, alphanumeric)
            vin_pattern = r'[A-HJ-NPR-Z0-9]{17}'
            text_content = listing_element.get_text() if listing_element else ""
            
            # Find potential VINs
            potential_vins = re.findall(vin_pattern, text_content)
            vin = potential_vins[0] if potential_vins else "VIN_NOT_FOUND"
            
            # Extract year (look for 4-digit years)
            year_match = re.search(r'\b(19|20)\d{2}\b', text_content)
            year = year_match.group(0) if year_match else None
            
            # Extract location information
            location = self._clean_location(self._extract_location_from_context(text_content))
            
            # Extract date information
            date_added = self._extract_date_from_context(text_content)
            
            # Extract price information
            price = self._clean_price(self._extract_price_from_context(text_content))
            
            # Create vehicle object
            vehicle = Vehicle(
                vin=vin,
                year=year,
                make=self.target_make,
                model=self.target_model,
                location=location,
                date_added=date_added,
                source_url=source_url,
                price=price
            )
            
            logger.info(f"Found vehicle: {year} {self.target_make} {self.target_model} - VIN: {vin}")
            return vehicle
            
        except Exception as e:
            logger.error(f"Error extracting vehicle info: {e}")
            return None
    
    def _extract_all_listings_from_page(self, html_content: str, source_url: str) -> List[Vehicle]:
        """
        Extract all vehicle listings from a page.
        This method looks for common listing patterns.
        """
        vehicles = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Common selectors for vehicle listings
            listing_selectors = [
                '.vehicle-listing',
                '.listing',
                '.vehicle',
                '.inventory-item',
                '.part-listing',
                '.result',
                '.item',
                'tr',  # Table rows
                '.car-listing'
            ]
            
            for selector in listing_selectors:
                listings = soup.select(selector)
                if listings:
                    logger.info(f"Found {len(listings)} potential listings using selector: {selector}")
                    
                    for listing in listings:
                        vehicle = self._extract_vehicle_info_from_listing(listing, source_url)
                        if vehicle:
                            vehicles.append(vehicle)
                    
                    # If we found vehicles with this selector, stop trying others
                    if vehicles:
                        break
            
            # If no structured listings found, try to extract from any text that mentions years
            if not vehicles:
                # Look for any mention of target years
                target_years = ['1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006']
                for year in target_years:
                    if year in html_content:
                        # Create a generic vehicle entry
                        vehicle = Vehicle(
                            vin="VIN_NOT_DISPLAYED",
                            year=year,
                            make=self.target_make,
                            model=self.target_model,
                            source_url=source_url
                        )
                        vehicles.append(vehicle)
                        logger.info(f"Found mention of {year} {self.target_make} {self.target_model}")
                        break  # Only add one per page to avoid duplicates
            
            logger.info(f"Extracted {len(vehicles)} vehicles from page")
            return vehicles
            
        except Exception as e:
            logger.error(f"Error parsing page content: {e}")
            return []
    
    def _extract_location_from_context(self, context: str) -> Optional[str]:
        """Extract location information from context."""
        location_patterns = [
            r'([A-Z][a-z]+,\s*[A-Z]{2})',  # City, State format
            r'([A-Z][a-z]+\s+[A-Z]{2})',   # City State format
            r'([A-Z]{2}\s+\d{5})',         # State ZIP format
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, context)
            if location_match:
                return location_match.group(1).strip()
        
        return None
    
    def _extract_date_from_context(self, context: str) -> Optional[str]:
        """Extract date information from context."""
        date_patterns = [
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}',
            r'\d{1,2}\/\d{1,2}\/\d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}-\d{1,2}-\d{4}'
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, context)
            if date_match:
                return date_match.group(0)
        
        return None
    
    def _extract_price_from_context(self, context: str) -> Optional[str]:
        """Extract price information from context."""
        price_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
            r'\$\d+(?:\.\d{2})?',
            r'Price:\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, context)
            if price_match:
                return price_match.group(0)
        
        return None 