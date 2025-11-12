#!/usr/bin/env python3

"""
report.py

Generates a self-contained HTML accessibility report from a results.csv file.
The report includes an overall summary and a sortable table, as well as a
detailed view to track a single URL's accessibility metrics over time.
"""

import pandas as pd
import json
import argparse
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def create_report(csv_file: Path, html_file: Path, template_dir: Path):
    """
    Reads the CSV file, processes data, and injects it into the HTML template.
    """
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"Error: Input file not found at {csv_file}")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print(f"Error: Input file {csv_file} is empty. No report generated.")
        return

    if df.empty:
        print(f"Warning: {csv_file} is empty. Report will be blank.")
        
    # --- CHANGE 1: Normalize URLs ---
    # Remove trailing slashes to treat 'example.com/' and 'example.com' as the same.
    df['url'] = df['url'].str.rstrip('/')
        
    # Convert timestamp (seconds) to a UTC-aware datetime object.
    # We explicitly set utc=True here to ensure consistency across environments.
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
    
    # --- CHANGE 2: De-duplicate within the same run ---
    # If a run had both 'page/' and 'page', they are now identical.
    # Keep only the first one we find for that 'datetime' and 'url' pair.
    df = df.drop_duplicates(subset=['datetime', 'url'], keep='first')
    
    # 1. Get data for the "latest run" (latest timestamp for each unique URL)
    latest_run_df = df.sort_values('datetime', ascending=False).drop_duplicates('url')
    
    # 2. Get all unique URLs for the dropdown
    all_urls = sorted(df['url'].unique().tolist())
    
    # 3. Get overall trend data (group by run, get averages)
    agg_df = df.groupby('datetime').agg({
        'AIM Score': 'mean',
        'Errors': 'mean',
        'Contrast Errors': 'mean',
        'Alerts': 'mean'
    }).reset_index().sort_values('datetime')

    # 4. Get all unique runs for the new dropdown (sorted newest first)
    all_runs = []
    if not df.empty:
        unique_datetimes = sorted(df['datetime'].unique(), reverse=True)
        for dt in unique_datetimes:
            # dt is a pandas Timestamp and supports tz_convert()
            
            # CRITICAL FIX: Use the raw Unix timestamp (seconds) as the value for filtering
            unix_timestamp = int(dt.timestamp()) 
            
            # The label should still be local-time formatted for display
            # FIX: Call tz_convert() directly on the pandas Timestamp object 'dt'
            local_time_dt = dt.tz_convert('America/New_York') 
            
            all_runs.append({
                'unix_s': unix_timestamp,
                # Use the timezone-converted Timestamp for strftime()
                'label': local_time_dt.strftime('%Y-%m-%d %I:%M %p') 
            })

    # 5. Convert dataframes to JSON strings
    # We use 'records' orient to get a list of [{{col: val, ...}}]
    full_data_json = df.to_json(orient='records')
    latest_run_data_json = latest_run_df.to_json(orient='records')
    all_urls_json = json.dumps(all_urls)
    overall_trend_data_json = agg_df.to_json(orient='records')
    all_runs_json = json.dumps(all_runs) # Pass new data to template
    
    # 6. Set up Jinja2 environment and load template
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('report.html.j2')
    
    # 7. Create the context and render the template
    context = {
        'full_data_json': full_data_json,
        'latest_run_data_json': latest_run_data_json,
        'all_urls_json': all_urls_json,
        'overall_trend_data_json': overall_trend_data_json,
        'all_runs_json': all_runs_json  # Pass new data to template
    }
    html_content = template.render(context)
    
    # 8. Write the final HTML to the output file
    try:
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Report successfully generated: {html_file.resolve()}")
    except IOError as e:
        print(f"Error writing to output file {html_file}: {e}")
        sys.exit(1)

def main():
    """
    Main function to parse command-line arguments and run the report generator.
    """
    parser = argparse.ArgumentParser(
        description="Generate an HTML accessibility report from wave_scanner.py results."
    )
    parser.add_argument(
        '-i', '--input',
        type=Path,
        default=Path('results.csv'),
        help="Input CSV file (default: results.csv)"
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('report.html'),
        help="Output HTML file (default: report.html)"
    )
    args = parser.parse_args()
    
    # Define the template directory as the same directory as this script
    template_dir = Path(__file__).parent.resolve()
    
    create_report(args.input, args.output, template_dir)

if __name__ == "__main__":
    main()