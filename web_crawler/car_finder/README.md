# Car Finder - Honda Insight Crawler

## Overview
This project crawls various websites to find listings for Honda Insight vehicles (2000-2006) that are available for auction or in junkyards.

## Features
- Automated testing of multiple scraping methods for each website
- Rich console output with colored tables and progress bars
- Modular design for easy addition of new websites
- Error handling and retry mechanisms

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Testing Row52.com
```bash
python test_row52.py
```

This will test multiple scraping methods against Row52.com to determine the best approach for extracting Honda Insight listings.

## Project Structure
```
car_finder/
├── README.md
├── requirements.txt
├── test_row52.py          # Test script for Row52.com
├── scrapers/              # Individual scraper modules (to be created)
│   ├── row52_scraper.py
│   └── base_scraper.py
└── utils/                 # Utility functions (to be created)
    ├── data_extraction.py
    └── notification.py
```

## Supported Websites
- [Row52.com](https://www.row52.com/) - Junkyard vehicle listings

## Adding New Websites
1. Create a new test script: `test_[website].py`
2. Test different scraping methods to find the best approach
3. Implement the scraper in the `scrapers/` directory
4. Add the scraper to the main monitoring system

## Data Extracted
For each Honda Insight listing, we extract:
- Year, Make, Model
- VIN number
- Location (city, state)
- Yard/lot information
- Date added
- Price (if available)
- Contact information

## Future Enhancements
- Support for additional websites (Copart, IAA, etc.)
- Email/SMS notifications for new listings
- Database storage for tracking listings over time
- Price trend analysis
- Distance-based filtering 