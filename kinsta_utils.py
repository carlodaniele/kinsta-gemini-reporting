import requests
import os

BASE_URL = "https://api.kinsta.com/v2/sites"
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")

def get_headers():
    return {
        "Authorization": f"Bearer {KINSTA_API_KEY}",
        "Content-Type": "application/json"
    }

def format_bytes_to_mb(bytes_val):
    """Converte i byte in Megabyte (MiB) con precisione a 2 decimali."""
    try:
        # Usiamo 1024*1024 per coerenza con il pannello MyKinsta
        return round(float(bytes_val) / (1024 * 1024), 2)
    except:
        return 0

def fetch_kinsta_metrics_combined(endpoints, start_date, end_date):
    """
    Recupera i dati da più endpoint e li somma giorno per giorno.
    Risolve il problema della banda parziale e dello sfasamento temporale.
    """
    combined_data = {}
    
    for endpoint in endpoints:
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
                analytics_data = response.json().get('analytics', {}).get('analytics_response', {}).get('data', [])
                if not analytics_data:
                    continue
                
                dataset = analytics_data[0].get('dataset', [])
                for item in dataset:
                    # Estraiamo solo la data (YYYY-MM-DD) per mappare correttamente i valori
                    day = item['datetime'].split('T')[0]
                    val = float(item.get('value', 0))
                    combined_data[day] = combined_data.get(day, 0) + val
        except Exception as e:
            print(f"Errore durante il fetch di {endpoint}: {e}")
            
    return combined_data
