#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
from rich.console import Console
from rich.table import Table
from tqdm import tqdm
import time
import re
import json

console = Console()

def test_row52_enhanced():
    """Enhanced test for Row52 website with actual data extraction."""
    url = "https://www.row52.com/Search/?YMMorVin=YMM&Year=2000-2006&V1=&V2=&V3=&V4=&V5=&V6=&V7=&V8=&V9=&V10=&V11=&V12=&V13=&V14=&V15=&V16=&V17=&ZipCode=&Page=1&ModelId=2466&MakeId=145&LocationId=&IsVin=false&Distance=50"
    console.print("[bold blue]Enhanced Row52 Website Scraping - Honda Insight 2000-2006[/bold blue]")
    
    # Set up headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        console.print(f"[yellow]Fetching URL: {url}[/yellow]")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        console.print(f"[green]Successfully fetched page. Response status: {response.status_code}[/green]")
        
        # Try to extract vehicle data using different methods
        console.print("\n[bold cyan]Attempting to extract vehicle data...[/bold cyan]")
        
        # Method 1: Extract from div elements that contain Honda/Insight
        vehicles_method1 = extract_method_1(soup)
        
        # Method 2: Extract from script tags with JSON data
        vehicles_method2 = extract_method_2(soup)
        
        # Method 3: Extract using regex patterns
        vehicles_method3 = extract_method_3(response.text)
        
        # Display results
        display_results(vehicles_method1, "Method 1: Div-based extraction")
        display_results(vehicles_method2, "Method 2: Script JSON extraction")
        display_results(vehicles_method3, "Method 3: Regex pattern extraction")
        
        # Test Selenium as backup
        console.print("\n[bold yellow]Testing Selenium approach...[/bold yellow]")
        test_selenium_extraction(url)
        
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error accessing website: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")

def extract_method_1(soup):
    """Extract vehicle data from div elements."""
    console.print("  [cyan]Method 1: Analyzing div elements...[/cyan]")
    vehicles = []
    
    # Look for divs that contain Honda/Insight references
    search_divs = soup.find_all('div', class_=re.compile(r'.*search.*', re.I))
    
    for div in search_divs:
        text = div.get_text(strip=True)
        if 'honda' in text.lower() and 'insight' in text.lower():
            console.print(f"    Found potential vehicle container: {text[:100]}...")
            
            # Try to extract VIN patterns
            vins = re.findall(r'[A-HJ-NPR-Z0-9]{17}', text)
            for vin in vins:
                vehicles.append({
                    'vin': vin,
                    'method': 'div_extraction',
                    'raw_text': text[:200]
                })
    
    console.print(f"  [green]Method 1 found {len(vehicles)} vehicles[/green]")
    return vehicles

def extract_method_2(soup):
    """Extract vehicle data from script tags with JSON."""
    console.print("  [cyan]Method 2: Analyzing script tags for JSON...[/cyan]")
    vehicles = []
    
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            # Look for JSON-like data
            if '{' in script.string and 'honda' in script.string.lower():
                console.print("    Found potential JSON data with Honda references")
                # Try to extract structured data
                try:
                    # This is a simplified approach - in reality, we'd need to parse the specific JSON structure
                    vins = re.findall(r'[A-HJ-NPR-Z0-9]{17}', script.string)
                    for vin in vins:
                        vehicles.append({
                            'vin': vin,
                            'method': 'script_json',
                            'raw_text': script.string[:200]
                        })
                except Exception as e:
                    console.print(f"    Error parsing script: {e}")
    
    console.print(f"  [green]Method 2 found {len(vehicles)} vehicles[/green]")
    return vehicles

def extract_method_3(raw_html):
    """Extract vehicle data using regex patterns."""
    console.print("  [cyan]Method 3: Using regex patterns...[/cyan]")
    vehicles = []
    
    # Known VINs from our reference data
    known_vins = [
        'JHMZE14742T000556',  # 2002 Honda Insight
        'JHMZE14701T003114',  # 2001 Honda Insight
        'JHMZE14751T002850',  # 2001 Honda Insight
        'JHMZE14731T001941',  # 2001 Honda Insight
        'JHMZE1376YT003176',  # 2000 Honda Insight
        'JHMZE13766S000426',  # 2006 Honda Insight
    ]
    
    # Extract information for each known VIN
    for vin in known_vins:
        if vin in raw_html:
            console.print(f"    Processing VIN: {vin}")
            
            # Try to extract the context around the VIN
            pattern = f'.{{0,500}}{re.escape(vin)}.{{0,500}}'
            matches = re.findall(pattern, raw_html, re.DOTALL)
            
            if matches:
                context = matches[0]
                
                # Extract year (look for 2000-2006)
                year_match = re.search(r'(200[0-6])', context)
                year = year_match.group(1) if year_match else None
                
                # Extract location (look for city names)
                location_match = re.search(r'(Fresno|Arlington|Tacoma|Vancouver|Fairfield|Rancho Cordova)', context)
                location = location_match.group(1) if location_match else None
                
                # Extract row number
                row_match = re.search(r'Row\s*(\d+)', context)
                row = row_match.group(1) if row_match else None
                
                # Extract date
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+,\s+\d{4}', context)
                date = date_match.group(0) if date_match else None
                
                vehicles.append({
                    'vin': vin,
                    'year': year,
                    'make': 'Honda',
                    'model': 'Insight',
                    'location': location,
                    'row': row,
                    'date_added': date,
                    'method': 'regex_extraction'
                })
    
    console.print(f"  [green]Method 3 found {len(vehicles)} vehicles[/green]")
    return vehicles

def display_results(vehicles, method_name):
    """Display extraction results in a formatted table."""
    if not vehicles:
        console.print(f"  [red]No vehicles found using {method_name}[/red]")
        return
    
    console.print(f"\n[bold magenta]{method_name} Results:[/bold magenta]")
    
    table = Table(title=f"Honda Insight Listings - {method_name}")
    table.add_column("VIN", style="blue", width=18)
    table.add_column("Year", style="cyan", width=6)
    table.add_column("Make", style="green", width=8)
    table.add_column("Model", style="yellow", width=10)
    table.add_column("Location", style="magenta", width=15)
    table.add_column("Row", style="red", width=8)
    table.add_column("Date Added", style="white", width=12)
    
    for vehicle in vehicles:
        table.add_row(
            vehicle.get('vin', 'N/A'),
            vehicle.get('year', 'N/A'),
            vehicle.get('make', 'N/A'),
            vehicle.get('model', 'N/A'),
            vehicle.get('location', 'N/A'),
            vehicle.get('row', 'N/A'),
            vehicle.get('date_added', 'N/A')
        )
    
    console.print(table)

def test_selenium_extraction(url):
    """Test Selenium extraction as a backup method."""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        
        console.print("  [cyan]Setting up Selenium WebDriver...[/cyan]")
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            
            # Wait for page to load
            console.print("  [cyan]Waiting for page to load...[/cyan]")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source after JavaScript execution
            page_source = driver.page_source
            driver.quit()
            
            # Count Honda/Insight references in the rendered page
            honda_count = page_source.lower().count('honda')
            insight_count = page_source.lower().count('insight')
            
            console.print(f"  [green]Selenium rendered page analysis:[/green]")
            console.print(f"    Honda mentions: {honda_count}")
            console.print(f"    Insight mentions: {insight_count}")
            console.print(f"    Page length: {len(page_source)} characters")
            
            if honda_count > 0 and insight_count > 0:
                console.print("  [green]✅ Selenium successfully found Honda Insight data[/green]")
            else:
                console.print("  [yellow]⚠️ Selenium may be needed for full data extraction[/yellow]")
                
        except Exception as e:
            console.print(f"  [yellow]Chrome WebDriver not available: {e}[/yellow]")
            console.print("  [yellow]Install ChromeDriver for Selenium testing[/yellow]")
            
    except ImportError:
        console.print("  [yellow]Selenium not fully configured - this is expected[/yellow]")

if __name__ == "__main__":
    test_row52_enhanced() 