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
import re


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
        
        # Clean the data before returning
        cleaned_data = clean_scraped_data(data)
        
        return cleaned_data
    except Exception as e:
        logger.error(f"Error loading latest results: {e}")
        return None

def clean_scraped_data(data):
    """Clean corrupted data from scraped results."""
    if not data or 'sites' not in data:
        return data
    
    def clean_price(price):
        """Clean price data."""
        if not price or not isinstance(price, str):
            return None
            
        # Remove extra whitespace and newlines
        price = price.strip().replace('\n', ' ').replace('\r', '')
        
        # Remove obvious corrupted data patterns
        corrupted_patterns = [
            r'\d+kg',  # Weight data mixed in
            r'\d+\.\d+\s*hrs',  # Time data mixed in
            r'\s+\d+kg\s*$',  # Weight at end
            r'^\s*[A-Z]\s*$',  # Single letters
            r'^\s*[A-Z]\s*\d+\s*$',  # Single letter followed by number
        ]
        
        for pattern in corrupted_patterns:
            price = re.sub(pattern, '', price, flags=re.IGNORECASE)
        
        price = price.strip()
        
        # If empty after cleaning, return None
        if not price:
            return None
            
        # If it contains multiple price-like patterns, take the first valid one
        price_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # $1,234.56
            r'\$\d+(?:-\d+)?',  # $100 or $100-200
            r'\d+(?:,\d{3})*(?:\.\d{2})?\s*\$',  # 1234.56$
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, price)
            if match:
                return match.group(0)
        
        # If it's a common valid non-numeric price, keep it
        valid_non_numeric = ['Call', 'Contact', 'See website', 'N/A', 'TBD', 'Ask']
        for valid_price in valid_non_numeric:
            if valid_price.lower() in price.lower():
                return valid_price
        
        # If price looks corrupted, return None
        if len(price) > 50 or re.search(r'[^\w\s\$\.,\-]', price):
            logger.warning(f"Corrupted price data detected: {price}")
            return None
            
        return price
    
    def clean_yard(yard):
        """Clean yard/business name data."""
        if not yard or not isinstance(yard, str):
            return None
            
        # Remove extra whitespace and newlines
        yard = yard.strip().replace('\n', ' ').replace('\r', '')
        
        # Remove obvious corrupted data patterns
        corrupted_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Price data mixed in
            r'\d+kg',  # Weight data mixed in
            r'\d+\.\d+\s*hrs',  # Time data mixed in
            r'^\s*[A-Z]\s*\d*\s*$',  # Single letters with optional numbers
        ]
        
        for pattern in corrupted_patterns:
            yard = re.sub(pattern, '', yard, flags=re.IGNORECASE)
        
        yard = yard.strip()
        
        # If empty after cleaning, return None
        if not yard:
            return None
            
        # If it's obviously a price, return None
        if yard.startswith('$') or yard.endswith('$'):
            logger.warning(f"Price data found in yard field: {yard}")
            return None
            
        # If yard name is too short or contains mostly numbers, likely corrupted
        if len(yard) < 3 or re.search(r'^\d+$', yard):
            logger.warning(f"Corrupted yard data detected: {yard}")
            return None
            
        return yard
    
    def expand_truncated_location(location):
        """Expand truncated location names to their full names."""
        if not location or not isinstance(location, str):
            return location
            
        truncation_mapping = {
            'Arlingto': 'Arlington',
            'Vancouve': 'Vancouver',
            'Fairfiel': 'Fairfield',
            'Rancho C': 'Rancho Cordova',
            'Sacram': 'Sacramento',
            'Portlan': 'Portland',
            'Seattl': 'Seattle'
        }
        
        return truncation_mapping.get(location, location)
    
    def is_valid_vin(vin):
        """Check if VIN is valid."""
        if not vin or not isinstance(vin, str):
            return False
            
        # Remove whitespace
        vin = vin.strip()
        
        # Check length (must be 17 characters)
        if len(vin) != 17:
            return False
            
        # Check if all characters are alphanumeric
        if not vin.isalnum():
            return False
            
        # Check for invalid characters (I, O, Q are not allowed in VINs)
        invalid_chars = set('IOQ')
        if any(char in invalid_chars for char in vin.upper()):
            return False
            
        # For Honda Insight, VIN should start with JHMZE
        if vin.upper().startswith('JHMZE'):
            return True
            
        # Accept other valid VIN patterns but log a warning
        logger.warning(f"VIN {vin} doesn't match Honda Insight pattern but appears valid")
        return True
    
    def clean_vin_or_id(vin_id):
        """Clean and validate VIN/ID data."""
        if not vin_id or not isinstance(vin_id, str):
            return "Not Found"
            
        # Remove extra whitespace and newlines
        vin_id = vin_id.strip().replace('\n', ' ').replace('\r', '')
        
        # If it's a real VIN, validate and return it
        if is_valid_vin(vin_id):
            return vin_id
        
        # If it's an LKQ ID, keep it as is (it's useful)
        if vin_id.startswith('LKQ_'):
            return vin_id
            
        # If it's a Car-Part stock number or similar, try to clean it
        # Remove obvious corrupted patterns
        corrupted_patterns = [
            r'\n+',  # Multiple newlines
            r'\s+hrs\s*$',  # Time data at end
            r'\d+\.\d+\s*hrs',  # Time data
            r'\d+kg',  # Weight data
        ]
        
        for pattern in corrupted_patterns:
            vin_id = re.sub(pattern, '', vin_id, flags=re.IGNORECASE)
        
        vin_id = vin_id.strip()
        
        # If it's too short or empty after cleaning, return "Not Found"
        if not vin_id or len(vin_id) < 1:
            return "Not Found"
            
        # If it's a single letter, it's likely corrupted
        if len(vin_id) == 1 and vin_id.isalpha():
            logger.warning(f"Corrupted VIN/ID detected, keeping vehicle with 'Not Found': {vin_id}")
            return "Not Found"
            
        # Keep anything else as an ID
        return vin_id
    
    cleaned_sites = {}
    total_cleaned = 0
    total_removed = 0  # This should now always be 0
    
    for site_name, vehicles in data['sites'].items():
        cleaned_vehicles = []
        
        for vehicle in vehicles:
            # Clean the VIN/ID (never remove entries, always keep the vehicle)
            cleaned_vin_id = clean_vin_or_id(vehicle.get('vin'))
            
            # Clean the vehicle data
            cleaned_vehicle = vehicle.copy()
            cleaned_vehicle['vin'] = cleaned_vin_id  # This will be renamed to vin_id later
            cleaned_vehicle['price'] = clean_price(vehicle.get('price'))
            cleaned_vehicle['yard'] = clean_yard(vehicle.get('yard'))
            
            # Expand truncated location names
            cleaned_vehicle['location'] = expand_truncated_location(vehicle.get('location'))
            cleaned_vehicle['yard'] = expand_truncated_location(cleaned_vehicle['yard'])
            
            cleaned_vehicles.append(cleaned_vehicle)
            total_cleaned += 1
        
        cleaned_sites[site_name] = cleaned_vehicles
    
    logger.info(f"Data cleaning complete: {total_cleaned} vehicles cleaned, {total_removed} vehicles removed")
    
    # Update the data structure
    cleaned_data = data.copy()
    cleaned_data['sites'] = cleaned_sites
    cleaned_data['total_count'] = total_cleaned
    
    return cleaned_data

def rename_vin_to_vin_id(vehicle_dict):
    """Rename 'vin' field to 'vin_id' in vehicle dictionary."""
    if 'vin' in vehicle_dict:
        vehicle_dict['vin_id'] = vehicle_dict.pop('vin')
    return vehicle_dict

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
    listings = [rename_vin_to_vin_id(vehicle.to_dict()) for vehicle in cached_results['all_sites']]
    
    # Also provide breakdown by site
    by_site = {}
    for site_name, vehicles in cached_results['by_site'].items():
        by_site[site_name] = {
            'count': len(vehicles),
            'listings': [rename_vin_to_vin_id(vehicle.to_dict()) for vehicle in vehicles]
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
    app.run(debug=True, host='0.0.0.0', port=5001) 