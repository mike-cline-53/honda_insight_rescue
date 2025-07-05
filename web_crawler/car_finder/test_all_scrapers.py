#!/usr/bin/env python3

import sys
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
import time
from datetime import datetime
import json

# Add the scrapers directory to the path
sys.path.append(str(Path(__file__).parent / "scrapers"))

from scrapers.scraper_manager import ScraperManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

def test_individual_scrapers():
    """Test each scraper individually."""
    console.print("\n[bold blue]Testing Individual Scrapers[/bold blue]")
    
    manager = ScraperManager()
    
    # Validate all scrapers first
    validation_results = manager.validate_scrapers()
    
    table = Table(title="Scraper Validation Results")
    table.add_column("Site", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Name", style="yellow")
    
    for site_name, is_valid in validation_results.items():
        status = "✓ Valid" if is_valid else "✗ Invalid"
        scraper_name = manager.scrapers[site_name].name if is_valid else "N/A"
        table.add_row(site_name, status, scraper_name)
    
    console.print(table)
    
    # Test a few scrapers individually
    test_sites = ['row52', 'fenix', 'uwrenchit']  # Start with a few to test
    
    for site_name in test_sites:
        console.print(f"\n[bold green]Testing {site_name}...[/bold green]")
        
        start_time = time.time()
        try:
            vehicles = manager.scrape_site(site_name)
            end_time = time.time()
            
            console.print(f"✓ {site_name} completed in {end_time - start_time:.2f} seconds")
            console.print(f"  Found {len(vehicles)} vehicles")
            
            if vehicles:
                # Show a sample vehicle
                sample_vehicle = vehicles[0]
                console.print(f"  Sample: {sample_vehicle.year} {sample_vehicle.make} {sample_vehicle.model}")
                console.print(f"  VIN: {sample_vehicle.vin}")
                console.print(f"  Location: {sample_vehicle.location}")
                
        except Exception as e:
            console.print(f"✗ {site_name} failed: {e}")

def test_all_scrapers():
    """Test all scrapers together."""
    console.print("\n[bold blue]Testing All Scrapers Together[/bold blue]")
    
    manager = ScraperManager()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("Scraping all sites...", total=len(manager.scrapers))
        
        # Use a smaller timeout for testing
        results = manager.scrape_all(max_workers=2, timeout=60)
        
        progress.update(task, completed=len(manager.scrapers))
    
    # Display results
    stats = manager.get_statistics(results)
    
    console.print(f"\n[bold green]Scraping Complete![/bold green]")
    console.print(f"Total vehicles found: {stats['total_vehicles']}")
    console.print(f"Sites scraped: {stats['sites_scraped']}")
    
    # Create results table
    table = Table(title="Scraping Results by Site")
    table.add_column("Site", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("Vehicles", style="green")
    table.add_column("Years", style="blue")
    table.add_column("Locations", style="magenta")
    
    for site_name, vehicles in results.items():
        scraper_name = manager.scrapers[site_name].name
        count = len(vehicles)
        
        years = list(set(v.year for v in vehicles if v.year))
        locations = list(set(v.location for v in vehicles if v.location))
        
        years_str = ", ".join(sorted(years)) if years else "N/A"
        locations_str = ", ".join(locations[:3]) if locations else "N/A"
        if len(locations) > 3:
            locations_str += f" (+{len(locations) - 3} more)"
        
        table.add_row(site_name, scraper_name, str(count), years_str, locations_str)
    
    console.print(table)
    
    # Save results to file
    save_test_results(results, stats)
    
    return results, stats

def save_test_results(results, stats):
    """Save test results to a JSON file."""
    try:
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        filepath = data_dir / filename
        
        # Convert Vehicle objects to dictionaries
        serializable_results = {}
        for site_name, vehicles in results.items():
            serializable_results[site_name] = [vehicle.to_dict() for vehicle in vehicles]
        
        data = {
            'timestamp': stats['timestamp'],
            'total_vehicles': stats['total_vehicles'],
            'sites_scraped': stats['sites_scraped'],
            'results': serializable_results,
            'site_stats': stats['site_stats']
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        console.print(f"\n[bold cyan]Test results saved to: {filepath}[/bold cyan]")
        
    except Exception as e:
        console.print(f"[bold red]Error saving test results: {e}[/bold red]")

def main():
    """Main test function."""
    console.print(Panel.fit(
        "[bold blue]Honda Insight Scraper Test Suite[/bold blue]\n"
        "Testing all scrapers for Honda Insight vehicles (1999-2006)",
        title="Test Suite",
        border_style="blue"
    ))
    
    # Test individual scrapers first
    test_individual_scrapers()
    
    # Then test all scrapers together
    results, stats = test_all_scrapers()
    
    # Final summary
    console.print(Panel.fit(
        f"[bold green]Test Complete![/bold green]\n"
        f"Total vehicles found: {stats['total_vehicles']}\n"
        f"Sites tested: {stats['sites_scraped']}\n"
        f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        title="Summary",
        border_style="green"
    ))

if __name__ == "__main__":
    main() 