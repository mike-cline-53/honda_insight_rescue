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

console = Console()

def test_row52_scraping():
    """Test scraping functionality for Row52 website - Honda Insight listings."""
    url = "https://www.row52.com/Search/?YMMorVin=YMM&Year=2000-2006&V1=&V2=&V3=&V4=&V5=&V6=&V7=&V8=&V9=&V10=&V11=&V12=&V13=&V14=&V15=&V16=&V17=&ZipCode=&Page=1&ModelId=2466&MakeId=145&LocationId=&IsVin=false&Distance=50"
    console.print("[bold blue]Testing Row52 Website Scraping - Honda Insight 2000-2006[/bold blue]")
    
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
        console.print(f"[green]Page length: {len(response.text)} characters[/green]")
        
        # Method 1: Look for common vehicle listing patterns
        console.print("\n[bold cyan]Method 1: Searching for common vehicle listing patterns[/bold cyan]")
        test_method_1(soup)
        
        # Method 2: Look for specific Row52 patterns
        console.print("\n[bold cyan]Method 2: Searching for Row52-specific patterns[/bold cyan]")
        test_method_2(soup)
        
        # Method 3: Look for table/grid structures
        console.print("\n[bold cyan]Method 3: Searching for table/grid structures[/bold cyan]")
        test_method_3(soup)
        
        # Method 4: Look for JavaScript-rendered content indicators
        console.print("\n[bold cyan]Method 4: Checking for JavaScript-rendered content[/bold cyan]")
        test_method_4(soup, response.text)
        
        # Method 5: Look for specific text patterns
        console.print("\n[bold cyan]Method 5: Searching for Honda Insight text patterns[/bold cyan]")
        test_method_5(soup, response.text)
        
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error accessing website: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")

def test_method_1(soup):
    """Test Method 1: Look for common vehicle listing patterns."""
    patterns = [
        ('div', {'class': 'vehicle'}),
        ('div', {'class': 'car'}),
        ('div', {'class': 'listing'}),
        ('div', {'class': 'item'}),
        ('div', {'class': 'result'}),
        ('tr', {}),  # Table rows
        ('li', {}),  # List items
    ]
    
    for tag, attrs in patterns:
        elements = soup.find_all(tag, attrs)
        if elements:
            console.print(f"  Found {len(elements)} {tag} elements with {attrs}")
            # Show first few elements
            for i, element in enumerate(elements[:3]):
                text = element.get_text(strip=True)[:100]
                console.print(f"    [{i+1}] {text}...")
        else:
            console.print(f"  No {tag} elements found with {attrs}")

def test_method_2(soup):
    """Test Method 2: Look for Row52-specific patterns."""
    # Look for specific Row52 classes or IDs
    row52_patterns = [
        ('div', {'class': re.compile(r'.*vehicle.*', re.I)}),
        ('div', {'class': re.compile(r'.*row.*', re.I)}),
        ('div', {'class': re.compile(r'.*search.*', re.I)}),
        ('div', {'class': re.compile(r'.*result.*', re.I)}),
        ('table', {}),
        ('tbody', {}),
    ]
    
    for tag, attrs in row52_patterns:
        elements = soup.find_all(tag, attrs)
        if elements:
            console.print(f"  Found {len(elements)} {tag} elements matching Row52 pattern")
            # Check if any contain Honda or Insight
            honda_elements = [e for e in elements if 'honda' in e.get_text().lower() or 'insight' in e.get_text().lower()]
            if honda_elements:
                console.print(f"    {len(honda_elements)} contain Honda/Insight references")
                for i, element in enumerate(honda_elements[:2]):
                    text = element.get_text(strip=True)[:150]
                    console.print(f"    Honda/Insight [{i+1}]: {text}...")

def test_method_3(soup):
    """Test Method 3: Look for table/grid structures."""
    # Look for tables
    tables = soup.find_all('table')
    console.print(f"  Found {len(tables)} table elements")
    
    for i, table in enumerate(tables[:2]):
        rows = table.find_all('tr')
        console.print(f"    Table {i+1}: {len(rows)} rows")
        if rows:
            # Check first few rows for Honda content
            for j, row in enumerate(rows[:3]):
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_text = ' | '.join([cell.get_text(strip=True) for cell in cells])
                    console.print(f"      Row {j+1}: {row_text[:100]}...")

def test_method_4(soup, raw_html):
    """Test Method 4: Check for JavaScript-rendered content."""
    # Look for indicators of JavaScript rendering
    js_indicators = [
        'react', 'vue', 'angular', 'app-root', 'ng-app',
        'data-reactroot', 'v-app', '__NEXT_DATA__'
    ]
    
    found_js = []
    for indicator in js_indicators:
        if indicator in raw_html.lower():
            found_js.append(indicator)
    
    if found_js:
        console.print(f"  Found JS framework indicators: {', '.join(found_js)}")
        console.print("  [yellow]Page may be JavaScript-rendered, might need Selenium[/yellow]")
    else:
        console.print("  No obvious JavaScript framework indicators found")
    
    # Look for JSON data in script tags
    scripts = soup.find_all('script')
    json_scripts = 0
    for script in scripts:
        if script.string and ('{' in script.string or '[' in script.string):
            json_scripts += 1
    
    console.print(f"  Found {json_scripts} script tags with potential JSON data")

def test_method_5(soup, raw_html):
    """Test Method 5: Search for Honda Insight text patterns."""
    # Look for Honda Insight mentions
    honda_count = raw_html.lower().count('honda')
    insight_count = raw_html.lower().count('insight')
    vin_count = len(re.findall(r'[A-HJ-NPR-Z0-9]{17}', raw_html))
    
    console.print(f"  'Honda' mentions: {honda_count}")
    console.print(f"  'Insight' mentions: {insight_count}")
    console.print(f"  Potential VIN patterns: {vin_count}")
    
    # Look for specific VIN patterns from the search results
    known_vins = [
        'JHMZE14742T000556',  # 2002 Honda Insight
        'JHMZE14701T003114',  # 2001 Honda Insight
        'JHMZE14751T002850',  # 2001 Honda Insight
        'JHMZE14731T001941',  # 2001 Honda Insight
        'JHMZE1376YT003176',  # 2000 Honda Insight
        'JHMZE13766S000426',  # 2006 Honda Insight
    ]
    
    found_vins = []
    for vin in known_vins:
        if vin in raw_html:
            found_vins.append(vin)
    
    if found_vins:
        console.print(f"  [green]Found known VINs: {', '.join(found_vins)}[/green]")
    else:
        console.print("  [yellow]No known VINs found in raw HTML[/yellow]")
    
    # Look for location patterns
    locations = ['Fresno', 'Arlington', 'Tacoma', 'Vancouver', 'Fairfield', 'Rancho Cordova']
    found_locations = []
    for location in locations:
        if location.lower() in raw_html.lower():
            found_locations.append(location)
    
    if found_locations:
        console.print(f"  [green]Found locations: {', '.join(found_locations)}[/green]")

def extract_vehicle_data(soup):
    """Attempt to extract vehicle data based on test results."""
    console.print("\n[bold magenta]Attempting to extract vehicle data...[/bold magenta]")
    
    # This will be implemented based on which test method works best
    # For now, let's try a few approaches
    
    table = Table(title="Honda Insight Listings Found")
    table.add_column("Year", style="cyan")
    table.add_column("Make", style="green")
    table.add_column("Model", style="yellow")
    table.add_column("VIN", style="blue")
    table.add_column("Location", style="magenta")
    table.add_column("Row", style="red")
    table.add_column("Date Added", style="white")
    
    # Try to find structured data
    # This is a placeholder - we'll implement based on test results
    console.print("  [yellow]Data extraction will be implemented based on test results[/yellow]")
    
    return table

if __name__ == "__main__":
    test_row52_scraping() 