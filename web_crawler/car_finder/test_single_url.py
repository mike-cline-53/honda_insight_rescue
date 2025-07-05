#!/usr/bin/env python3
"""
Test script to check a single LKQ URL for Honda Civics
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.lkq_scraper import LKQScraper

def test_single_url():
    # URL with known results: 3 Honda Civics at Monrovia location
    test_url = "https://www.lkqpickyourpart.com/parts/monrovia-1281/?year=2006&make=HONDA&model=CIVIC&part="
    
    print(f"Testing LKQ scraper on single URL:")
    print(f"URL: {test_url}")
    print(f"Expected: 3 Honda Civics in 'Possible Matches' section")
    print("-" * 60)
    
    # Create scraper instance
    scraper = LKQScraper()
    
    # Test the specific URL
    results = scraper._scrape_location(test_url)
    
    print(f"\nResults found: {len(results)}")
    
    if results:
        print("\nDetailed Results:")
        for i, vehicle in enumerate(results, 1):
            print(f"{i}. {vehicle.year} {vehicle.make} {vehicle.model}")
            print(f"   Location: {vehicle.location}")
            print(f"   Yard: {vehicle.yard}")
            print(f"   Row: {vehicle.row}")
            print(f"   Date Added: {vehicle.date_added}")
            print(f"   Source URL: {vehicle.source_url}")
            print()
    else:
        print("No vehicles found - this indicates an issue with the scraper")
        
        # Let's also test the raw HTML to see what we're getting
        print("\nTesting raw HTTP request...")
        response = scraper._make_request(test_url)
        if response:
            print(f"HTTP Status: {response.status_code}")
            print(f"Content length: {len(response.text)}")
            
            # Look for key indicators in the HTML
            html_content = response.text.lower()
            if "possible matches" in html_content:
                print("✓ Found 'Possible Matches' section in HTML")
            else:
                print("✗ 'Possible Matches' section not found in HTML")
                
            if "honda" in html_content:
                print("✓ Found 'Honda' in HTML content")
            else:
                print("✗ 'Honda' not found in HTML content")
                
            if "civic" in html_content:
                print("✓ Found 'Civic' in HTML content")
            else:
                print("✗ 'Civic' not found in HTML content")
        else:
            print("Failed to fetch the page")

if __name__ == "__main__":
    test_single_url() 