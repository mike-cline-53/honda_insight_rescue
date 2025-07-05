# Honda Insight Car Finder - Usage Guide

## Quick Start

```bash
# Basic scan - check all sites for Honda Insight listings
python car_monitor.py --scan

# Scan and save results to JSON file
python car_monitor.py --scan --save

# Scan specific site only
python car_monitor.py --scan --site row52

# Compare with previous results
python car_monitor.py --scan --compare

# Watch mode - scan every 30 minutes
python car_monitor.py --watch --save
```

## Commands

### `--scan`
Perform a one-time scan of all configured sites (currently Row52) for Honda Insight listings.

### `--save`
Save the results to a timestamped JSON file in the `data/` directory.

### `--compare`
Compare current results with the most recent previous scan to detect new or removed listings.

### `--site <site_name>`
Scan only the specified site. Currently supports: `row52`

### `--watch`
Run in continuous monitoring mode, scanning every 30 minutes. Press Ctrl+C to stop.

### `--output <filename>`
Specify a custom filename for saved results (use with `--save`).

## Example Output

```
Honda Insight Listings Summary
┏━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Site  ┃ Vehicles Found ┃ Status    ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ ROW52 │ 6              │ ✅ Active │
└───────┴────────────────┴───────────┘

Detailed Listings - ROW52
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Year   ┃ VIN                ┃ Location        ┃ Yard                 ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ 2002   │ JHMZE14742T000556  │ Fresno          │ Fresno               │
│ 2001   │ JHMZE14701T003114  │ N/A             │ Arlington            │
│ 2001   │ JHMZE14751T002850  │ Tacoma          │ Tacoma               │
│ 2001   │ JHMZE14731T001941  │ N/A             │ Vancouver            │
│ 2000   │ JHMZE1376YT003176  │ N/A             │ Fairfield            │
│ 2006   │ JHMZE13766S000426  │ N/A             │ Rancho Cordova       │
└────────┴────────────────────┴─────────────────┴──────────────────────┘
```

## Data Storage

Results are saved to JSON files in the `data/` directory with the following structure:

```json
{
  "timestamp": "2025-07-05T12:13:29.537857",
  "sites": {
    "row52": [
      {
        "vin": "JHMZE14742T000556",
        "year": "2002",
        "make": "Honda",
        "model": "Insight",
        "location": "Fresno",
        "yard": "Fresno",
        "row": null,
        "date_added": null,
        "source_url": "https://www.row52.com/Search/...",
        "scraped_at": "2025-07-05T12:13:29.537861"
      }
    ]
  }
}
```

## Change Detection

When using `--compare`, the system will:
- Compare current results with the most recent previous scan
- Show new listings that have appeared
- Show listings that have been removed
- Highlight changes for each site

Example output:
```
🆕 New listings: 1
  • 2001 Honda Insight - JHMZE14701T003114

❌ Removed listings: 1
  • JHMZE14742T000556
```

## Automation

For continuous monitoring, you can set up a cron job or use the built-in watch mode:

```bash
# Run every hour (cron job)
0 * * * * cd /path/to/car_finder && python car_monitor.py --scan --save --compare

# Or use watch mode
python car_monitor.py --watch --save --compare
```

## Adding New Sites

To add new sites:

1. Create a new scraper in `scrapers/new_site_scraper.py`
2. Implement the scraping logic following the Row52 scraper pattern
3. Add the new scraper to the `CarMonitor` class in `car_monitor.py`
4. Update the `--site` choices in the argument parser

## Data Extracted

For each Honda Insight listing, the system extracts:
- VIN (Vehicle Identification Number)
- Year (decoded from VIN)
- Make & Model (Honda Insight)
- Location (city/state)
- Yard name
- Row number (if available)
- Date added (if available)
- Source URL

## Troubleshooting

### No listings found
- Check if the website structure has changed
- Verify the search URL is still valid
- Check network connectivity

### Duplicate listings
- The system automatically deduplicates by VIN
- If you see unexpected duplicates, check the VIN extraction logic

### Missing data (row, date_added)
- Some data may not be available in the current page format
- Consider implementing detailed page scraping for more information

## Files and Directories

```
car_finder/
├── car_monitor.py          # Main CLI tool
├── scrapers/
│   ├── row52_scraper.py    # Row52 scraper
│   └── __init__.py
├── data/                   # Saved results (JSON files)
├── test_row52.py           # Initial test script
├── test_row52_enhanced.py  # Enhanced test script
├── requirements.txt        # Python dependencies
└── README.md              # Project documentation
``` 