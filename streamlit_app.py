import streamlit as st
from streamlit_tags import st_tags_sidebar
import pandas as pd
import json
from datetime import datetime
from scraper import (
    fetch_html_api,
    save_raw_data,
    format_data,
    save_formatted_data,
    calculate_price,
    html_to_markdown_with_readability,
    create_dynamic_listing_model,
    create_listings_container_model,
    scrape_url,
    generate_unique_folder_name
)
from pagination_detector import detect_pagination_elements
import re
from urllib.parse import urlparse
from assets import PRICING
import os

# Initialize Streamlit app
st.set_page_config(page_title="Mawsool AI", page_icon="🦑", layout="wide")
st.title("Mawsool AI 🦑")

# Add the logo
st.markdown(
    """
    <style>
    .logo {
        width: 100px;
        height: auto;
    }
    </style>
    <img class="logo" src="https://github.com/adeyali1/testscr/blob/main/Mawsool%20Website%20Logo%20%20(2).png" alt="Mawsool AI Logo">
    """,
    unsafe_allow_html=True
)

# Initialize session state variables
if 'scraping_state' not in st.session_state:
    st.session_state['scraping_state'] = 'idle'  # Possible states: 'idle', 'waiting', 'scraping', 'completed'
if 'results' not in st.session_state:
    st.session_state['results'] = None
if 'driver' not in st.session_state:
    st.session_state['driver'] = None
if 'urls' not in st.session_state:
    st.session_state['urls'] = []
if 'processed_urls' not in st.session_state:
    st.session_state['processed_urls'] = 0
if 'real_time_results' not in st.session_state:
    st.session_state['real_time_results'] = []

# Sidebar components
st.sidebar.title("Web Scraper Settings")

# API Keys
with st.sidebar.expander("API Keys", expanded=False):
    st.session_state['openai_api_key'] = st.text_input("OpenAI API Key", type="password")
    st.session_state['gemini_api_key'] = st.text_input("Gemini API Key", type="password")
    st.session_state['groq_api_key'] = st.text_input("Groq API Key", type="password")

# Model selection
model_selection = st.sidebar.selectbox("Select Model", options=list(PRICING.keys()), index=0)

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

st.sidebar.markdown("---")

# Conditionally display Pagination and Attended Mode options
use_pagination = st.sidebar.toggle("Enable Pagination")
pagination_details = ""
if use_pagination:
    pagination_details = st.sidebar.text_input(
        "Enter Pagination Details (optional)",
        help="Describe how to navigate through pages (e.g., 'Next' button class, URL pattern)"
    )

st.sidebar.markdown("---")

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
        st.session_state['model_selection'] = model_selection
        st.session_state['use_pagination'] = use_pagination
        st.session_state['pagination_details'] = pagination_details
        st.session_state['scraping_state'] = 'scraping'
        st.session_state['processed_urls'] = 0
        st.session_state['real_time_results'] = []

# Scraping logic
if st.session_state['scraping_state'] == 'scraping':
    with st.spinner('Scraping in progress...'):
        # Perform scraping
        output_folder = os.path.join('output', generate_unique_folder_name(st.session_state['urls'][0]))
        os.makedirs(output_folder, exist_ok=True)

        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0
        all_data = []
        all_raw_data = []
        pagination_info = None

        for i, url in enumerate(st.session_state['urls'], start=1):
            st.write(f"Processing URL {i}: {url}")  # Debug statement
            try:
                # Fetch HTML
                raw_html = fetch_html_api(url)
                markdown = html_to_markdown_with_readability(raw_html)
                all_raw_data.append(markdown)

                # Detect pagination if enabled and only for the first URL
                if st.session_state['use_pagination'] and i == 1:
                    pagination_data, token_counts, pagination_price = detect_pagination_elements(
                        url, st.session_state['pagination_details'], st.session_state['model_selection'], markdown
                    )
                    # Check if pagination_data is a dict or a model with 'page_urls' attribute
                    if isinstance(pagination_data, dict):
                        page_urls = pagination_data.get("page_urls", [])
                    else:
                        page_urls = pagination_data.page_urls

                    pagination_info = {
                        "page_urls": page_urls,
                        "token_counts": token_counts,
                        "price": pagination_price
                    }
                # Scrape data if fields are specified
                if show_tags:
                    # Create dynamic models
                    DynamicListingModel = create_dynamic_listing_model(st.session_state['fields'])
                    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)
                    # Format data
                    formatted_data, token_counts = format_data(
                        markdown, DynamicListingsContainer, DynamicListingModel, st.session_state['model_selection']
                    )
                    input_tokens, output_tokens, cost = calculate_price(token_counts, st.session_state['model_selection'])
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                    total_cost += cost

                    # Add source URL to the results
                    for listing in formatted_data.listings:
                        listing_dict = listing.model_dump()  # Convert to dictionary
                        listing_dict['source'] = url  # Add source URL
                        updated_listing = DynamicListingModel(**listing_dict)  # Create updated listing
                        formatted_data.listings[formatted_data.listings.index(listing)] = updated_listing

                    all_data.append(formatted_data)

                    # Update real-time results
                    st.session_state['real_time_results'].extend([listing.model_dump() for listing in formatted_data.listings])
                    real_time_df = pd.DataFrame(st.session_state['real_time_results'])
                    st.dataframe(real_time_df, use_container_width=True)

                # Update processed URLs count
                st.session_state['processed_urls'] += 1

                # Display real-time results for every 25 websites
                if st.session_state['processed_urls'] % 25 == 0:
                    st.write(f"Processed {st.session_state['processed_urls']} websites.")
                    st.write(f"Current URL: {url}")
                    st.write(f"Current Markdown: {markdown}")
                    st.write(f"Current Formatted Data: {formatted_data}")

            except Exception as e:
                st.error(f"Error processing URL {i}: {e}")
                continue  # Continue processing the next URL

        # Save all raw data to a single file
        raw_data_path = os.path.join(output_folder, 'all_raw_data.md')
        with open(raw_data_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(all_raw_data))
        st.write(f"All raw data saved to {raw_data_path}")

        # Save all formatted data to a single file
        combined_df = pd.DataFrame([item.model_dump() for sublist in all_data for item in sublist.listings])
        formatted_data_path = os.path.join(output_folder, 'all_sorted_data.csv')
        combined_df.to_csv(formatted_data_path, index=False)
        st.write(f"All sorted data saved to {formatted_data_path}")

        # Save results
        st.session_state['results'] = {
            'data': all_data,
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'total_cost': total_cost,
            'output_folder': output_folder,
            'pagination_info': pagination_info
        }
        st.session_state['scraping_state'] = 'completed'

# Display results
if st.session_state['scraping_state'] == 'completed' and st.session_state['results']:
    results = st.session_state['results']
    all_data = results['data']
    total_input_tokens = results['input_tokens']
    total_output_tokens = results['output_tokens']
    total_cost = results['total_cost']
    output_folder = results['output_folder']
    pagination_info = results['pagination_info']

    # Display scraping details
    if show_tags:
        st.subheader("Scraping Results")
        combined_df = pd.DataFrame([item.model_dump() for sublist in all_data for item in sublist.listings])
        st.dataframe(combined_df, use_container_width=True)

        # Display token usage and cost
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Scraping Details")
        st.sidebar.markdown("#### Token Usage")
        st.sidebar.markdown(f"*Input Tokens:* {total_input_tokens}")
        st.sidebar.markdown(f"*Output Tokens:* {total_output_tokens}")
        st.sidebar.markdown(f"**Total Cost:** :green-background[**${total_cost:.4f}**]")

        # Download options
        st.subheader("Download Extracted Data")
        col1, col2 = st.columns(2)
        with col1:
            json_data = json.dumps(all_data, default=lambda o: [item.model_dump() for item in o.listings], indent=4)
            st.download_button(
                "Download JSON",
                data=json_data,
                file_name="scraped_data.json"
            )
        with col2:
            combined_df = pd.DataFrame([item.model_dump() for sublist in all_data for item in sublist.listings])
            st.download_button(
                "Download CSV",
                data=combined_df.to_csv(index=False),
                file_name="scraped_data.csv"
            )

        st.success(f"Scraping completed. Results saved in {output_folder}")

    # Display pagination info
    if pagination_info:
        st.markdown("---")
        st.subheader("Pagination Information")

        # Display token usage and cost using metrics
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Pagination Details")
        st.sidebar.markdown(f"**Number of Page URLs:** {len(pagination_info['page_urls'])}")
        st.sidebar.markdown("#### Pagination Token Usage")
        st.sidebar.markdown(f"*Input Tokens:* {pagination_info['token_counts']['input_tokens']}")
        st.sidebar.markdown(f"*Output Tokens:* {pagination_info['token_counts']['output_tokens']}")
        st.sidebar.markdown(f"**Pagination Cost:** :blue-background[**${pagination_info['price']:.4f}**]")

        # Display page URLs in a table
        st.write("**Page URLs:**")
        # Make URLs clickable
        pagination_df = pd.DataFrame(pagination_info["page_urls"], columns=["Page URLs"])

        st.dataframe(
            pagination_df,
            column_config={
                "Page URLs": st.column_config.LinkColumn("Page URLs")
            },use_container_width=True
        )

        # Download pagination URLs
        st.subheader("Download Pagination URLs")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("Download Pagination CSV",data=pagination_df.to_csv(index=False),file_name="pagination_urls.csv")
        with col2:
            st.download_button("Download Pagination JSON",data=json.dumps(pagination_info['page_urls'], indent=4),file_name="pagination_urls.json")
    # Reset scraping state
    if st.sidebar.button("Clear Results"):
        st.session_state['scraping_state'] = 'idle'
        st.session_state['results'] = None

   # If both scraping and pagination were performed, show totals under the pagination table
    if show_tags and pagination_info:
        st.markdown("---")
        total_input_tokens_combined = total_input_tokens + pagination_info['token_counts']['input_tokens']
        total_output_tokens_combined = total_output_tokens + pagination_info['token_counts']['output_tokens']
        total_combined_cost = total_cost + pagination_info['price']
        st.markdown("### Total Counts and Cost (Including Pagination)")
        st.markdown(f"**Total Input Tokens:** {total_input_tokens_combined}")
        st.markdown(f"**Total Output Tokens:** {total_output_tokens_combined}")
        st.markdown(f"**Total Combined Cost:** :rainbow-background[**${total_combined_cost:.4f}**]")
# Helper function to generate unique folder names
def generate_unique_folder_name(url):
    timestamp = datetime.now().strftime('%Y_%m_%d__%H_%M_%S')

    # Parse the URL
    parsed_url = urlparse(url)

    # Extract the domain name
    domain = parsed_url.netloc or parsed_url.path.split('/')[0]

    # Remove 'www.' if present
    domain = re.sub(r'^www\.', '', domain)

    # Remove any non-alphanumeric characters and replace with underscores
    clean_domain = re.sub(r'\W+', '_', domain)

    return f"{clean_domain}_{timestamp}"
