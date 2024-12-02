import os
import random
import time
import re
import json
from datetime import datetime
from typing import List, Dict, Type

import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, create_model
import html2text

from dotenv import load_dotenv
import http.client

# Load environment variables
load_dotenv()

def fetch_html_api(url):
    conn = http.client.HTTPSConnection("fast-ninja-scraper.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': "YOUR_RAPIDAPI_KEY_HERE",  # Replace with your valid key
        'x-rapidapi-host': "fast-ninja-scraper.p.rapidapi.com"
    }
    conn.request("GET", f"/scrape?url={url}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    
    # Load JSON response
    response = json.loads(data.decode("utf-8"))
    if response.get("status") == "success":
        return response["content"]  # Return the HTML content
    else:
        raise ValueError(f"Failed to fetch HTML for {url}: {response.get('message', 'Unknown error')}")

def html_to_markdown_with_readability(html_content):
    cleaned_html = clean_html(html_content)
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    markdown_content = markdown_converter.handle(cleaned_html)
    return markdown_content

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for element in soup.find_all(['header', 'footer']):
        element.decompose()
    return str(soup)

def save_raw_data(raw_data: str, output_folder: str, file_name: str):
    os.makedirs(output_folder, exist_ok=True)
    raw_output_path = os.path.join(output_folder, file_name)
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    return raw_output_path

def scrape_url(url: str, fields: List[str], output_folder: str, file_number: int, csv_file):
    """Scrape a single URL and save the results incrementally to a CSV file."""
    try:
        # Fetch HTML content using API
        raw_html = fetch_html_api(url)
        markdown = html_to_markdown_with_readability(raw_html)

        # Save raw data
        save_raw_data(markdown, output_folder, f'rawData_{file_number}.md')

        # Add the scraped data to CSV
        data_dict = {
            "URL": url,
            "Scraped_Content": markdown  # Adding the entire markdown content
        }

        df = pd.DataFrame([data_dict])

        # Append data to CSV file
        if not os.path.exists(csv_file):
            df.to_csv(csv_file, index=False)
        else:
            df.to_csv(csv_file, mode='a', header=False, index=False)

        return True  # Indicating successful processing

    except Exception as e:
        print(f"An error occurred while processing {url}: {e}")
        return False
