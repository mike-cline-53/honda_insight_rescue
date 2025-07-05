# Honda Insight Rescue 🚗

A web crawler and monitoring tool to help Honda Insight enthusiasts find available 2000-2006 Honda Insight vehicles from junkyards and online marketplaces.

## Features

- **Web Scraping**: Automatically scrapes Row52 junkyard listings for Honda Insight vehicles
- **Web Interface**: Clean, responsive web dashboard to view and manage searches
- **Data Storage**: Saves search results in JSON format for historical tracking
- **API Endpoints**: RESTful API for programmatic access to vehicle data
- **Real-time Updates**: Monitor listings and get notified of new vehicles

## Project Structure

```
insight/
├── web_crawler/
│   └── car_finder/
│       ├── scrapers/          # Web scraping modules
│       ├── templates/         # HTML templates for web interface
│       ├── data/             # Stored search results
│       ├── car_monitor.py    # Main monitoring script
│       ├── web_app.py        # Flask web application
│       └── requirements.txt  # Python dependencies
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mike-cline-53/honda_insight_rescue.git
cd honda_insight_rescue
```

2. Navigate to the car finder directory:
```bash
cd web_crawler/car_finder
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

#### Running the Web Application

1. Start the Flask web server:
```bash
python web_app.py
```

2. Open your browser and go to: `http://localhost:5000`

#### Running the Scraper Directly

```bash
python car_monitor.py
```

## API Endpoints

- `GET /api/listings` - Get all stored vehicle listings
- `GET /api/scrape` - Trigger a new scraping session
- `GET /api/stats` - Get statistics about stored data

## Contributing

This project is designed for the Honda Insight enthusiast community. Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Target Vehicles

This tool specifically searches for:
- 2000-2006 Honda Insight (1st generation)
- All trim levels and conditions
- Both manual and CVT transmissions

## Built For

The [InsightCentral.net](https://insightcentral.net) community and Honda Insight enthusiasts worldwide.

## License

This project is open source and available under the [MIT License](LICENSE).

## Disclaimer

This tool is for educational and research purposes. Please respect the terms of service of the websites being scraped and use responsibly. 