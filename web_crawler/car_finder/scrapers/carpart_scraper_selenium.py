#!/usr/bin/env python3

import logging
import time
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from .base_scraper import BaseScraper, Vehicle

logger = logging.getLogger(__name__)

class CarPartSeleniumScraper(BaseScraper):
    """Selenium-based scraper for Car-Part.com Honda Insight listings."""
    
    def __init__(self):
        super().__init__("Car-Part.com (Selenium)")
        self.base_url = "https://car-part.com/index.htm"
        self.driver = None
        
        # Common parts to search for
        self.common_parts = [
            "A Pillar",
            "Fender",
            "Headlight Housing",
            "Steering Wheel",
            "Bumper Cover (Front)",
            "Mirror, Door"
        ]
        
        # Honda Insight years
        self.insight_years = ["2000", "2001", "2002", "2003", "2004", "2005", "2006"]
    
    def _setup_driver(self):
        """Setup Chrome driver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        
    def _cleanup_driver(self):
        """Clean up the driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def scrape_listings(self) -> List[Vehicle]:
        """Scrape Honda Insight listings from Car-Part.com using Selenium."""
        logger.info("Starting Car-Part.com scraping for Honda Insight using Selenium")
        
        all_vehicles = []
        
        try:
            self._setup_driver()
            
            # Search for each part across all years (2000-2006) in one request
            for part in self.common_parts:
                logger.info(f"Searching for {part} in Honda Insight (2000-2006)...")
                
                vehicles = self._search_for_part_all_years(part)
                all_vehicles.extend(vehicles)  # Collect all results first (with duplicates)
                
                if vehicles:
                    logger.info(f"  Found {len(vehicles)} listings for {part}")
                
                # Small delay between searches to be respectful
                time.sleep(2)
            
            # Now apply the new filtering logic:
            # 1. Count how many times each stock # appears
            stock_counts = {}
            for vehicle in all_vehicles:
                stock_num = vehicle.vin  # Stock# is stored in VIN field
                if stock_num:
                    stock_counts[stock_num] = stock_counts.get(stock_num, 0) + 1
            
            # 2. Only keep vehicles whose stock # appears more than once
            multi_part_stocks = {stock for stock, count in stock_counts.items() if count > 1}
            
            # 3. Filter vehicles to only include those with multi-part stock numbers
            filtered_vehicles = [v for v in all_vehicles if v.vin in multi_part_stocks]
            
            # 4. Deduplicate by keeping only one instance of each stock #
            seen_stocks = set()
            unique_vehicles = []
            for vehicle in filtered_vehicles:
                stock_num = vehicle.vin
                if stock_num not in seen_stocks:
                    seen_stocks.add(stock_num)
                    unique_vehicles.append(vehicle)
            
            logger.info(f"Found {len(all_vehicles)} total listings")
            logger.info(f"Found {len(stock_counts)} unique stock numbers")
            logger.info(f"Found {len(multi_part_stocks)} vehicles with multiple parts available")
            logger.info(f"Final result: {len(unique_vehicles)} unique Honda Insight vehicles with multiple parts on Car-Part.com")
            
            return unique_vehicles
            
        except Exception as e:
            logger.error(f"Error in Car-Part.com scraping: {e}")
            return []
        finally:
            self._cleanup_driver()
    
    def _search_for_part_all_years(self, part: str) -> List[Vehicle]:
        """Search for Honda Insight vehicles for a specific part across all years (2000-2006)."""
        try:
            # Navigate to the main page
            self.driver.get(self.base_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "year"))
            )
            
            # Step 1: Select ANY year (we'll set the range later)
            year_select = Select(self.driver.find_element(By.ID, "year"))
            year_select.select_by_visible_text("2000")  # Just pick one to start
            time.sleep(2)  # Wait for JavaScript to update model dropdown
            
            # Step 2: Select Honda Insight model
            model_select = Select(self.driver.find_element(By.ID, "model"))
            model_select.select_by_visible_text("Honda Insight")
            time.sleep(2)  # Wait for any JavaScript updates
            
            # Step 3: Select part
            part_select = Select(self.driver.find_element(By.NAME, "userPart"))
            
            # Find the part option that contains our target part
            part_options = part_select.options
            selected_part = None
            
            for option in part_options:
                if part.lower() in option.text.lower():
                    selected_part = option.text
                    part_select.select_by_visible_text(option.text)
                    break
            
            if not selected_part:
                logger.warning(f"Could not find part '{part}' in dropdown")
                return []
            
            time.sleep(1)
            
            # Step 4: Set location to search all areas
            location_select = Select(self.driver.find_element(By.ID, "Loc"))
            location_select.select_by_visible_text("All Areas/Select an Area")
            time.sleep(1)
            
            # Step 5: Enter ZIP code if required
            try:
                zip_input = self.driver.find_element(By.NAME, "userZip")
                zip_input.clear()
                zip_input.send_keys("10001")  # Default NYC ZIP code
                time.sleep(1)
            except:
                pass  # ZIP code field might not be present
            
            # Step 6: Submit the initial form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='image']")
            submit_button.click()
            
            # Handle potential alert about ZIP code
            try:
                WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                logger.info(f"Alert appeared: {alert_text}")
                alert.accept()
                
                # If ZIP code alert, try to enter ZIP code and resubmit
                if "Zip" in alert_text or "ZIP" in alert_text:
                    zip_input = self.driver.find_element(By.NAME, "userZip")
                    zip_input.clear()
                    zip_input.send_keys("10001")
                    time.sleep(1)
                    
                    # Resubmit the form
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='image']")
                    submit_button.click()
                    
            except TimeoutException:
                # No alert appeared, continue
                pass
            
            # Wait for the intermediate selection page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Handle the intermediate page with year range selection
            return self._handle_year_range_selection(part, selected_part)
            
        except TimeoutException:
            logger.error(f"Timeout searching for Honda Insight {part}")
            return []
        except NoSuchElementException as e:
            logger.error(f"Element not found searching for Honda Insight {part}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching for Honda Insight {part}: {e}")
            return []
    
    def _handle_year_range_selection(self, part: str, selected_part: str) -> List[Vehicle]:
        """Handle the intermediate page with year range selection."""
        try:
            page_source = self.driver.page_source
            
            # Check if we got an error page
            if "INVALID SELECTION" in page_source:
                logger.warning(f"Invalid selection for Honda Insight {part}")
                return []
            
            # Check if this is the year range selection page
            if "Non-Interchange search using only Honda Insight" in page_source:
                logger.info(f"Found year range selection page for {part}")
                
                # Select the second radio button option ("Non-Interchange search using only Honda Insight")
                try:
                    radio_buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    if len(radio_buttons) >= 2:
                        # Select the second radio button
                        radio_buttons[1].click()
                        time.sleep(1)
                        
                        # Set year range to 2000-2006
                        try:
                            # Find the year range dropdowns
                            year_dropdowns = self.driver.find_elements(By.TAG_NAME, "select")
                            
                            # Look for dropdowns that contain year values
                            for dropdown in year_dropdowns:
                                options = dropdown.find_elements(By.TAG_NAME, "option")
                                option_texts = [opt.text for opt in options]
                                
                                # Check if this dropdown contains years
                                if "2000" in option_texts:
                                    # Set start year to 2000
                                    Select(dropdown).select_by_visible_text("2000")
                                    time.sleep(0.5)
                                elif "2006" in option_texts:
                                    # Set end year to 2006
                                    Select(dropdown).select_by_visible_text("2006")
                                    time.sleep(0.5)
                            
                            logger.info(f"Set year range to 2000-2006 for {part}")
                            
                        except Exception as e:
                            logger.warning(f"Could not set year range: {e}")
                        
                        # Submit the search
                        search_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='image'], input[value*='SEARCH']")
                        search_button.click()
                        
                        # Wait for results page to load
                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        
                        # Parse the results
                        return self._parse_search_results(selected_part, self.driver.page_source)
                        
                except Exception as e:
                    logger.error(f"Error handling year range selection: {e}")
                    return []
            
            # If not the year range page, parse directly
            return self._parse_search_results(selected_part, page_source)
            
        except Exception as e:
            logger.error(f"Error in year range selection: {e}")
            return []
    
    def _parse_search_results(self, part: str, page_source: str) -> List[Vehicle]:
        """Parse search results from the results page."""
        vehicles = []
        
        try:
            # Check if there are results
            if "No parts found" in page_source or "0 parts found" in page_source:
                logger.info(f"No parts found for Honda Insight {part}")
                return []
            
            # Check if this is an intermediate selection page (e.g., engine type selection)
            if "radio" in page_source and "dummyVar" in page_source:
                logger.info(f"Found intermediate selection page for Honda Insight {part}")
                return self._handle_intermediate_selection(part)
            
            # Look for result rows/listings
            # Car-Part.com results are usually in a table format
            result_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
            
            for row in result_rows:
                try:
                    # Extract data from the row
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) >= 3:  # Make sure we have enough data
                        # Extract relevant information
                        row_text = row.text.strip()
                        
                        # Skip header rows and empty rows
                        if not row_text or "Part" in row_text and "Price" in row_text:
                            continue
                        
                        # Create a vehicle entry
                        vehicle = Vehicle(
                            vin="VIN_FROM_CARPART",  # Car-Part.com might not show VINs
                            year=None,  # Will be extracted from results since we're searching all years
                            make="Honda",
                            model="Insight",
                            location=self._extract_location_from_row(row_text),
                            yard=self._extract_yard_from_row(row_text),
                            date_added=self._extract_date_from_row(row_text),
                            source_url=self.driver.current_url,
                            price=self._extract_price_from_row(row_text),
                            contact_info=self._extract_contact_from_row(row_text)
                        )
                        
                        vehicles.append(vehicle)
                        logger.debug(f"Found vehicle: {year} Honda Insight {part} - {vehicle.location}")
                
                except Exception as e:
                    logger.debug(f"Error parsing row: {e}")
                    continue
            
            # If we didn't find structured data, try to extract from page content
            if not vehicles and "Honda Insight" in page_source:
                # Create a generic entry indicating we found something
                vehicle = Vehicle(
                    vin="VIN_FROM_CARPART",
                    year=None,  # Will be extracted from individual results
                    make="Honda",
                    model="Insight",
                    location="Location from Car-Part.com",
                    yard="Various yards",
                    source_url=self.driver.current_url,
                    price="See website",
                    contact_info="Contact via Car-Part.com"
                )
                vehicles.append(vehicle)
                logger.info(f"Found listings for Honda Insight {part} on Car-Part.com")
            
            return vehicles
            
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return []
    
    def _handle_intermediate_selection(self, part: str) -> List[Vehicle]:
        """Handle intermediate selection pages (e.g., engine type selection)."""
        vehicles = []
        
        try:
            logger.info(f"Handling intermediate selection for Honda Insight {part}")
            
            # Find all radio button options
            radio_buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='dummyVar']")
            
            if not radio_buttons:
                logger.warning("No radio button options found on intermediate page")
                return []
            
            # Simplified approach: Only try the first radio button option to avoid stale element errors
            # This reduces complexity and makes the scraper more reliable
            try:
                first_radio = radio_buttons[0]
                
                # Get the label text for this radio button
                radio_id = first_radio.get_attribute("id")
                option_text = "First available option"
                
                if radio_id:
                    try:
                        label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{radio_id}']")
                        option_text = label.text.strip()
                    except:
                        pass  # Use default text if label not found
                
                logger.info(f"  Trying option: {option_text}")
                
                # Select the first radio button
                first_radio.click()
                time.sleep(1)
                
                # Submit the form
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='image']")
                submit_button.click()
                
                # Wait for the results page
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Parse the actual results
                results_html = self.driver.page_source
                
                # Check if we got actual results this time
                if "No parts found" in results_html or "0 parts found" in results_html:
                    logger.info(f"    No parts found for option: {option_text}")
                else:
                    # Parse the results
                    option_vehicles = self._parse_final_results(part, option_text, results_html)
                    vehicles.extend(option_vehicles)
                    
                    if option_vehicles:
                        logger.info(f"    Found {len(option_vehicles)} vehicles for option: {option_text}")
                
            except Exception as e:
                logger.error(f"Error processing radio button option: {e}")
            
            return vehicles
            
        except Exception as e:
            logger.error(f"Error handling intermediate selection: {e}")
            return []
    
    def _parse_final_results(self, part: str, option_text: str, page_source: str) -> List[Vehicle]:
        """Parse the final results page after selecting specific options."""
        vehicles = []
        
        try:
            # Look for the main results table (Table 5 based on our analysis)
            # The structure is: Year/Part/Model | Description | Grade | Stock# | Price | Dealer | Distance
            result_tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            # Find the table with Stock# header (usually the largest table with results)
            results_table = None
            for table in result_tables:
                header_row = table.find_element(By.TAG_NAME, "tr") if table.find_elements(By.TAG_NAME, "tr") else None
                if header_row:
                    header_text = header_row.text
                    if "Stock#" in header_text and "Price" in header_text:
                        results_table = table
                        break
            
            if not results_table:
                logger.warning("Could not find results table with Stock# header")
                return []
            
            # Get all rows except the header
            all_rows = results_table.find_elements(By.TAG_NAME, "tr")
            data_rows = all_rows[1:] if len(all_rows) > 1 else []
            
            logger.info(f"Found {len(data_rows)} data rows in results table")
            
            for i, row in enumerate(data_rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    # Expected structure: [Year/Part/Model, Description, Grade, Stock#, Price, Dealer, Distance]
                    if len(cells) >= 5:  # Need at least 5 cells for basic data
                        
                        # Extract Stock# from cell 4 (index 3)
                        stock_num = cells[3].text.strip() if len(cells) > 3 else None
                        
                        # Skip if no stock number
                        if not stock_num or stock_num in ['', '-', 'N/A']:
                            continue
                        
                        # Extract Year/Part/Model from cell 1 (index 0)
                        year_part_model = cells[0].text.strip() if len(cells) > 0 else ""
                        
                        # Extract description from cell 2 (index 1) 
                        description = cells[1].text.strip() if len(cells) > 1 else ""
                        
                        # Extract grade from cell 3 (index 2)
                        grade = cells[2].text.strip() if len(cells) > 2 else ""
                        
                        # Extract price from cell 5 (index 4)
                        price = cells[4].text.strip() if len(cells) > 4 else ""
                        
                        # Extract dealer info from cell 6 (index 5)
                        dealer_info = cells[5].text.strip() if len(cells) > 5 else ""
                        
                        # Extract distance from cell 7 (index 6)
                        distance = cells[6].text.strip() if len(cells) > 6 else ""
                        
                        # Parse location and contact from dealer info
                        location = self._extract_location_from_dealer_info(dealer_info)
                        contact_info = self._extract_contact_from_dealer_info(dealer_info)
                        yard = self._extract_yard_from_dealer_info(dealer_info)
                        
                        # Create vehicle entry with Stock# as VIN
                        vehicle = Vehicle(
                            vin=stock_num,  # Use Stock# as unique identifier
                            year=self._extract_year_from_cell(year_part_model),
                            make="Honda",
                            model="Insight",
                            location=location,
                            yard=yard,
                            date_added=None,  # Car-Part.com doesn't show dates typically
                            source_url=self.driver.current_url,
                            price=self._clean_price(price),
                            contact_info=contact_info
                        )
                        
                        vehicles.append(vehicle)
                        logger.debug(f"Found vehicle: Stock#{stock_num} - {price} - {location}")
                
                except Exception as e:
                    logger.debug(f"Error parsing result row {i}: {e}")
                    continue
            
            return vehicles
            
        except Exception as e:
            logger.error(f"Error parsing final results: {e}")
            return []
    
    def _extract_year_from_cell(self, year_part_model: str) -> Optional[str]:
        """Extract year from the year/part/model cell."""
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', year_part_model)
        return year_match.group(0) if year_match else None
    
    def _extract_location_from_dealer_info(self, dealer_info: str) -> Optional[str]:
        """Extract location from dealer info cell."""
        if not dealer_info:
            return None
        
        # Look for location patterns in dealer info
        import re
        location_patterns = [
            r'([A-Z][a-z]+,\s*[A-Z]{2})',  # City, State
            r'([A-Z]{2}\s+\d{5})',         # State ZIP
            r'([A-Z][a-z]+\s+[A-Z]{2})',   # City State
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, dealer_info)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_contact_from_dealer_info(self, dealer_info: str) -> Optional[str]:
        """Extract contact info from dealer info cell."""
        if not dealer_info:
            return None
        
        # Look for phone numbers
        import re
        contact_patterns = [
            r'(\(\d{3}\)\s*\d{3}-\d{4})',
            r'(\d{3}-\d{3}-\d{4})',
            r'(\d{3}\.\d{3}\.\d{4})',
        ]
        
        for pattern in contact_patterns:
            match = re.search(pattern, dealer_info)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_yard_from_dealer_info(self, dealer_info: str) -> Optional[str]:
        """Extract yard/business name from dealer info cell."""
        if not dealer_info:
            return None
        
        # Look for business name patterns
        import re
        yard_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Auto|Salvage|Parts|Recycling))',
            r'([A-Z&][A-Za-z\s&]+(?:Auto|Salvage|Parts|Recycling))',
            r'Call\s+([A-Z][A-Za-z\s]+)',
        ]
        
        for pattern in yard_patterns:
            match = re.search(pattern, dealer_info)
            if match:
                return match.group(1).strip()
        
        # If no specific pattern, take first line of dealer info
        lines = dealer_info.split('\n')
        if lines and len(lines[0].strip()) > 0:
            return lines[0].strip()
        
        return None
    
    def _clean_price(self, price: str) -> Optional[str]:
        """Clean and format price string."""
        if not price:
            return None
        
        price = price.strip()
        if price in ['', '-', 'N/A', 'Call']:
            return price if price == 'Call' else None
        
        # Ensure price starts with $
        if price and not price.startswith('$'):
            price = f"${price}"
        
        return price
    
    def _extract_location_from_row(self, row_text: str) -> Optional[str]:
        """Extract location from a result row."""
        # Look for common location patterns
        import re
        location_patterns = [
            r'([A-Z][a-z]+,\s*[A-Z]{2})',  # City, State
            r'([A-Z]{2}\s+\d{5})',         # State ZIP
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, row_text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_yard_from_row(self, row_text: str) -> Optional[str]:
        """Extract yard/business name from a result row."""
        # Look for business name patterns
        import re
        yard_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Auto|Salvage|Parts|Recycling))',
            r'([A-Z&][A-Za-z\s&]+(?:Auto|Salvage|Parts|Recycling))',
        ]
        
        for pattern in yard_patterns:
            match = re.search(pattern, row_text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_date_from_row(self, row_text: str) -> Optional[str]:
        """Extract date from a result row."""
        # Look for date patterns
        import re
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4})',
            r'(\d{1,2}-\d{1,2}-\d{2,4})',
            r'(\w{3}\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, row_text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_price_from_row(self, row_text: str) -> Optional[str]:
        """Extract price from a result row."""
        # Look for price patterns
        import re
        price_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*\$',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, row_text)
            if match:
                return f"${match.group(1)}"
        
        return None
    
    def _extract_contact_from_row(self, row_text: str) -> Optional[str]:
        """Extract contact info from a result row."""
        # Look for phone numbers
        import re
        contact_patterns = [
            r'(\(\d{3}\)\s*\d{3}-\d{4})',
            r'(\d{3}-\d{3}-\d{4})',
            r'(\d{3}\.\d{3}\.\d{4})',
        ]
        
        for pattern in contact_patterns:
            match = re.search(pattern, row_text)
            if match:
                return match.group(1)
        
        return None 