# 🚗 Honda Insight Rescue

> **Helping the Honda Insight community find parts cars and keep these efficient hybrids on the road**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-%23000.svg?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)

Honda Insight Rescue is an automated web scraping system that monitors salvage yards and auction sites for Honda Insight vehicles (2000-2006). Built specifically for the [InsightCentral.net](https://insightcentral.net) community, this tool helps enthusiasts find parts cars before they're crushed or disappear forever.

## 🎯 Features

- **🔍 Automated Monitoring** - Scans Row52.com every 30 minutes for new Honda Insight listings
- **📊 Web Dashboard** - Beautiful, responsive web interface with real-time updates
- **🚀 REST API** - Full API access for programmatic data retrieval
- **🔄 Change Tracking** - Automatically detects new and removed listings
- **📱 Mobile Friendly** - Works perfectly on phones and tablets
- **⚡ Real-time Updates** - Live data refreshing without page reloads
- **🎨 Modern UI** - Clean, Honda-themed design built with Bootstrap 5

## 🚙 Why Honda Insight (2000-2006)?

The first-generation Honda Insight was revolutionary:
- **First hybrid sold in America** (1999 model year)
- **Incredible fuel economy** - Up to 70 MPG highway
- **Limited production** - Only ~17,000 units sold in the US
- **Lightweight design** - Advanced aluminum space frame
- **Historical significance** - Pioneered hybrid technology

With so few produced and many lost over time, every surviving Insight helps preserve automotive history and keeps these amazing efficient vehicles running.

## 🖥️ Live Demo

Check out the live web interface: **[Coming Soon]**

## 🛠️ Installation

### Prerequisites
- Python 3.12+
- pip (Python package installer)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/mike-cline-53/honda_insight_rescue.git
   cd honda_insight_rescue
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the web application**
   ```bash
   python web_app.py
   ```

5. **Open your browser**
   ```
   http://localhost:5000
   ```

## 📖 Usage

### Web Interface

The web interface provides:
- **Dashboard** - Overview of current listings with stats
- **Vehicle Cards** - Detailed information for each Honda Insight found
- **Filtering** - Search by year, location, VIN
- **Manual Scanning** - Trigger immediate scans
- **Real-time Updates** - Auto-refresh every 5 minutes

### Command Line Interface

```bash
# Basic scan
python car_monitor.py --scan

# Scan and save results
python car_monitor.py --scan --save

# Continuous monitoring (every 30 minutes)
python car_monitor.py --watch --save --compare

# Compare with previous results
python car_monitor.py --scan --compare
```

### REST API

```bash
# Get current listings
curl http://localhost:5000/api/listings

# Trigger a manual scan
curl -X POST http://localhost:5000/api/scan

# Check system status
curl http://localhost:5000/api/status
```

Full API documentation available at `/api` when running the web app.

## 📊 Current Data Sources

| Source | Status | Coverage | Update Frequency |
|--------|--------|----------|------------------|
| **Row52.com** | ✅ Active | Pick-n-Pull yards nationwide | Every 30 minutes |
| Copart.com | 🚧 Coming Soon | Auction vehicles | - |
| IAA-Auction.com | 🚧 Coming Soon | Insurance auctions | - |

## 🗂️ Project Structure

```
honda_insight_rescue/
├── web_app.py              # Flask web application
├── car_monitor.py          # CLI monitoring tool
├── scrapers/
│   ├── row52_scraper.py    # Row52.com scraper
│   └── __init__.py
├── templates/              # HTML templates
│   ├── base.html          # Base template
│   ├── index.html         # Main dashboard
│   ├── about.html         # About page
│   └── api.html           # API documentation
├── data/                   # Saved results (JSON files)
├── test_*.py              # Test scripts
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔌 API Reference

### GET `/api/listings`
Returns current Honda Insight listings

```json
{
  "listings": [
    {
      "vin": "JHMZE14742T000556",
      "year": "2002",
      "make": "Honda",
      "model": "Insight",
      "location": "Fresno",
      "yard": "PICK-n-PULL Fresno",
      "row": "61",
      "date_added": "Jul 02, 2025",
      "source_url": "https://www.row52.com/...",
      "scraped_at": "2025-07-05T12:13:29.537861"
    }
  ],
  "total_count": 6,
  "last_updated": "2025-07-05T12:13:29.537857",
  "scan_in_progress": false
}
```

### POST `/api/scan`
Triggers manual scan of all data sources

### GET `/api/status`
Returns system status and scan information

## 🚀 Deployment

### Docker (Recommended)

```bash
# Build the image
docker build -t honda-insight-rescue .

# Run the container
docker run -p 5000:5000 honda-insight-rescue
```

### Traditional Hosting

```bash
# Using Gunicorn
gunicorn --bind 0.0.0.0:5000 web_app:app

# Using systemd service
sudo systemctl enable honda-insight-rescue
sudo systemctl start honda-insight-rescue
```

## 🤝 Contributing

We welcome contributions from the Honda Insight community! Here's how you can help:

### Adding New Data Sources

1. Create a new scraper in `scrapers/new_site_scraper.py`
2. Follow the pattern established by `row52_scraper.py`
3. Add the scraper to `car_monitor.py` and `web_app.py`
4. Submit a pull request

### Reporting Issues

- Found a bug? [Open an issue](https://github.com/mike-cline-53/honda_insight_rescue/issues)
- Have a feature request? [Start a discussion](https://github.com/mike-cline-53/honda_insight_rescue/discussions)
- Want to add a new site? [Create a feature request](https://github.com/mike-cline-53/honda_insight_rescue/issues)

### Development Setup

```bash
git clone https://github.com/mike-cline-53/honda_insight_rescue.git
cd honda_insight_rescue
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pytest  # Run tests
```

## 📊 Data Extracted

For each Honda Insight listing, we extract:

- **VIN** - Vehicle Identification Number
- **Year** - Decoded from VIN (2000-2006)
- **Location** - City/state where vehicle is located
- **Yard** - Junkyard or facility name
- **Row** - Row number in the yard (when available)
- **Date Added** - When vehicle was added to yard
- **Source URL** - Direct link to listing

## 🌟 Community

### InsightCentral.net
Join the premier Honda Insight community at [InsightCentral.net](https://insightcentral.net) for:
- Technical discussions and repair guides
- Parts marketplace and trading
- Member builds and modifications
- Honda Insight news and updates

### Get Involved
- ⭐ **Star this repository** to show your support
- 🍴 **Fork and contribute** to help improve the project
- 📢 **Share with other Insight owners** on forums and social media
- 💡 **Suggest new features** or data sources to monitor

## 📈 Current Results

As of the latest scan, Honda Insight Rescue has found:
- **6 active listings** across Pick-n-Pull yards
- **Multiple states covered** including CA, WA, OR
- **Years 2000-2006** all represented in current inventory

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **InsightCentral.net community** - For inspiration and support
- **Honda** - For creating these amazing hybrid pioneers
- **Row52/Pick-n-Pull** - For providing accessible junkyard inventory data
- **Contributors** - Everyone who helps improve this project

## 📞 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/mike-cline-53/honda_insight_rescue/issues)
- 💬 **Questions**: [GitHub Discussions](https://github.com/mike-cline-53/honda_insight_rescue/discussions)
- 🌐 **Community**: [InsightCentral.net](https://insightcentral.net)

---

<div align="center">

**Made with ❤️ for the Honda Insight community**

*Every part saved is an Insight saved!*

[⭐ Star this repo](https://github.com/mike-cline-53/honda_insight_rescue) • [🍴 Fork](https://github.com/mike-cline-53/honda_insight_rescue/fork) • [📝 Contribute](https://github.com/mike-cline-53/honda_insight_rescue/blob/main/CONTRIBUTING.md)

</div> 