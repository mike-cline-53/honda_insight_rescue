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
from dataclasses import asdict

# Add the scrapers directory to the path
sys.path.append(str(Path(__file__).parent / "scrapers"))

from row52_scraper import Row52Scraper, Vehicle

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
        scraper = Row52Scraper()
        vehicles = scraper.scrape_listings()
        
        cached_results = {
            'row52': vehicles,
            'timestamp': datetime.now().isoformat(),
            'total_count': len(vehicles)
        }
        
        last_scan_time = datetime.now()
        logger.info(f"Background scan completed. Found {len(vehicles)} vehicles.")
        
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
        data = {
            'timestamp': results['timestamp'],
            'sites': {
                'row52': [vehicle.to_dict() for vehicle in results['row52']]
            }
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
            vehicles = []
            for vehicle_data in file_data['sites']['row52']:
                vehicle = Vehicle(
                    vin=vehicle_data['vin'],
                    year=vehicle_data['year'],
                    make=vehicle_data['make'],
                    model=vehicle_data['model'],
                    location=vehicle_data['location'],
                    yard=vehicle_data['yard'],
                    row=vehicle_data['row'],
                    date_added=vehicle_data['date_added'],
                    source_url=vehicle_data['source_url']
                )
                vehicles.append(vehicle)
            
            cached_results = {
                'row52': vehicles,
                'timestamp': file_data['timestamp'],
                'total_count': len(vehicles)
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
    listings = [asdict(vehicle) for vehicle in cached_results['row52']]
    
    return jsonify({
        'listings': listings,
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
        'cached_count': len(cached_results.get('row52', []))
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

def start_background_scanner():
    """Start the background scanning thread."""
    def scanner_loop():
        while True:
            try:
                scan_sites()
                # Wait 30 minutes before next scan
                time.sleep(1800)
            except Exception as e:
                logger.error(f"Error in scanner loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    thread = threading.Thread(target=scanner_loop)
    thread.daemon = True
    thread.start()
    logger.info("Background scanner started")

if __name__ == '__main__':
    # Load initial data
    file_data = load_latest_results()
    if file_data:
        logger.info("Loaded initial data from file")
    
    # Start background scanner
    start_background_scanner()
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000) 