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
    """Converte i byte grezzi in Megabyte con gestione errori migliorata."""
    try:
        if bytes_value is None: return 0
        # Kinsta API restituisce spesso i dati come stringhe o float
        val = float(bytes_value)
        # Conversione: Byte -> KB -> MB
        return round(val / (1024 * 1024), 2)
    except (ValueError, TypeError):
        return 0

def fetch_kinsta_metric(endpoint, start_date, end_date):
    url = f"{BASE_URL}/{endpoint}"
    params = {
        "company_id": KINSTA_COMPANY_ID,
        "from": f"{start_date}T00:00:00.000Z",
        "to": f"{end_date}T23:59:59.000Z",
        "time_span": "12_hours" 
    }
    try:
        response = requests.get(url, headers=get_headers(), params=params)
        if response.status_code == 200:
            data_node = response.json()['analytics']['analytics_response']['data'][0]
            dataset = data_node.get('dataset', [])
            
            value_map = {}
            for item in dataset:
                # Pulizia: prendiamo solo la data (YYYY-MM-DD) ignorando l'ora
                day_key = item['datetime'].split('T')[0]
                val = float(item.get('value', 0))
                
                # Sommiamo se ci sono più voci per lo stesso giorno
                value_map[day_key] = value_map.get(day_key, 0) + val
                
            return value_map
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
    return {}
