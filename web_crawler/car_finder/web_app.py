#!/usr/bin/env python3

from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import threading
import time
import logging


# Add the scrapers directory to the path
sys.path.append(str(Path(__file__).parent / "scrapers"))

from scrapers.scraper_manager import ScraperManager
from scrapers.base_scraper import Vehicle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'honda-insight-rescue-2025'

# Global variables for caching
cached_results = {}
last_scan_time = None
scan_in_progress = False

def scan_sites():
    """Background function to scan all sites."""
    global cached_results, last_scan_time, scan_in_progress
    
    if scan_in_progress:
        return
    
    scan_in_progress = True
    logger.info("Starting background scan...")
    
    try:
        with ScraperManager() as manager:
            results = manager.scrape_all(max_workers=9, timeout=300)
            
            # Flatten results into a single list for backward compatibility
            all_vehicles = []
            for site_name, vehicles in results.items():
                all_vehicles.extend(vehicles)
            
            cached_results = {
                'all_sites': all_vehicles,
                'by_site': results,
                'timestamp': datetime.now().isoformat(),
                'total_count': len(all_vehicles)
            }
            
            last_scan_time = datetime.now()
            logger.info(f"Background scan completed. Found {len(all_vehicles)} vehicles across {len(results)} sites.")
            
            # Save to file
            save_results_to_file(cached_results)
        
    except Exception as e:
        logger.error(f"Error during background scan: {e}")
    finally:
        scan_in_progress = False

def save_results_to_file(results):
    """Save results to JSON file."""
    try:
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"honda_insight_listings_{timestamp}.json"
        filepath = data_dir / filename
        
        # Convert Vehicle objects to dictionaries
        sites_data = {}
        for site_name, vehicles in results['by_site'].items():
            sites_data[site_name] = [vehicle.to_dict() for vehicle in vehicles]
        
        data = {
            'timestamp': results['timestamp'],
            'total_count': results['total_count'],
            'sites': sites_data
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Results saved to {filepath}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")

def load_latest_results():
    """Load the most recent results from file."""
    try:
        data_dir = Path(__file__).parent / "data"
        if not data_dir.exists():
            return None
        
        json_files = list(data_dir.glob("honda_insight_listings_*.json"))
        if not json_files:
            return None
        
        latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
        
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        logger.error(f"Error loading latest results: {e}")
        return None

@app.route('/')
def index():
    """Main page showing Honda Insight listings."""
    return render_template('index.html')

@app.route('/api/listings')
def api_listings():
    """API endpoint to get current listings."""
    global cached_results, last_scan_time
    
    # If no cached results or they're old, try to load from file
    if not cached_results or (last_scan_time and datetime.now() - last_scan_time > timedelta(hours=1)):
        file_data = load_latest_results()
        if file_data:
            # Convert back to Vehicle objects for consistency
            all_vehicles = []
            by_site = {}
            
            for site_name, vehicles_data in file_data['sites'].items():
                site_vehicles = []
                for vehicle_data in vehicles_data:
                    vehicle = Vehicle(
                        vin=vehicle_data['vin'],
                        year=vehicle_data.get('year'),
                        make=vehicle_data.get('make'),
                        model=vehicle_data.get('model'),
                        location=vehicle_data.get('location'),
                        yard=vehicle_data.get('yard'),
                        row=vehicle_data.get('row'),
                        date_added=vehicle_data.get('date_added'),
                        source_url=vehicle_data.get('source_url'),
                        price=vehicle_data.get('price'),
                        contact_info=vehicle_data.get('contact_info')
                    )
                    site_vehicles.append(vehicle)
                    all_vehicles.append(vehicle)
                
                by_site[site_name] = site_vehicles
            
            cached_results = {
                'all_sites': all_vehicles,
                'by_site': by_site,
                'timestamp': file_data['timestamp'],
                'total_count': len(all_vehicles)
            }
            last_scan_time = datetime.fromisoformat(file_data['timestamp'])
    
    if not cached_results:
        return jsonify({
            'listings': [],
            'total_count': 0,
            'last_updated': None,
            'scan_in_progress': scan_in_progress
        })
    
    # Convert Vehicle objects to dictionaries for JSON response
    listings = [vehicle.to_dict() for vehicle in cached_results['all_sites']]
    
    # Also provide breakdown by site
    by_site = {}
    for site_name, vehicles in cached_results['by_site'].items():
        by_site[site_name] = {
            'count': len(vehicles),
            'listings': [vehicle.to_dict() for vehicle in vehicles]
        }
    
    return jsonify({
        'listings': listings,
        'by_site': by_site,
        'total_count': cached_results['total_count'],
        'last_updated': cached_results['timestamp'],
        'scan_in_progress': scan_in_progress
    })

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """API endpoint to trigger a manual scan."""
    global scan_in_progress
    
    if scan_in_progress:
        return jsonify({'error': 'Scan already in progress'}), 409
    
    # Start scan in background thread
    thread = threading.Thread(target=scan_sites)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Scan started', 'scan_in_progress': True})

@app.route('/api/status')
def api_status():
    """API endpoint to check scan status."""
    global last_scan_time, scan_in_progress
    
    return jsonify({
        'scan_in_progress': scan_in_progress,
        'last_scan_time': last_scan_time.isoformat() if last_scan_time else None,
        'cached_count': len(cached_results.get('all_sites', [])),
        'sites_count': len(cached_results.get('by_site', {}))
    })

@app.route('/about')
def about():
    """About page."""
    return render_template('about.html')

@app.route('/api')
def api_docs():
    """API documentation."""
    return render_template('api.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Load initial data
    file_data = load_latest_results()
    if file_data:
        logger.info("Loaded initial data from file")
    else:
        logger.info("No previous scan data found. Use the web interface to start a scan.")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000) 