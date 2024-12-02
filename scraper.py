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
import tiktoken
import streamlit as st

from dotenv import load_dotenv
import http.client

from openai import OpenAI
import google.generativeai as genai
from groq import Groq

from api_management import get_api_key
from assets import USER_AGENTS, PRICING, HEADLESS_OPTIONS, SYSTEM_MESSAGE, USER_MESSAGE, LLAMA_MODEL_FULLNAME, GROQ_LLAMA_MODEL_FULLNAME, HEADLESS_OPTIONS_DOCKER
load_dotenv()

def fetch_html_api(url):
    conn = http.client.HTTPSConnection("fast-ninja-scraper.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': "779950d602mshdb324e7fb7fc384p10ad06jsnc96469ca8d95",
        'x-rapidapi-host': "fast-ninja-scraper.p.rapidapi.com"
    }
    conn.request("GET", f"/scrape?url={url}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove headers and footers based on common HTML tags or classes
    for element in soup.find_all(['header', 'footer']):
        element.decompose()  # Remove these tags and their content

    return str(soup)

def html_to_markdown_with_readability(html_content):
    cleaned_html = clean_html(html_content)

    # Convert to markdown
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    markdown_content = markdown_converter.handle(cleaned_html)

    return markdown_content

def save_raw_data(raw_data: str, output_folder: str, file_name: str):
    """Save raw markdown data to the specified output folder."""
    os.makedirs(output_folder, exist_ok=True)
    raw_output_path = os.path.join(output_folder, file_name)
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    print(f"Raw data saved to {raw_output_path}")
    return raw_output_path

def save_incremental_data_to_csv(data_dict, csv_file_path):
    """
    Saves the data incrementally to a CSV file.
    """
    df = pd.DataFrame([data_dict])
    
    # Save or append to CSV
    if not os.path.exists(csv_file_path):
        df.to_csv(csv_file_path, index=False)
    else:
        df.to_csv(csv_file_path, mode='a', header=False, index=False)

def scrape_url(url: str, fields: List[str], selected_model: str, output_folder: str, file_number: int, csv_file_path: str):
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

        # Save the scraped data in real-time to CSV
        save_incremental_data_to_csv(data_dict, csv_file_path)

        return True  # Indicating successful processing

    except Exception as e:
        print(f"An error occurred while processing {url}: {e}")
        return False
