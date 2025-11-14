# WAVE Accessibility Scanner & Reporter

This project automates accessibility testing for websites. It uses the **WAVE WebAIM tool** to scan a list of URLs, saves the results (including screenshots), and generates an interactive HTML report to visualize the data and track changes over time.

## Features

  * **Automated Scanning:** Runs WAVE on as many URLs as you want from a simple text file.
  * **Data Logging:** Saves all results to `results.csv` and `results.jsonl` for your records.
  * **Visual Proof:** Takes a WebP screenshot of the full WAVE report page for each scan (automatically compressed from PNG).
  * **Progress Bars:** Shows real-time progress during scans (or detailed logging with `--verbose` flag).
  * **Interactive Report:** Builds a single, self-contained `report.html` file with charts and sortable tables.
  * **Trend Tracking:** See how accessibility scores (like the AIM Score) and error counts change over time for each site.
  * **Run Comparison:** The report lets you easily switch between different scan runs to compare results.

-----

## Compatibility

This tool has been tested and confirmed to work in the following environments:

  * Windows (using **PowerShell**)
  * Linux (specifically via **WSL** - Windows Subsystem for Linux)

It should work on any system that can run Python 3, Google Chrome, and the required libraries.

-----

## How to Use

Follow these steps to run your first scan and generate a report.

### Step 1: Setup

1.  **Check Prerequisites:** You must have **Python 3** and **Google Chrome** (or Chromium) installed on your computer.

2.  **Install Libraries:** Open your terminal and install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

    Or install individually:

    ```bash
    pip install nodriver pandas jinja2 tqdm Pillow
    ```

### Step 2: Add Your URLs

1.  Create a new file named `urls.txt` in the same folder as the scripts.

2.  Add the websites you want to scan. Put **one URL on each line**.

    **Example `urls.txt`:**

    ```
    https://www.google.com
    https://www.github.com
    https://www.example.com/
    https://www.example.com/about-us
    ```

### Step 3: Run the Scan

1.  In your terminal, run the `run.py` script:

    ```bash
    python run.py
    ```

2.  The script will:

      * Open Google Chrome.
      * Visit the WAVE report page for each URL in `urls.txt`.
      * Wait for the report to finish.
      * Take a screenshot and convert it to WebP format.
      * Save all the data.

    By default, you'll see two progress bars:
      * **Overall Progress:** Shows how many pages have been scanned.
      * **Current Page:** Shows the 6 steps for the page being scanned.

3.  **Outputs:** This step creates and adds to the following:

      * `results.csv`: The main data file for all your scans.
      * `results.jsonl`: A JSON-line version of the data.
      * `screenshots/`: A new folder containing all the screenshots (in WebP format).

#### Command-Line Options

**Custom Input File:**
```bash
# Use a different file instead of urls.txt
python run.py --input myurls.txt
# or use short form
python run.py -i myurls.txt
```

**Verbose Mode:**
```bash
# Show detailed logging instead of progress bars
python run.py --verbose
```

**Adjust Wait Times:**
The script waits a random time (between 5 and 35 seconds by default) on each page to allow it to fully load. You can change this:

```bash
# Wait between 10 and 40 seconds instead
python run.py --min-sleep 10 --max-sleep 40
```

**Combine Options:**
```bash
# Use custom input file with verbose logging and custom wait times
python run.py -i myurls.txt --verbose --min-sleep 10 --max-sleep 40
```

### Step 4: Generate the Report

1.  Once the scan is done, run the `report.py` script:

    ```bash
    python report.py
    ```

2.  This script reads your `results.csv` file, processes all the data, and builds the final HTML report.

3.  **Output:** This creates `report.html`.

### Step 5: View Your Report

Open the `report.html` file in your web browser to view the results.

You can re-run Step 3 and Step 4 as many times as you like. Each time you run the scan, new data will be added, and the report will update to show trends over time.

-----

## File Descriptions

  * `run.py`
    The main scanner. This script uses `nodriver` to control Chrome, runs the scans, and saves the data and screenshots.

  * `report.py`
    The report builder. This script uses `pandas` to read `results.csv` and `jinja2` to put all the data into the HTML template.

  * `report.html.j2`
    The Jinja2 (HTML) template for the final report. This is the "mold" that `report.py` fills with your data.

-----

## Troubleshooting

  * **"Google Chrome Not Found" Error:**
    The `run.py` script needs Google Chrome to be installed in its default location. If you see this error, it means the script can't find it. The error message will give you instructions on how to edit `run.py` to point to your exact Chrome location.
