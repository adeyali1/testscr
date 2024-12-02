import streamlit as st
from streamlit_tags import st_tags_sidebar
import pandas as pd
import os
from scraper import (
    fetch_html_api,
    save_raw_data,
    scrape_url,
    html_to_markdown_with_readability,
    generate_unique_folder_name
)
from datetime import datetime
from urllib.parse import urlparse
import re

# Initialize Streamlit app
st.set_page_config(page_title="Mawsool AI", page_icon="🦑", layout="wide")
st.title("Mawsool AI 🦑")

# Sidebar components
st.sidebar.title("Web Scraper Settings")

# API Keys Section - Add OpenAI API Key
with st.sidebar.expander("API Keys", expanded=True):
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    st.session_state['openai_api_key'] = openai_api_key

# File uploader for bulk URLs
uploaded_file = st.sidebar.file_uploader("Upload CSV or TXT file with URLs", type=["csv", "txt"])

# Fields to extract
show_tags = st.sidebar.checkbox("Enable Scraping")
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
    elif 'openai_api_key' not in st.session_state or not st.session_state['openai_api_key']:
        st.error("Please provide your OpenAI API Key.")
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
        csv_file_path = os.path.join(output_folder, 'scraped_data.csv')

        for i, url in enumerate(st.session_state['urls'], start=1):
            st.write(f"Processing URL {i}: {url}")
            try:
                # Scrape data and save it to CSV
                success = scrape_url(url, st.session_state['fields'], "", output_folder, i, csv_file_path)

                if success:
                    st.session_state['processed_urls'] += 1

                if st.session_state['processed_urls'] % 25 == 0:
                    st.write(f"Processed {st.session_state['processed_urls']} websites.")

                # Periodically update to avoid overwhelming system memory for large datasets
                if i % 100 == 0:
                    st.experimental_rerun()

            except Exception as e:
                st.error(f"Error processing URL {i}: {e}")
                continue

        st.success(f"Scraping completed. Data saved to CSV at {csv_file_path}.")
        st.session_state['scraping_state'] = 'completed'
