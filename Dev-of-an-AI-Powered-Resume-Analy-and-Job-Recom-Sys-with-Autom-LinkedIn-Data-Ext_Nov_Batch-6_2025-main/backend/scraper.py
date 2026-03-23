import os
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    StaleElementReferenceException,
    ElementClickInterceptedException
)

from dotenv import load_dotenv

# Import our backend components
# Note: These imports assume the package structure is set up correctly.
# If running this script directly, you might need to adjust python path.
try:
    from backend.llm_analyzer import LLMAnalyzer
    from utils.database import save_job_listings, get_skills_gap_analysis, get_user_analysis, check_job_exists
except ImportError:
    # Fallback for direct execution/testing
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.llm_analyzer import LLMAnalyzer
    from utils.database import save_job_listings, get_skills_gap_analysis, get_user_analysis, check_job_exists

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# WebDriver Setup
# --------------------------------------------------
def get_driver(headless=True, user_agent=None):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")

    if user_agent:
        options.add_argument(f"user-agent={user_agent}")
    else:
        # Default modern user agent
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Path to chromedriver - read from environment variable (CHROMEDRIVER_PATH)
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "").strip()
    if chromedriver_path:
        # Use provided chromedriver binary
        if os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            logger.warning(f"CHROMEDRIVER_PATH is set to '{chromedriver_path}' but file does not exist. Falling back to system chromedriver on PATH.")
            driver = webdriver.Chrome(options=options)
    else:
        # No path provided — use chromedriver from PATH
        driver = webdriver.Chrome(options=options)

    return driver

# --------------------------------------------------
# Utilities
# --------------------------------------------------
def human_typing(element, text):
    """Simulate human typing with random delays."""
    for ch in text:
        element.send_keys(ch)
        time.sleep(random.uniform(0.05, 0.15))
    time.sleep(random.uniform(0.3, 0.6))

def random_sleep(min_seconds=1.0, max_seconds=2.0):
    time.sleep(random.uniform(min_seconds, max_seconds))

# --------------------------------------------------
# LinkedIn Scraper Class
# --------------------------------------------------
class LinkedInJobScraper:
    def __init__(self, user_id=None, headless=None):
        self.user_id = user_id
        
        # Determine headless mode: Argument > Env Var > Default (True)
        if headless is None:
            headless_env = os.getenv("CHROME_HEADLESS", "true").lower()
            headless = headless_env == "true"
            
        self.driver = get_driver(headless=headless)
        self.wait = WebDriverWait(self.driver, 20)
        self.llm_analyzer = LLMAnalyzer()
        self.base_url = "https://www.linkedin.com"
        
    def login(self, email, password):
        """Login to LinkedIn."""
        logger.info(f"Logging in as {email}...")
        try:
            self.driver.get(f"{self.base_url}/login")
            
            email_elem = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            human_typing(email_elem, email)
            
            pass_elem = self.driver.find_element(By.ID, "password")
            human_typing(pass_elem, password)
            
            pass_elem.send_keys(Keys.RETURN)
            
            # Wait for feed or challenge
            try:
                WebDriverWait(self.driver, 15).until(EC.url_contains("/feed"))
                logger.info("Login successful.")
                return True
            except TimeoutException:
                if "checkpoint" in self.driver.current_url:
                    logger.warning("LinkedIn security checkpoint detected. Manual intervention required.")
                    input("Press Enter after solving the CAPTCHA in the browser...")
                    return True
                logger.error("Login failed or timed out.")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def search_jobs(self, keywords: str, location: str, limit: int = 50, filters: Optional[Dict[str, Any]] = None, progress_callback=None):
        """
        Navigate to jobs page and search with filters.
        
        Args:
            keywords: e.g. "Software Engineer Python"
            location: e.g. "San Francisco, CA"
            limit: Max jobs to scrape
            filters: Dict with optional keys:
                - date_posted: "24h", "week", "month"
                - experience: list of ["internship", "entry", "associate", "mid_senior", "director", "executive"]
                - job_type: list of ["full_time", "contract", "part_time", "temporary", "internship", "volunteer", "other"]
                - remote: list of ["on_site", "remote", "hybrid"]
            progress_callback: Optional function(scraped_count, total_limit, time_remaining_str)
        """
        logger.info(f"Searching for '{keywords}' in '{location}' with filters: {filters}")
        
        # Base query params
        query_params = {
            "keywords": keywords,
            "location": location,
        }
        
        # Helper to map filters to LinkedIn URL params
        if filters:
            # Date Posted (f_TPR)
            date_map = {"24h": "r86400", "week": "r604800", "month": "r2592000"}
            if filters.get("date_posted") in date_map:
                query_params["f_TPR"] = date_map[filters["date_posted"]]
                
            # Experience Level (f_E)
            exp_map = {
                "internship": "1", "entry": "2", "associate": "3", 
                "mid_senior": "4", "director": "5", "executive": "6"
            }
            if filters.get("experience"):
                # Handle single string or list
                exps = filters["experience"] if isinstance(filters["experience"], list) else [filters["experience"]]
                codes = [exp_map[e] for e in exps if e in exp_map]
                if codes:
                    query_params["f_E"] = ",".join(codes)
                    
            # Remote Filter (f_WT)
            remote_map = {"on_site": "1", "remote": "2", "hybrid": "3"}
            if filters.get("remote"):
                remotes = filters["remote"] if isinstance(filters["remote"], list) else [filters["remote"]]
                codes = [remote_map[r] for r in remotes if r in remote_map]
                if codes:
                    query_params["f_WT"] = ",".join(codes)

            # Job Type (f_JT)
            type_map = {
                "full_time": "F", "part_time": "P", "contract": "C", 
                "temporary": "T", "internship": "I", "volunteer": "V", "other": "O"
            }
            if filters.get("job_type"):
                types = filters["job_type"] if isinstance(filters["job_type"], list) else [filters["job_type"]]
                codes = [type_map[t] for t in types if t in type_map]
                if codes:
                    query_params["f_JT"] = ",".join(codes)

        # Construct URL
        query_string = urllib.parse.urlencode(query_params, safe=",")
        search_url = f"{self.base_url}/jobs/search/?{query_string}"
        
        logger.info(f"Navigating to: {search_url}")
        self.driver.get(search_url)
        random_sleep(1, 2)
        
        return self._scrape_job_list(limit, search_location=location, progress_callback=progress_callback)

    def _scrape_job_list(self, limit: int, search_location: str = None, progress_callback=None) -> List[Dict]:
        """Iterate through job list and extract details."""
        scraped_jobs = []
        page = 1
        start_time = time.time()
        
        while len(scraped_jobs) < limit:
            logger.info(f"Scraping page {page}, collected {len(scraped_jobs)}/{limit} jobs...")
            
            # Wait for job list to load
            try:
                # Common selectors for job cards
                # These classes change frequently. Using clearer attributes if available.
                job_card_selector = ".job-card-container, li.jobs-search-results__list-item"
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, job_card_selector)))
                
                # Scroll the list to load ALL lazy-loaded elements on the current page
                job_list_container = self.driver.find_elements(By.CSS_SELECTOR, ".jobs-search-results-list")
                
                if job_list_container:
                    container = job_list_container[0]
                    # Force strict scrolling to load all items (approx 25)
                    for _ in range(4):
                        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", container)
                        time.sleep(1.5)
                else:
                    # Fallback for full page generic scroll - try multiple scrolls
                    for _ in range(5):
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)

                random_sleep(1, 2)
                
                # Find all fully loaded job cards
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, job_card_selector)
                logger.info(f"Found {len(job_cards)} job cards on page {page}")
                
                # STRICT PROCESSING LOGIC: Process jobs on this page up to 25
                processed_on_this_page = 0
                MAX_PER_PAGE = 25
                
                processed_urls_on_page = set()
                
                for i, card in enumerate(job_cards):
                    if len(scraped_jobs) >= limit:
                        break
                        
                    if processed_on_this_page >= MAX_PER_PAGE:
                        logger.info(f"Reached limit of {MAX_PER_PAGE} jobs for page {page}. Moving to next.")
                        break

                    try:
                        # Optimization: Check if job exists BEFORE clicking
                        # Try to extract URL from the visible card
                        try:
                            # Typically the title itself is a link, or inside the card
                            link_elem = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title, .job-card-container__link")
                            pre_url = link_elem.get_attribute("href").split('?')[0]
                            
                            if pre_url in processed_urls_on_page:
                                continue
                                
                            if self.user_id and check_job_exists(self.user_id, pre_url):
                                logger.info(f"Skipping already scraped job: {pre_url}")
                                processed_on_this_page += 1 # Count as processed to advance logic
                                continue
                                
                            processed_urls_on_page.add(pre_url)
                        except:
                            # If we can't get URL easily, we proceed to click and check later
                            pass

                        # Scroll the individual card into view to ensure it's clickable
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", card)
                        random_sleep(0.3, 0.6)
                        
                        # Click to load details
                        try:
                            card.click()
                        except ElementClickInterceptedException:
                            self.driver.execute_script("arguments[0].click();", card)
                            
                        # Wait for details to load
                        random_sleep(0.8, 1.5) 
                        
                        # Extract basic info (refresh reference in case of stale element)
                        try:
                             title_elem = self.driver.find_elements(By.CSS_SELECTOR, ".job-card-list__title, strong")[i] 
                        except:
                             # Fallback relative to card if still valid or just assume it's the active one
                             title_elem = card.find_element(By.CSS_SELECTOR, ".job-card-list__title, strong")
                             
                        job_title = title_elem.text.strip()

                        # Parse details
                        job_details = self._extract_job_details_pane(job_title, search_location=search_location)
                        
                        if job_details:
                            # Double check URL after extraction if we missed it before
                            final_url = job_details.get("job_url")
                            if final_url and (self.user_id and check_job_exists(self.user_id, final_url)):
                                 logger.info("Skipping existing job (confirmed after click).")
                                 processed_on_this_page += 1
                                 continue
                            
                            # Use LLM to structure the description
                            logger.info(f"Parsing description for: {job_title}")
                            parsed_data = self.llm_analyzer.parse_job_description(job_details['raw_description'])
                            
                            # Merge parsed data
                            if "error" not in parsed_data:
                                job_details["job_analysis"] = parsed_data
                            
                            scraped_jobs.append(job_details)
                            processed_on_this_page += 1
                            
                            # Save immediately to DB if user_id is set
                            if self.user_id:
                                save_job_listings(self.user_id, [job_details])
                                
                            # Progress Update with ETA
                            elapsed = time.time() - start_time
                            count = len(scraped_jobs)
                            if count > 0:
                                avg_time = elapsed / count
                                remaining = limit - count
                                eta_seconds = int(remaining * avg_time)
                                eta_str = f"{eta_seconds // 60}m {eta_seconds % 60}s"
                            else:
                                eta_str = "Calculating..."
                                
                            if progress_callback:
                                progress_callback(count, limit, eta_str)

                    except Exception as e:
                        logger.warning(f"Failed to scrape a job card: {e}")
                        continue
                
                # Pagination Logic
                if len(scraped_jobs) >= limit:
                    break
                    
                if page >= 10: 
                    logger.info("Reached maximum page limit (10). Stopping.")
                    break

                # Look for "Next" button
                try:
                    next_selectors = [
                        "button[aria-label*='Next']",
                        ".artdeco-pagination__button--next",
                        "button.artdeco-pagination__button--next",
                        f"button[aria-label='Page {page+1}']"
                    ]
                    
                    next_button = None
                    for selector in next_selectors:
                        try:
                            next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if next_button:
                                break
                        except:
                            continue
                            
                    if not next_button:
                        raise NoSuchElementException("Next button not found")

                    self.driver.execute_script("arguments[0].scrollIntoView();", next_button)
                    time.sleep(0.5)
                    try:
                        next_button.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", next_button)

                    page += 1
                    logger.info(f"Navigating to page {page}...")
                    random_sleep(2, 4)
                except NoSuchElementException:
                    logger.info("No next page button found. Scrape complete.")
                    break


                    
            except TimeoutException:
                logger.warning("Timeout waiting for job list.")
                break
            except Exception as e:
                logger.error(f"Error during scraping loop: {e}")
                # Don't break immediately, try to recover or move to next page
                try:
                     # Try to scroll a bit to unfreeze/change state
                     self.driver.execute_script("window.scrollBy(0, 100);")
                except:
                     pass
                continue # Continue the outer loop (re-finding elements) instead of breaking
                
        return scraped_jobs

    def _extract_job_details_pane(self, job_title_fallback, search_location=None):
        """Extract info from the right-hand details pane."""
        try:
            # Wait for details container
            details_selector = ".jobs-search__job-details--container, .job-view-layout"
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, details_selector)))
            
            # URL
            try:
                # Sometimes the URL is in a 'share' button or the title link in the pane
                link_elem = self.driver.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__job-title a, .jobs-unified-top-card__job-title a")
                job_url = link_elem.get_attribute("href").split('?')[0] # Clean URL
            except Exception:
                job_url = self.driver.current_url # Fallback
            
            # Company
            try:
                company = self.driver.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name").text.strip()
            except Exception:
                company = "Unknown"
                
            # Location & Date Extraction
            try:
                # Strategy 1: Look for the primary description block (Company · Location · Date)
                primary_desc = self.driver.find_elements(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__primary-description-container, .job-details-jobs-unified-top-card__primary-description, .jobs-unified-top-card__primary-description")
                
                location = "Unknown"
                posted_date_str = None
                
                if primary_desc:
                    full_text = primary_desc[0].text
                    parts = [p.strip() for p in full_text.split('·')]
                    
                    for part in parts:
                        # Skip if it is the company name (fuzzy match)
                        if company != "Unknown" and company.lower() in part.lower():
                            continue
                        
                        # Check if it looks like a date
                        lower_part = part.lower()
                        if any(k in lower_part for k in ["ago", "hour", "minute", "day", "week", "month", "year", "reposted"]):
                            posted_date_str = part
                            continue
                            
                        # If not company and not date, likely location
                        if location == "Unknown":
                            location = part
                
                # Strategy 2: Fallbacks if not found
                if location == "Unknown":
                    location_selectors = [
                        ".job-details-jobs-unified-top-card__bullet",
                        ".jobs-unified-top-card__bullet",
                        "span.tvm__text--low-emphasis", # Common for meta-data
                        ".job-details-jobs-unified-top-card__workplace-type" 
                    ]
                    for selector in location_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for el in elements:
                                text = el.text.strip()
                                # Filter out common non-location text like "Apply" or numbers
                                if text and len(text) > 2 and not text[0].isdigit():
                                    # Helper check for time
                                    lower_text = text.lower()
                                    if any(k in lower_text for k in ["ago", "hour", "minute", "day", "week", "month", "year", "reposted"]):
                                        continue
                                        
                                    if location == "Unknown": 
                                         location = text
                                         break
                        except Exception:
                           continue

                # Date fallback if not found in primary block
                if not posted_date_str:
                    try:
                        # Try finding separate date element
                        date_elem = self.driver.find_elements(By.CSS_SELECTOR, ".tvm__text--low-emphasis, .job-details-jobs-unified-top-card__posted-date")
                        for el in date_elem:
                            text = el.text.strip()
                            if any(k in text.lower() for k in ["ago", "hour", "minute", "day", "week", "month"]):
                                posted_date_str = text
                                break
                    except Exception:
                        pass

            except Exception:
                location = "Unknown"
                posted_date_str = None

            # Applicant Count Extraction
            applicant_count = 0
            try:
                # Strategy 1: Specific Selectors
                app_selectors = [
                    ".job-details-jobs-unified-top-card__applicant-count",
                    ".jobs-unified-top-card__applicant-count",
                    ".jobs-unified-top-card__bullet",
                    ".tvm__text--low-emphasis", 
                    ".job-details-jobs-unified-top-card__primary-description",
                    ".job-details-jobs-unified-top-card__subtitle" # Often contains the full metadata string
                ]
                
                found_app = False
                for selector in app_selectors:
                    if found_app: break
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for el in elements:
                            text = el.text.strip().lower()
                            
                            # 1. "Over 100 people clicked apply" or "25 applicants"
                            # Regex to capture: number followed by variations
                            # Patterns to match:
                            # 100 applicants
                            # over 100 applicants
                            # 50 people clicked apply
                            # over 50 people clicked apply
                            
                            if "applicant" in text or "people clicked apply" in text:
                                # Remove commas from numbers first
                                clean_text = text.replace(',', '')
                                
                                # Pattern 1: Direct "applicant" association
                                match = re.search(r'(?:over\s+)?(\d+)\s*(?:applicants|people clicked apply)', clean_text)
                                if match:
                                    applicant_count = int(match.group(1))
                                    found_app = True
                                    break
                                
                                # Pattern 2: "· 145 applicants" (bullet point style)
                                match = re.search(r'·\s*(\d+)\s*(?:applicants|people)', clean_text)
                                if match:
                                    applicant_count = int(match.group(1))
                                    found_app = True
                                    break

                    except: continue
            except Exception:
                pass


            # Convert relative date to actual timestamp
            posted_date = datetime.now()
            if posted_date_str:
                posted_date = self._parse_relative_date(posted_date_str)
            
            # Formating date for DB (YYYY-MM-DD HH:MM:SS)
            formatted_date = posted_date.strftime('%Y-%m-%d %H:%M:%S')

            # Full Description
            try:
                description_box = self.driver.find_element(By.ID, "job-details")
                description = description_box.text.strip()
                
                # Check for "Show more" button in description
                try:
                    show_more = description_box.find_element(By.CSS_SELECTOR, "button[aria-label*='Show more']")
                    show_more.click()
                    random_sleep(0.5, 1)
                    description = description_box.text.strip()
                except Exception:
                    pass
            except Exception:
                description = ""
                
            return {
                "job_title": job_title_fallback,
                "company_name": company,
                "location": location,
                "job_description": description, # Used for storage
                "raw_description": description, # Used for LLM
                "job_url": job_url,
                "match_percentage": 0, # To be calculated later
                "posted_date": formatted_date,
                "applicant_count": applicant_count
            }
            
        except Exception as e:
            logger.error(f"Error extracting job details pane: {e}")
            return None

    def _parse_relative_date(self, relative_str: str) -> datetime:
        """Convert relative time string (e.g. '2 days ago') to datetime object."""
        try:
            now = datetime.now()
            relative_str = relative_str.lower().strip()
            
            # Handle "Reposted" prefix
            relative_str = relative_str.replace("reposted", "").strip()
            
            # Regex to find number and unit
            match = re.search(r'(\d+)\s+(minute|hour|day|week|month)', relative_str)
            if not match:
                return now
                
            amount = int(match.group(1))
            unit = match.group(2)
            
            if "minute" in unit:
                return now - timedelta(minutes=amount)
            elif "hour" in unit:
                return now - timedelta(hours=amount)
            elif "day" in unit:
                return now - timedelta(days=amount)
            elif "week" in unit:
                return now - timedelta(weeks=amount)
            elif "month" in unit:
                # Approximation
                return now - timedelta(days=amount*30)
                
            return now
        except:
            return datetime.now()


    def scrape_recommended_jobs(self, user_id: int, limit: int = 10):
        """
        Automatically scrape jobs based on user's profile.
        """
        logger.info(f"Starting automated scrape for user {user_id}...")
        
        # 1. Try to get target role from gap analysis
        gap_analysis = get_skills_gap_analysis(user_id)
        # gap_analysis might be a list or direct dict depending on my earlier check
        # The DB function returns a list if limit > 1, or single item/None if limit=1. 
        # But wait, get_skills_gap_analysis signature in db.py: def get_skills_gap_analysis(user_id, limit=1...)
        # It returns results[0] if limit=1.
        
        target_role = None
        if gap_analysis:
            target_role = gap_analysis.get("target_role")
            
        # 2. If no target role, try to infer from resume analysis
        if not target_role:
            analysis = get_user_analysis(user_id)
            if analysis:
                # Naive inference: pop top skill or use a default
                # Ideally we'd ask LLM to infer job title from resume text, 
                # but for now let's assume if they haven't done gap analysis they might just want general "Software" jobs
                # or use the first technical skill
                skills = analysis.get("skills", {})
                tech_skills = skills.get("technical_skills", [])
                if tech_skills:
                    target_role = f"{tech_skills[0]} Developer"
        
        # 3. Default
        if not target_role:
            target_role = "Software Engineer"
            
        logger.info(f"inferred search keywords: {target_role}")
        
        # Location preference - placeholder (could be stored in user profile)
        location = "Remote" 
        
        # Execute search
        return self.search_jobs(target_role, location, limit=limit, filters={"remote": ["remote", "hybrid"]})

    def close(self):
        if self.driver:
            self.driver.quit()

# --------------------------------------------------
# Main Execution (Testing)
# --------------------------------------------------
if __name__ == "__main__":
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    if not email or not password:
        logger.error("Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD env vars.")
        exit(1)
        
    scraper = LinkedInJobScraper(user_id=1)
    try:
        if scraper.login(email, password):
            jobs = scraper.search_jobs("Python Developer", "Remote", limit=5)
            logger.info(f"Scraped {len(jobs)} jobs.")

    finally:
        scraper.close()
