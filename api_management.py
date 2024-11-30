import streamlit as st
import os
import http.client
import json

def get_api_key(api_key_name):
    # Check if the API key from the sidebar is present, else fallback to the .env file
    if api_key_name == 'OPENAI_API_KEY':
        return st.session_state['openai_api_key'] or os.getenv(api_key_name)
    elif api_key_name == 'GOOGLE_API_KEY':
        return st.session_state['gemini_api_key'] or os.getenv(api_key_name)
    elif api_key_name == 'GROQ_API_KEY':
        return st.session_state['groq_api_key'] or os.getenv(api_key_name)
    elif api_key_name == 'NEW_API_KEY':
        return st.session_state['new_api_key'] or os.getenv(api_key_name)
    else:
        return os.getenv(api_key_name)

def make_api_request(url):
    conn = http.client.HTTPSConnection("cheap-web-scarping-api.p.rapidapi.com")

    # Prepare the payload with the provided URL
    payload = json.dumps({"url": url, "waitUntil": "domcontentloaded"})

    headers = {
        'x-rapidapi-key': "779950d602mshdb324e7fb7fc384p10ad06jsnc96469ca8d95",
        'x-rapidapi-host': "cheap-web-scarping-api.p.rapidapi.com",
        'Content-Type': "application/json"
    }

    try:
        # Make the API request
        conn.request("POST", "/api/scrape", payload, headers)
        res = conn.getresponse()
        data = res.read()

        # Parse the response
        response_data = data.decode("utf-8")
        return json.loads(response_data)
    except Exception as e:
        # Handle exceptions and return error message
        return {"error": str(e)}
    finally:
        conn.close()
