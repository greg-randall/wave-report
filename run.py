#!/usr/bin/env python3

"""
wave_scanner.py

This script automates accessibility testing using the WAVE WebAIM tool.
It reads a list of URLs from 'urls.txt', visits the WAVE report page for each URL,
scrapes the accessibility report data (errors, contrast errors, alerts, etc.),
takes a screenshot of the report, and saves the results to 'results.csv'
and 'results.jsonl'.
"""

# TASK: Create main script file and add imports
import asyncio
import csv
import json
import re
import logging
import datetime
from pathlib import Path
import argparse  # Added for command-line arguments
import random    # Added for random sleep
import uuid
from tqdm import tqdm  # Added for progress bars
from PIL import Image  # Added for WebP conversion


# Import nodriver
try:
    import nodriver as uc
except ImportError:
    print("Error: 'nodriver' library not found.")
    print("Please install it using: pip install nodriver")
    exit(1)


# TASK: Define utility function to sanitize filenames
def sanitize_filename(url: str) -> str:
    """
    Removes protocol and replaces invalid filename characters from a URL.
    """
    # Remove protocol
    s = re.sub(r"https?://", "", url)
    # Replace invalid characters with an underscore
    s = re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)
    return s


# TASK: Define utility function to read URLs
def get_urls(filename: str) -> list[str]:
    """
    Reads a list of URLs from a text file, one URL per line.
    """
    urls = []
    try:
        with open(filename, "r") as f:
            lines = f.readlines()
            # Strip whitespace and filter out empty lines
            urls = [line.strip() for line in lines if line.strip()]
    except FileNotFoundError:
        logging.error(f"Input file not found: {filename}")
        return []
    return urls


# TASK: Define utility function to write CSV header
# TASK: Define utility function to write CSV header
def initialize_csv(filename: str):
    """
    Checks if a CSV file exists. If not, creates it and writes the header.
    """
    # Use Pathlib to check if the file exists
    csv_file = Path(filename)
    
    if csv_file.exists():
        # If it exists, do nothing.
        logging.info(f"CSV file '{filename}' already exists. Appending results.")
        return

    # If it does not exist, create it and write the header
    logging.info(f"CSV file '{filename}' not found. Creating new file with header.")
    header = [
        'url', 'timestamp', 'timestamp_h', 'screenshot_file', 'Errors',
        'Contrast Errors', 'Alerts', 'Features', 'Structure', 'ARIA', 'AIM Score'
    ]
    try:
        # Use "w" mode (write) ONLY for this initial creation
        with open(csv_file, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    except IOError as e:
        logging.error(f"Failed to create and initialize CSV file {filename}: {e}")

# TASK: Define utility function to append JSONL data
def save_to_jsonl(filename: str, data: dict):
    """
    Appends a single JSON object as a new line to a .jsonl file.
    """
    try:
        with open(filename, "a", encoding='utf-8') as f:
            json_string = json.dumps(data)
            f.write(json_string + "\n")
    except IOError as e:
        logging.error(f"Failed to save to JSONL file {filename}: {e}")


# TASK: Define utility function to append CSV data
def save_to_csv(filename: str, data: dict):
    """
    Appends a single row of data to the CSV file.
    """
    # First, flatten the 'results' list into a dictionary for easy lookup
    flat_results = {}
    for item in data.get('results', []):
        # Use the label directly as the key
        label = item.get('label', '').strip()
        if not label:
            continue
        
        if 'count' in item:
            flat_results[label] = item['count']
        elif 'value' in item:
            flat_results[label] = item['value']
            
    # Define the exact order of columns, matching initialize_csv
    header = [
        'url', 'timestamp', 'timestamp_h', 'screenshot_file', 'Errors',
        'Contrast Errors', 'Alerts', 'Features', 'Structure', 'ARIA', 'AIM Score'
    ]

    # Build the row using .get() to avoid errors for missing keys
    row = [
        data.get('url', ''),
        data.get('timestamp', ''),
        data.get('timestamp_h', ''),
        data.get('screenshot_file', ''),
        flat_results.get('Errors', 0),
        flat_results.get('Contrast Errors', 0),
        flat_results.get('Alerts', 0),
        flat_results.get('Features', 0),
        flat_results.get('Structure', 0),
        flat_results.get('ARIA', 0),
        # --- REVERTED FIX ---
        # Now we look for "AIM Score" (no colon) again
        flat_results.get('AIM Score', 0.0)
        # --- END OF FIX ---
    ]

    try:
        with open(filename, "a", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except IOError as e:
        logging.error(f"Failed to save to CSV file {filename}: {e}")


# TASK: Create the main async processing function `process_url`
async def process_url(
    tab: uc.Tab, 
    url: str, 
    min_sleep: int, 
    max_sleep: int,
    run_unix_ts: int,    # <-- ADDED
    run_human_ts: str    # <-- ADDED
) -> dict | None:
    """
    Processes a single URL: navigates to WAVE, waits for results,
    takes a screenshot, and scrapes the accessibility data.
    """
    try:
        # TASK: `process_url`: Navigate and set viewport
        wave_url = f"https://wave.webaim.org/report#/{url}"
        await tab.get(wave_url)

        # --- NEW: Wait random time for page to settle ---
        # Wait a random amount of time after loading the page,
        # but before we start scraping.
        sleep_duration = random.randint(min_sleep, max_sleep)
        logging.info(f"Waiting {sleep_duration}s for page to settle...")
        await asyncio.sleep(sleep_duration)
        # --- END NEW ---
        
        # Set a standard desktop viewport
        await tab.send(uc.cdp.emulation.set_device_metrics_override(
            width=1920,
            height=1080,
            device_scale_factor=1,
            mobile=False
        ))

        # TASK: `process_url`: Wait for report to load
        # Step 1: Wait for the AIM score value to be present (max 60s)
        # This confirms the analysis is complete and data is available.
        logging.info(f"Waiting for AIM score for {url}...")
        await tab.select("span#aim-score-value", timeout=60)
        logging.info(f"AIM score found for {url}.")


        # --- MODIFIED SECTION ---
        # Step 2: Manually poll for the spinner to disappear
        logging.info(f"Waiting for spinner to disappear for {url}...")
        try:
            timeout = 30  # 30 seconds timeout
            start_time = asyncio.get_event_loop().time()
            spinner_gone = False
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # Check if the element exists at all
                spinner = await tab.query_selector("#wave5_loading")
                
                if not spinner:
                    # It's gone from the DOM
                    spinner_gone = True
                    break
                
                # If it exists, check its display style
                try:
                    display_style = await spinner.style.get_property_value('display')
                    if display_style == 'none':
                        # It's hidden
                        spinner_gone = True
                        break
                except Exception:
                    # Style property might not be accessible yet, just means it's not 'none'
                    pass
                    
                await asyncio.sleep(0.5)  # Poll every 500ms

            if spinner_gone:
                logging.info(f"Spinner is gone for {url}.")
                # Step 3: Add a 1-second delay just to be safe
                logging.info("Waiting 1 extra second for rendering...")
                await asyncio.sleep(1)
            else:
                logging.warning(f"Spinner did NOT disappear for {url} after {timeout}s. Taking screenshot anyway.")

        except Exception as e:
            # This is not critical.
            logging.warning(f"Spinner check failed for {url}, proceeding anyway... ({e})")
        # --- END MODIFIED SECTION ---

        # TASK: `process_url`: Generate timestamps and screenshot paths
        # --- MODIFIED: Use the timestamp passed from main ---
        sanitized_url = sanitize_filename(url)
        
        # Use the run's unix timestamp for the filename
        screenshot_filename = f"{run_unix_ts}_{sanitized_url}_{uuid.uuid4()}.png"
        screenshot_path = Path("screenshots") / screenshot_filename
        # --- END MODIFIED ---

        # TASK: `process_url`: Take and save screenshot
        # Step 4: Take the screenshot
        await tab.save_screenshot(screenshot_path, format='png')
        # --- END MODIFIED ---

        # TASK: `process_url`: Extract data using selectors
        results_list = []

        # TASK: `process_url`: Repeat data extraction for all list items
        
        # 1. Errors
        errors_text = (await tab.select("li#error span")).text
        results_list.append({"label": "Errors", "count": int(errors_text)})
        
        # 2. Contrast Errors
        contrast_text = (await tab.select("li#contrastnum span")).text
        results_list.append({"label": "Contrast Errors", "count": int(contrast_text)})
        
        # 3. Alerts
        alerts_text = (await tab.select("li#alert span")).text
        results_list.append({"label": "Alerts", "count": int(alerts_text)})
        
        # 4. Features
        features_text = (await tab.select("li#feature span")).text
        results_list.append({"label": "Features", "count": int(features_text)})
        
        # 5. Structure
        structure_text = (await tab.select("li#structure span")).text
        results_list.append({"label": "Structure", "count": int(structure_text)})
        
        # 6. ARIA
        aria_text = (await tab.select("li#aria span")).text
        results_list.append({"label": "ARIA", "count": int(aria_text)})

        # TASK: `process_url`: Extract AIM score
        aim_label = (await tab.select("span#aim-score-label")).text
        aim_value = (await tab.select("span#aim-score-value")).text
        
        # --- THIS IS THE FIX ---
        # Strip whitespace AND remove the colon from the label
        clean_label = aim_label.strip().replace(":", "")
        # --- END OF FIX ---
        
        results_list.append({
            "label": clean_label, # This will be "AIM Score"
            "value": float(aim_value)
        })

        # TASK: `process_url`: Package and return final data
        # --- MODIFIED: Use passed-in timestamps ---
        return {
            "url": url,
            "timestamp": run_unix_ts,
            "timestamp_h": run_human_ts,
            "screenshot_file": str(screenshot_path),
            "results": results_list
        }
        # --- END MODIFIED ---

    except Exception as e:
        # Catch-all for any error during processing (timeout, element not found, etc.)
        logging.error(f"Failed to process {url}: {e}")
        return None


# TASK: Create the main async function

# TASK: Create the main async function
async def main(min_sleep: int, max_sleep: int):
    """
    Main function to initialize, run the browser, and process all URLs.
    """
    # TASK: `main`: Initialize browser and environment
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create screenshots directory if it doesn't exist
    Path("screenshots").mkdir(exist_ok=True)
    
    # Create/overwrite CSV file with header
    initialize_csv('results.csv')
    
    # Get URLs to process
    urls = get_urls('urls.txt')
    if not urls:
        logging.error("No URLs found in urls.txt. Exiting.")
        return

    # TASK: `main`: Start browser and get tab
    logging.info("Starting browser...")
    
    # --- MODIFIED SECTION ---
    try:
        # Try to start the browser. nodriver will try to find Chrome automatically.
        browser = await uc.start()
    except FileNotFoundError:
        logging.error("=" * 60)
        logging.error("! Google Chrome Not Found !")
        logging.error("This script needs Google Chrome or Chromium to work.")
        logging.error("Please download and install Google Chrome here:")
        logging.error("  https://www.google.com/chrome/")
        logging.error("\nIf you already have Chrome, but it's in a custom folder,")
        logging.error("you can edit this script. Find this line:")
        logging.error("  browser = await uc.start()")
        logging.error("And change it to point to your Chrome app, like this:")
        logging.error("  browser = await uc.start(browser_executable_path=r'C:\\path\\to\\chrome.exe')")
        logging.error("=" * 60)
        return  # Stop the script
    except Exception as e:
        logging.error(f"An unexpected error occurred while starting the browser: {e}")
        return  # Stop the script
    # --- END MODIFIED SECTION ---
    
    tab = browser.main_tab
    logging.info(f"Starting scan for {len(urls)} URLs...")

    # --- NEW: Generate a single timestamp for this entire run ---
    run_datetime = datetime.datetime.now(datetime.timezone.utc)
    run_unix_ts = int(run_datetime.timestamp())
    run_human_ts = run_datetime.strftime("%m/%d/%Y %I:%M %p")
    logging.info(f"Using run timestamp: {run_human_ts} (UTC)")
    # --- END NEW ---

    # TASK: `main`: Loop and process URLs
    for url in urls:
        logging.info(f"Processing {url}...")
        # Pass the sleep times and timestamps into the processing function
        # --- MODIFIED: Pass timestamps ---
        data = await process_url(
            tab, 
            url, 
            min_sleep, 
            max_sleep,
            run_unix_ts,    # <-- Pass run timestamp
            run_human_ts    # <-- Pass run timestamp
        )
        # --- END MODIFIED ---

        # TASK: `main`: Save results and handle failures
        if data:
            save_to_jsonl('results.jsonl', data)
            save_to_csv('results.csv', data)
            logging.info(f"Successfully saved data for {url}")
        else:
            logging.warning(f"No data returned for {url}. Skipping save.")

    # TASK: `main`: Add cleanup
    logging.info("Scan complete.")
    
    # --- FIX: browser.stop() is not async, so it should not be awaited ---
    browser.stop()

# TASK: Add script runner boilerplate
if __name__ == "__main__":
    
    # --- NEW: Parse Command-Line Arguments ---
    parser = argparse.ArgumentParser(
        description="Run WAVE accessibility scan on a list of URLs."
    )
    parser.add_argument(
        '--min-sleep',
        type=int,
        default=5,
        help="Minimum time (in seconds) to wait for page to settle. (Default: 5)"
    )
    parser.add_argument(
        '--max-sleep',
        type=int,
        default=35,
        help="Maximum time (in seconds) to wait for page to settle. (Default: 35)"
    )
    args = parser.parse_args()

    # Validate sleep times
    if args.min_sleep < 0 or args.max_sleep < 0:
        print("Error: Sleep times cannot be negative.")
        exit(1)
    if args.min_sleep > args.max_sleep:
        print("Error: --min-sleep cannot be greater than --max-sleep.")
        exit(1)
    # --- END NEW ---

    try:
        # Pass args to main
        uc.loop().run_until_complete(main(args.min_sleep, args.max_sleep))
    except KeyboardInterrupt:
        logging.info("Scan interrupted by user. Exiting.")