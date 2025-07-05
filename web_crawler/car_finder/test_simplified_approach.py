#!/usr/bin/env python3

import sys
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
import requests
from bs4 import BeautifulSoup

# Add the scrapers directory to the path
sys.path.append(str(Path(__file__).parent / "scrapers"))

from scrapers.base_scraper import BaseScraper, Vehicle

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

class LKQSimplifiedTest(BaseScraper):
    """Simplified LKQ scraper for testing."""
    
    def scrape_listings(self) -> list[Vehicle]:
        """Test scraping LKQ with simplified approach."""
        vehicles = []
        
        # Test with a specific LKQ location and year
        test_urls = [
            f"https://www.lkqpickyourpart.com/parts/atlanta-3378/?year=2001&make={self.target_make}&model={self.target_model}&part=",
            f"https://www.lkqpickyourpart.com/parts/atlanta-3378/?year=2005&make={self.target_make}&model={self.target_model}&part=",
        ]
        
        for url in test_urls:
            response = self._make_request(url)
            if response:
                page_vehicles = self._extract_all_listings_from_page(response.text, url)
                vehicles.extend(page_vehicles)
        
        return vehicles

def test_insight_vs_civic():
    """Test both Honda Insight and Honda Civic to see the difference."""
    console.print(Panel.fit(
        "[bold blue]Testing Simplified Approach[/bold blue]\n"
        "Comparing Honda Insight vs Honda Civic results",
        title="Simplified Scraper Test",
        border_style="blue"
    ))
    
    # Test Honda Insight
    console.print("\n[bold green]Testing Honda Insight...[/bold green]")
    insight_scraper = LKQSimplifiedTest("LKQ Test - Insight", "HONDA", "INSIGHT")
    insight_vehicles = insight_scraper.scrape_listings()
    console.print(f"Honda Insight results: {len(insight_vehicles)} vehicles found")
    
    # Test Honda Civic
    console.print("\n[bold green]Testing Honda Civic...[/bold green]")
    civic_scraper = LKQSimplifiedTest("LKQ Test - Civic", "HONDA", "CIVIC")
    civic_vehicles = civic_scraper.scrape_listings()
    console.print(f"Honda Civic results: {len(civic_vehicles)} vehicles found")
    
    # Show results
    console.print(f"\n[bold cyan]Results Summary:[/bold cyan]")
    console.print(f"Honda Insight: {len(insight_vehicles)} vehicles")
    console.print(f"Honda Civic: {len(civic_vehicles)} vehicles")
    
    # Show some sample vehicles if found
    if insight_vehicles:
        console.print(f"\n[bold yellow]Sample Honda Insight:[/bold yellow]")
        for i, vehicle in enumerate(insight_vehicles[:3]):
            console.print(f"  {i+1}. {vehicle.year} {vehicle.make} {vehicle.model} - VIN: {vehicle.vin}")
    
    if civic_vehicles:
        console.print(f"\n[bold yellow]Sample Honda Civic:[/bold yellow]")
        for i, vehicle in enumerate(civic_vehicles[:3]):
            console.print(f"  {i+1}. {vehicle.year} {vehicle.make} {vehicle.model} - VIN: {vehicle.vin}")

def test_direct_url():
    """Test by directly checking what a search URL returns."""
    console.print(f"\n[bold blue]Direct URL Test[/bold blue]")
    
    # Test URLs
    insight_url = "https://www.lkqpickyourpart.com/parts/atlanta-3378/?year=2001&make=HONDA&model=INSIGHT&part="
    civic_url = "https://www.lkqpickyourpart.com/parts/atlanta-3378/?year=2001&make=HONDA&model=CIVIC&part="
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    console.print(f"Testing Insight URL: {insight_url}")
    try:
        response = requests.get(insight_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            console.print(f"Insight page loaded successfully. Page length: {len(response.text)} characters")
            
            # Look for common indicators of results
            if "no results" in response.text.lower():
                console.print("❌ Page explicitly says 'no results'")
            elif "inventory" in response.text.lower():
                console.print("✅ Page mentions 'inventory'")
            elif "vehicle" in response.text.lower():
                console.print("✅ Page mentions 'vehicle'")
            else:
                console.print("? Page content unclear")
                
    except Exception as e:
        console.print(f"❌ Error fetching Insight URL: {e}")
    
    console.print(f"\nTesting Civic URL: {civic_url}")
    try:
        response = requests.get(civic_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            console.print(f"Civic page loaded successfully. Page length: {len(response.text)} characters")
            
            # Look for common indicators of results
            if "no results" in response.text.lower():
                console.print("❌ Page explicitly says 'no results'")
            elif "inventory" in response.text.lower():
                console.print("✅ Page mentions 'inventory'")
            elif "vehicle" in response.text.lower():
                console.print("✅ Page mentions 'vehicle'")
            else:
                console.print("? Page content unclear")
                
    except Exception as e:
        console.print(f"❌ Error fetching Civic URL: {e}")

if __name__ == "__main__":
    # First test the direct URLs to see what's actually returned
    test_direct_url()
    
    # Then test the simplified scraper approach
    test_insight_vs_civic()
    
    console.print(Panel.fit(
        "[bold green]Test Complete![/bold green]\n"
        "This simplified approach removes VIN verification complexity\n"
        "and trusts the website's search functionality.",
        title="Summary",
        border_style="green"
    )) 