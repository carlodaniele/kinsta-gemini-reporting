import requests
import os

# API Configuration from environment variables
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
BASE_URL = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics"

def get_headers():
    """Returns standard authorization headers for Kinsta API."""
    return {"Authorization": f"Bearer {KINSTA_API_KEY}"}

def format_bytes_to_mb(bytes_value):
    """Converts raw bytes from API to human-readable Megabytes."""

    try:
        # Standard conversion to MB
        # return round(int(bytes_value) / (1024 * 1024), 2)

        # Decimal standard (used in MyKinsta dashboard) 
        return round(int(bytes_value) / 1_000_000, 2)

    except (ValueError, TypeError):
        return 0

def fetch_kinsta_metric(endpoint, start_date, end_date):
    """
    Generic helper to fetch any metric from Kinsta for a specific 7-day range.
    Supported endpoints: visits, bandwidth, disk-space.
    """

    url = f"{BASE_URL}/{endpoint}"

    params = {
        "company_id": KINSTA_COMPANY_ID,
        "from": f"{start_date}T00:00:00.000Z",
        "to": f"{end_date}T23:59:59.000Z",
        "time_span": "30_days"
    }

    try:
        response = requests.get(url, headers=get_headers(), params=params)
        if response.status_code == 200:
            # Target the specific JSON structure: analytics -> analytics_response -> data
            data_node = response.json()['analytics']['analytics_response']['data'][0]
            total = data_node.get('total', 0)
            dataset = data_node.get('dataset', [])[:7]
            return total, dataset

    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")

    return 0, []

def fetch_site_name():
    """Fetches the site name from Kinsta API using the Environment ID."""
    url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            # L'API restituisce il nome del sito e dell'ambiente
            data = response.json()
            site_label = data['site']['display_name']
            env_label = data['display_name']
            return f"{site_label} ({env_label})"
    except Exception as e:
        print(f"Error fetching site name: {e}")
    return "Unknown Site"
    
