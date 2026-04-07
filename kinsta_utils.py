import requests

BASE_URL = "https://api.kinsta.com/v2/sites"
# Assicurati che queste variabili siano popolate correttamente nel tuo ambiente
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")

def get_headers():
    return {
        "Authorization": f"Bearer {KINSTA_API_KEY}",
        "Content-Type": "application/json"
    }

def format_bytes_to_mb(bytes_val):
    """Converte i byte in Megabyte (MiB) con arrotondamento a 2 decimali."""
    try:
        return round(float(bytes_val) / (1024 * 1024), 2)
    except:
        return 0

def fetch_kinsta_metrics_combined(endpoints, start_date, end_date):
    """
    Interroga più endpoint e somma i valori per ogni singola data.
    Restituisce un dizionario { "YYYY-MM-DD": ValoreTotale }
    """
    combined_data = {}
    
    for endpoint in endpoints:
        url = f"{BASE_URL}/{endpoint}"
        params = {
            "company_id": KINSTA_COMPANY_ID,
            "from": f"{start_date}T00:00:00.000Z",
            "to": f"{end_date}T23:59:59.000Z",
            "time_span": "12_hours" # Granularità per coprire bene la giornata
        }
        
        try:
            response = requests.get(url, headers=get_headers(), params=params)
            if response.status_code == 200:
                # Navighiamo nel JSON di Kinsta
                data_list = response.json().get('analytics', {}).get('analytics_response', {}).get('data', [])
                if not data_list: continue
                
                dataset = data_list[0].get('dataset', [])
                for item in dataset:
                    # Puliamo la data dal timestamp UTC (es: 2026-03-31T12:00:00Z -> 2026-03-31)
                    day = item['datetime'].split('T')[0]
                    val = float(item.get('value', 0))
                    # Sommiamo (Server + CDN + Edge)
                    combined_data[day] = combined_data.get(day, 0) + val
        except Exception as e:
            print(f"Errore durante il fetch di {endpoint}: {e}")
            
    return combined_data
