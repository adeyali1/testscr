import http.client
import json

class NewAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "cheap-web-scarping-api.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.base_url,
            'Content-Type': "application/json"
        }

    def scrape(self, url: str, wait_until: str = "domcontentloaded"):
        """
        Send a request to the scraping API to scrape the data from the given URL.

        :param url: The URL to scrape.
        :param wait_until: The condition to wait for (e.g., "domcontentloaded").
        :return: The scraped data from the API.
        """
        conn = http.client.HTTPSConnection(self.base_url)
        payload = json.dumps({"url": url, "waitUntil": wait_until})

        try:
            conn.request("POST", "/api/scrape", payload, self.headers)
            res = conn.getresponse()
            data = res.read()
            if res.status == 200:
                return json.loads(data.decode("utf-8"))
            else:
                raise ValueError(f"API request failed with status code {res.status}: {data.decode('utf-8')}")
        finally:
            conn.close()

# Example usage
if __name__ == "__main__":
    api_key = "779950d602mshdb324e7fb7fc384p10ad06jsnc96469ca8d95"
    new_api = NewAPI(api_key)
    result = new_api.scrape("https://mawsool.tech")
    print(json.dumps(result, indent=4))
