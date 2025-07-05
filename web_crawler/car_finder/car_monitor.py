#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from rich.text import Text
import time

# Add the scrapers directory to the path
sys.path.append(str(Path(__file__).parent / "scrapers"))

from row52_scraper import Row52Scraper, Vehicle

console = Console()

class CarMonitor:
    """Main monitoring class for Honda Insight listings."""
    
    def __init__(self):
        self.scrapers = {
            'row52': Row52Scraper()
        }
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
    def scan_all_sites(self) -> Dict[str, List[Vehicle]]:
        """Scan all configured sites for Honda Insight listings."""
        results = {}
        
        for site_name, scraper in self.scrapers.items():
            console.print(f"[bold blue]Scanning {site_name}...[/bold blue]")
            
            with console.status(f"[bold green]Fetching data from {site_name}...") as status:
                try:
                    vehicles = scraper.scrape_listings()
                    results[site_name] = vehicles
                    console.print(f"[green]✅ {site_name}: Found {len(vehicles)} vehicles[/green]")
                except Exception as e:
                    console.print(f"[red]❌ {site_name}: Error - {e}[/red]")
                    results[site_name] = []
        
        return results
    
    def display_results(self, results: Dict[str, List[Vehicle]]):
        """Display scan results in a formatted table."""
        total_vehicles = sum(len(vehicles) for vehicles in results.values())
        
        if total_vehicles == 0:
            console.print("[yellow]No Honda Insight listings found.[/yellow]")
            return
        
        # Create summary table
        summary_table = Table(title="Honda Insight Listings Summary")
        summary_table.add_column("Site", style="cyan")
        summary_table.add_column("Vehicles Found", style="green")
        summary_table.add_column("Status", style="yellow")
        
        for site_name, vehicles in results.items():
            status = "✅ Active" if vehicles else "❌ No listings"
            summary_table.add_row(site_name.upper(), str(len(vehicles)), status)
        
        console.print(summary_table)
        console.print()
        
        # Create detailed table for each site
        for site_name, vehicles in results.items():
            if not vehicles:
                continue
            
            detail_table = Table(title=f"Detailed Listings - {site_name.upper()}")
            detail_table.add_column("Year", style="cyan", width=6)
            detail_table.add_column("VIN", style="blue", width=18)
            detail_table.add_column("Location", style="magenta", width=15)
            detail_table.add_column("Yard", style="green", width=20)
            detail_table.add_column("Row", style="red", width=6)
            detail_table.add_column("Date Added", style="white", width=12)
            
            for vehicle in vehicles:
                detail_table.add_row(
                    vehicle.year or "N/A",
                    vehicle.vin,
                    vehicle.location or "N/A",
                    vehicle.yard or "N/A",
                    vehicle.row or "N/A",
                    vehicle.date_added or "N/A"
                )
            
            console.print(detail_table)
            console.print()
    
    def save_results(self, results: Dict[str, List[Vehicle]], filename: str = None):
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"honda_insight_listings_{timestamp}.json"
        
        filepath = self.data_dir / filename
        
        # Convert to serializable format
        data = {
            'timestamp': datetime.now().isoformat(),
            'sites': {}
        }
        
        for site_name, vehicles in results.items():
            data['sites'][site_name] = [vehicle.to_dict() for vehicle in vehicles]
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        console.print(f"[green]Results saved to: {filepath}[/green]")
        return filepath
    
    def load_previous_results(self, filename: str) -> Dict:
        """Load previous results from JSON file."""
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            return {}
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def compare_results(self, current: Dict[str, List[Vehicle]], previous_file: str = None):
        """Compare current results with previous scan."""
        if previous_file is None:
            # Find the most recent file
            json_files = list(self.data_dir.glob("honda_insight_listings_*.json"))
            if not json_files:
                console.print("[yellow]No previous results found for comparison.[/yellow]")
                return
            
            previous_file = max(json_files, key=lambda f: f.stat().st_mtime).name
        
        previous_data = self.load_previous_results(previous_file)
        
        if not previous_data:
            console.print("[yellow]No previous results found for comparison.[/yellow]")
            return
        
        console.print(f"[bold blue]Comparing with previous results: {previous_file}[/bold blue]")
        
        # Compare each site
        for site_name, current_vehicles in current.items():
            if site_name not in previous_data.get('sites', {}):
                continue
            
            previous_vehicles = previous_data['sites'][site_name]
            previous_vins = {v['vin'] for v in previous_vehicles}
            current_vins = {v.vin for v in current_vehicles}
            
            new_vins = current_vins - previous_vins
            removed_vins = previous_vins - current_vins
            
            if new_vins or removed_vins:
                console.print(f"\n[bold yellow]Changes detected for {site_name.upper()}:[/bold yellow]")
                
                if new_vins:
                    console.print(f"[green]🆕 New listings: {len(new_vins)}[/green]")
                    for vin in new_vins:
                        vehicle = next(v for v in current_vehicles if v.vin == vin)
                        console.print(f"  • {vehicle.year} Honda Insight - {vin}")
                
                if removed_vins:
                    console.print(f"[red]❌ Removed listings: {len(removed_vins)}[/red]")
                    for vin in removed_vins:
                        console.print(f"  • {vin}")
            else:
                console.print(f"[green]✅ No changes for {site_name.upper()}[/green]")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Honda Insight Car Monitor")
    parser.add_argument("--scan", action="store_true", help="Scan all sites for listings")
    parser.add_argument("--save", action="store_true", help="Save results to JSON file")
    parser.add_argument("--compare", action="store_true", help="Compare with previous results")
    parser.add_argument("--site", choices=['row52'], help="Scan specific site only")
    parser.add_argument("--watch", action="store_true", help="Watch mode - scan every 30 minutes")
    parser.add_argument("--output", help="Output filename for saved results")
    
    args = parser.parse_args()
    
    if not any([args.scan, args.watch]):
        parser.print_help()
        return
    
    monitor = CarMonitor()
    
    if args.watch:
        console.print("[bold blue]Starting watch mode - scanning every 30 minutes...[/bold blue]")
        console.print("Press Ctrl+C to stop")
        
        try:
            while True:
                console.print(f"\n[bold green]Scanning at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/bold green]")
                results = monitor.scan_all_sites()
                monitor.display_results(results)
                
                if args.save:
                    monitor.save_results(results, args.output)
                
                if args.compare:
                    monitor.compare_results(results)
                
                console.print("[yellow]Waiting 30 minutes for next scan...[/yellow]")
                time.sleep(1800)  # 30 minutes
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Watch mode stopped.[/yellow]")
    
    elif args.scan:
        if args.site:
            # Scan specific site only
            scraper = monitor.scrapers.get(args.site)
            if not scraper:
                console.print(f"[red]Unknown site: {args.site}[/red]")
                return
            
            console.print(f"[bold blue]Scanning {args.site} only...[/bold blue]")
            vehicles = scraper.scrape_listings()
            results = {args.site: vehicles}
        else:
            # Scan all sites
            results = monitor.scan_all_sites()
        
        monitor.display_results(results)
        
        if args.save:
            monitor.save_results(results, args.output)
        
        if args.compare:
            monitor.compare_results(results)

if __name__ == "__main__":
    main() 