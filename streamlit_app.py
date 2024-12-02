import streamlit as st
from streamlit_tags import st_tags_sidebar
import pandas as pd
import json
import os
from scraper import (
    fetch_html_api,
    save_raw_data,
    format_data,
    create_dynamic_listing_model,
    create_listings_container_model,
    scrape_url
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from urllib.parse import urlparse
import re

# Set up Google Sheets Integration
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("client_secret_1016778401112-1q5tdlkuvcl0rkbbjmptbirmk0vn8drv.apps.googleusercontent.com.json", scope)
client = gspread.authorize(creds)
sheet = client.open("ScrapedData").sheet1

# Initialize Streamlit app
st.set_page_config(page_title="Mawsool AI", page_icon="🦑", layout="wide")
st.title("Mawsool AI 🦑")

# Sidebar components
st.sidebar.title("Web Scraper Settings")

# File uploader for bulk URLs
uploaded_file = st.sidebar.file_uploader("Upload CSV or TXT file with URLs", type=["csv", "txt"])

# Fields to extract
show_tags = st.sidebar.toggle("Enable Scraping")
fields = []
if show_tags:
    fields = st_tags_sidebar(
        label='Enter Fields to Extract:',
        text='Press enter to add a field',
        value=[],
        suggestions=[],
        maxtags=-1,
        key='fields_input'
    )

# Main action button
if st.sidebar.button("LAUNCH SCRAPER", type="primary"):
    if uploaded_file is None:
        st.error("Please upload a file containing URLs.")
    elif show_tags and len(fields) == 0:
        st.error("Please enter at least one field to extract.")
    else:
        # Read URLs from the uploaded file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
            st.session_state['urls'] = df.iloc[:, 0].tolist()
        elif uploaded_file.name.endswith('.txt'):
            st.session_state['urls'] = uploaded_file.getvalue().decode("utf-8").splitlines()

        # Set up scraping parameters in session state
        st.session_state['fields'] = fields
        st.session_state['scraping_state'] = 'scraping'
        st.session_state['processed_urls'] = 0

# Scraping logic
if st.session_state.get('scraping_state') == 'scraping':
    with st.spinner('Scraping in progress...'):
        output_folder = 'output'
        os.makedirs(output_folder, exist_ok=True)

        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0
        all_data = []

        for i, url in enumerate(st.session_state['urls'], start=1):
            st.write(f"Processing URL {i}: {url}")
            try:
                # Fetch HTML and convert to markdown
                raw_html = fetch_html_api(url)
                markdown = html_to_markdown_with_readability(raw_html)

                # Scrape data if fields are specified
                if show_tags:
                    input_tokens, output_tokens, cost, formatted_data = scrape_url(
                        url, st.session_state['fields'], st.session_state['model_selection'], output_folder, i, markdown, sheet
                    )
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                    total_cost += cost

                    # Update processed URLs count
                    st.session_state['processed_urls'] += 1

                if st.session_state['processed_urls'] % 25 == 0:
                    st.write(f"Processed {st.session_state['processed_urls']} websites.")

            except Exception as e:
                st.error(f"Error processing URL {i}: {e}")
                continue

        st.success(f"Scraping completed. Results saved in Google Sheets.")
        st.session_state['scraping_state'] = 'completed'
