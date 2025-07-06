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

class ScraperManager:
    """Manages all Honda Insight scrapers."""
    
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
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all_sessions()
        
    def scrape_all(self, max_workers: int = 4, timeout: int = 300) -> Dict[str, List[Vehicle]]:
        """
        Scrape all sites for Honda Insight listings.
        
        Args:
            max_workers: Maximum number of concurrent scrapers
            timeout: Timeout in seconds for each scraper
            
        Returns:
            Dictionary mapping site names to lists of vehicles
        """
        logger.info(f"Starting scraping across {len(self.scrapers)} sites")
        
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
        logger.info(f"Scraping completed. Total vehicles found: {total_vehicles}")
        
        return results
    
    def _scrape_site_with_timeout(self, site_name: str, scraper, timeout: int) -> List[Vehicle]:
        """Scrape a single site with timeout protection."""
        try:
            logger.info(f"Starting scraping {site_name}")
            start_time = time.time()
            
            vehicles = scraper.scrape_listings()
            
            end_time = time.time()
            logger.info(f"Completed scraping {site_name} in {end_time - start_time:.2f} seconds")
            
            return vehicles
            
        except Exception as e:
            logger.error(f"Error scraping {site_name}: {e}")
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
        for site_name, vehicles in results.items():
            site_stats[site_name] = {
                'count': len(vehicles),
                'years': list(set(v.year for v in vehicles if v.year)),
                'locations': list(set(v.location for v in vehicles if v.location)),
                'yards': list(set(v.yard for v in vehicles if v.yard))
            }
        
        return {
            'total_vehicles': total_vehicles,
            'sites_scraped': len(results),
            'timestamp': datetime.now().isoformat(),
            'site_stats': site_stats
        }
    
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
    
    def close_all_sessions(self):
        """Close all scraper sessions to free up connections."""
        for scraper in self.scrapers.values():
            if hasattr(scraper, 'close_session'):
                scraper.close_session() 