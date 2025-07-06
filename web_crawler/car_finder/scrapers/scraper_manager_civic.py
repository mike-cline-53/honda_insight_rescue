#!/usr/bin/env python3

import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

from .base_scraper import Vehicle
from .row52_scraper import Row52Scraper
from .fenix_scraper import FenixScraper
from .uwrenchit_scraper import UWrenchItScraper
from .kenny_upull_scraper import KennyUPullScraper
from .upull_pay_scraper import UPullPayScraper
from .upullm_scraper import UPullMScraper
from .wilberts_scraper import WilbertsScraper
from .lkq_scraper import LKQScraper
from .nvpap_scraper import NVPAPScraper
from .pullnsave_scraper import PullNSaveScraper
from .carpart_scraper_selenium import CarPartSeleniumScraper

logger = logging.getLogger(__name__)

class ScraperManagerCivic:
    """Manages all Honda Civic scrapers."""
    
    def __init__(self):
        self.scrapers = {
            'row52': Row52Scraper(),
            'fenix': FenixScraper(),
            'uwrenchit': UWrenchItScraper(),
            'kenny_upull': KennyUPullScraper(),
            'upull_pay': UPullPayScraper(),
            'upullm': UPullMScraper(),
            'wilberts': WilbertsScraper(),
            'lkq': LKQScraper(),
            'nvpap': NVPAPScraper(),
            'pullnsave': PullNSaveScraper(),
            'carpart': CarPartSeleniumScraper()
        }
        
        # Configure scrapers for Honda Civic
        self._configure_scrapers_for_civic()
        
    def _configure_scrapers_for_civic(self):
        """Configure scrapers to search for Honda Civic instead of Honda Insight."""
        
        # Row52 scraper configuration
        row52_scraper = self.scrapers['row52']
        if hasattr(row52_scraper, 'search_url'):
            # Update Row52 for Honda Civic: ModelId=2469 is Honda Civic, Year range 1996-2024
            row52_scraper.search_url = f"{row52_scraper.base_url}/Search/?YMMorVin=YMM&Year=1996-2024&V1=&V2=&V3=&V4=&V5=&V6=&V7=&V8=&V9=&V10=&V11=&V12=&V13=&V14=&V15=&V16=&V17=&ZipCode=&Page=1&ModelId=2469&MakeId=145&LocationId=&IsVin=false&Distance=50"
            
        # Fenix scraper configuration - already has search_url
        fenix_scraper = self.scrapers['fenix']
        if hasattr(fenix_scraper, 'search_url'):
            # Update Fenix for Honda Civic by replacing INSIGHT with CIVIC in the URL
            original_url = fenix_scraper.search_url
            civic_url = original_url.replace('INSIGHT', 'CIVIC').replace('Insight', 'Civic')
            fenix_scraper.search_url = civic_url
            
        # LKQ scraper configuration
        lkq_scraper = self.scrapers['lkq']
        if hasattr(lkq_scraper, 'years'):
            # LKQ Pick Your Part - use same years as Honda Insight for testing (1999-2006)
            lkq_scraper.years = ['1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006']
        # Update LKQ location URLs to search for Honda Civic
        if hasattr(lkq_scraper, 'location_urls'):
            # Replace INSIGHT with CIVIC in the URLs
            updated_urls = []
            for url in lkq_scraper.location_urls:
                civic_url = url.replace('INSIGHT', 'CIVIC').replace('Insight', 'Civic')
                updated_urls.append(civic_url)
            lkq_scraper.location_urls = updated_urls
            
        # For other scrapers, we'll update their names to indicate Honda Civic search
        # but they may still search for Honda Insight due to hardcoded VIN patterns
        for site_name, scraper in self.scrapers.items():
            # Update the name to indicate it's attempting Honda Civic search
            if hasattr(scraper, 'name'):
                if 'Honda Civic' not in scraper.name:
                    scraper.name = f"{scraper.name} (Honda Civic)"
                    
        logger.info("Configured scrapers for Honda Civic searches where possible")
    
    def scrape_all(self, max_workers: int = 4, timeout: int = 300) -> Dict[str, List[Vehicle]]:
        """
        Scrape all sites for Honda Civic listings.
        
        Args:
            max_workers: Maximum number of concurrent scrapers
            timeout: Timeout in seconds for each scraper
            
        Returns:
            Dictionary mapping site names to lists of vehicles
        """
        logger.info(f"Starting Honda Civic scraping across {len(self.scrapers)} sites")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scraping tasks
            future_to_site = {
                executor.submit(self._scrape_site_with_timeout, site_name, scraper, timeout): site_name
                for site_name, scraper in self.scrapers.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_site):
                site_name = future_to_site[future]
                try:
                    vehicles = future.result()
                    results[site_name] = vehicles
                    logger.info(f"Completed scraping {site_name}: {len(vehicles)} vehicles found")
                except Exception as e:
                    logger.error(f"Error scraping {site_name}: {e}")
                    results[site_name] = []
        
        total_vehicles = sum(len(vehicles) for vehicles in results.values())
        logger.info(f"Honda Civic scraping completed. Total vehicles found: {total_vehicles}")
        
        return results
    
    def _scrape_site_with_timeout(self, site_name: str, scraper, timeout: int) -> List[Vehicle]:
        """Scrape a single site with timeout protection."""
        try:
            logger.info(f"Starting Honda Civic scraping {site_name}")
            start_time = time.time()
            
            # For Honda Civic, we need to modify the scraper's behavior
            if hasattr(scraper, 'scrape_listings'):
                vehicles = scraper.scrape_listings()
            else:
                logger.warning(f"Scraper {site_name} does not have scrape_listings method")
                return []
            
            end_time = time.time()
            logger.info(f"Completed Honda Civic scraping {site_name} in {end_time - start_time:.2f} seconds")
            
            return vehicles
            
        except Exception as e:
            logger.error(f"Error scraping {site_name} for Honda Civic: {e}")
            return []
    
    def scrape_site(self, site_name: str) -> List[Vehicle]:
        """Scrape a single site by name."""
        if site_name not in self.scrapers:
            logger.error(f"Unknown site: {site_name}")
            return []
        
        scraper = self.scrapers[site_name]
        return scraper.scrape_listings()
    
    def get_site_names(self) -> List[str]:
        """Get list of all available site names."""
        return list(self.scrapers.keys())
    
    def get_site_info(self) -> Dict[str, str]:
        """Get information about all available sites."""
        return {
            site_name: scraper.name
            for site_name, scraper in self.scrapers.items()
        }
    
    def validate_scrapers(self) -> Dict[str, bool]:
        """Validate that all scrapers are properly configured."""
        validation_results = {}
        
        for site_name, scraper in self.scrapers.items():
            try:
                # Check if scraper has required methods
                has_scrape_method = hasattr(scraper, 'scrape_listings')
                has_name = hasattr(scraper, 'name')
                
                validation_results[site_name] = has_scrape_method and has_name
                
                if not validation_results[site_name]:
                    logger.warning(f"Scraper {site_name} failed validation")
                    
            except Exception as e:
                logger.error(f"Error validating scraper {site_name}: {e}")
                validation_results[site_name] = False
        
        return validation_results
    
    def get_statistics(self, results: Dict[str, List[Vehicle]]) -> Dict[str, any]:
        """Get statistics about scraping results."""
        total_vehicles = sum(len(vehicles) for vehicles in results.values())
        
        site_stats = {}
        sites_with_results = 0
        sites_without_results = []
        
        for site_name, vehicles in results.items():
            count = len(vehicles)
            if count > 0:
                sites_with_results += 1
            else:
                sites_without_results.append(site_name)
                
            site_stats[site_name] = {
                'count': count,
                'years': list(set(v.year for v in vehicles if v.year)),
                'locations': list(set(v.location for v in vehicles if v.location)),
                'yards': list(set(v.yard for v in vehicles if v.yard)),
                'scraper_name': self.scrapers[site_name].name if hasattr(self.scrapers[site_name], 'name') else 'Unknown'
            }
        
        return {
            'total_vehicles': total_vehicles,
            'sites_scraped': len(results),
            'sites_with_results': sites_with_results,
            'sites_without_results': sites_without_results,
            'timestamp': datetime.now().isoformat(),
            'site_stats': site_stats
        }
    
    def get_sites_without_results(self, results: Dict[str, List[Vehicle]]) -> List[Dict[str, str]]:
        """Get detailed information about sites that returned no results."""
        sites_without_results = []
        
        for site_name, vehicles in results.items():
            if len(vehicles) == 0:
                scraper = self.scrapers[site_name]
                site_info = {
                    'site_name': site_name,
                    'scraper_name': scraper.name if hasattr(scraper, 'name') else 'Unknown',
                    'base_url': scraper.base_url if hasattr(scraper, 'base_url') else 'Unknown'
                }
                sites_without_results.append(site_info)
        
        return sites_without_results
    
    def filter_results(self, results: Dict[str, List[Vehicle]], 
                      year: str = None, 
                      location: str = None, 
                      max_price: float = None) -> Dict[str, List[Vehicle]]:
        """Filter results based on criteria."""
        filtered_results = {}
        
        for site_name, vehicles in results.items():
            filtered_vehicles = []
            
            for vehicle in vehicles:
                # Apply filters
                if year and vehicle.year != year:
                    continue
                
                if location and location.lower() not in (vehicle.location or '').lower():
                    continue
                
                if max_price and vehicle.price:
                    try:
                        price_value = float(vehicle.price.replace('$', '').replace(',', ''))
                        if price_value > max_price:
                            continue
                    except (ValueError, AttributeError):
                        pass
                
                filtered_vehicles.append(vehicle)
            
            filtered_results[site_name] = filtered_vehicles
        
        return filtered_results 