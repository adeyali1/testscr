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

from dotenv import load_dotenv
import http.client

from openai import OpenAI
import google.generativeai as genai
from groq import Groq

from api_management import get_api_key
from assets import USER_AGENTS, PRICING, HEADLESS_OPTIONS, SYSTEM_MESSAGE, USER_MESSAGE, LLAMA_MODEL_FULLNAME, GROQ_LLAMA_MODEL_FULLNAME, HEADLESS_OPTIONS_DOCKER

# Load environment variables
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

def create_dynamic_listing_model(field_names: List[str]) -> Type[BaseModel]:
    field_definitions = {field: (str, ...) for field in field_names}
    field_definitions['source'] = (str, ...)
    return create_model('DynamicListingModel', **field_definitions)

def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    return create_model('DynamicListingsContainer', listings=(List[listing_model], ...))

def format_data(data, DynamicListingsContainer, DynamicListingModel, selected_model):
    # Dummy implementation for format_data, replace it with the actual formatting
    return DynamicListingsContainer(listings=[]), {}

def calculate_price(token_counts, model):
    input_token_count = token_counts.get("input_tokens", 0)
    output_token_count = token_counts.get("output_tokens", 0)
    input_cost = input_token_count * PRICING[model]["input"]
    output_cost = output_token_count * PRICING[model]["output"]
    total_cost = input_cost + output_cost
    return input_token_count, output_token_count, total_cost

def scrape_url(url: str, fields: List[str], selected_model: str, output_folder: str, file_number: int, markdown: str, csv_file):
    """Scrape a single URL and save the results incrementally to a CSV file."""
    try:
        # Save raw data
        save_raw_data(markdown, output_folder, f'rawData_{file_number}.md')

        # Create the dynamic listing model
        DynamicListingModel = create_dynamic_listing_model(fields)

        # Create the container model that holds a list of the dynamic listing models
        DynamicListingsContainer = create_listings_container_model(DynamicListingModel)

        # Format data
        formatted_data, token_counts = format_data(markdown, DynamicListingsContainer, DynamicListingModel, selected_model)

        # Add source URL to the results
        for listing in formatted_data.listings:
            listing.source = url

        # Prepare data for saving to CSV
        formatted_data_dict = formatted_data.dict() if hasattr(formatted_data, 'dict') else formatted_data
        data_list = [[url] + [listing.get(field, "") for field in fields] for listing in formatted_data_dict.get("listings", [])]

        # Append data to CSV file
        df = pd.DataFrame(data_list, columns=["URL"] + fields)
        if not os.path.exists(csv_file):
            df.to_csv(csv_file, index=False)
        else:
            df.to_csv(csv_file, mode='a', header=False, index=False)

        # Calculate and return token usage and cost
        input_tokens, output_tokens, total_cost = calculate_price(token_counts, selected_model)
        return input_tokens, output_tokens, total_cost, formatted_data

    except Exception as e:
        print(f"An error occurred while processing {url}: {e}")
        return 0, 0, 0, None
