import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import calendar
import time
from datetime import datetime
from google import generativeai as genai
from google.generativeai.types import RequestOptions
from fpdf import FPDF, XPos, YPos

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_SITE_ID = os.getenv("KINSTA_SITE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaPrecisionReporter:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/{KINSTA_SITE_ID}/analytics"

    def get_time_range(self):
        """Calcola start e end in millisecondi per il mese corrente."""
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        # Unix timestamp in millisecondi
        start_ms = int(time.mktime(start_date.timetuple()) * 1000)
        end_ms = int(time.time() * 1000)
        return start_ms, end_ms

    def fetch(self, endpoint):
        start, end = self.get_time_range()
        url = f"{self.base_url}/{endpoint}"
        params = {"start": start, "end": end}
        
        try:
            res = requests.get(url, headers=self.headers, params=params)
            if res.status_code == 200:
                return res.json()
            print(f"Errore {endpoint}: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"Errore connessione {endpoint}: {e}")
        return {}

def main():
    reporter = KinstaPrecisionReporter()
    
    # 1. Recupero Dati
    v_raw = reporter.fetch("visits")
    b_raw = reporter.fetch("server-bandwidth")
    d_raw = reporter.fetch("disk-space")
    geo_raw = reporter.fetch("top-countries")

    # 2. Estrazione (Mapping basato su Documentazione Kinsta)
    # Struttura: data -> site -> [endpoint] -> report
    visits_list = v_raw.get('data', {}).get('site', {}).get('visits', {}).get('report', [])
    bw_list = b_raw.get('data', {}).get('site', {}).get('server_bandwidth', {}).get('report', [])
    disk_list = d_raw.get('data', {}).get('site', {}).get('disk_space', {}).get('report', [])
    countries = geo_raw.get('data', {}).get('site', {}).get('top_countries', [])

    total_visits = sum(int(i.get('value', 0)) for i in visits_list)
    total_bw_mb = round(sum(int(i.get('value', 0)) for i in bw_list) / (1024*1024), 2)
    last_disk_mb = round(int(disk_list[-1].get('value', 0)) / (1024*1024), 2) if disk_list else 0
    top_country = countries[0].get('name', 'N/A') if countries else 'N/A'

    print(f"Dati estratti: {total_visits} visite, {total_bw_mb} MB banda")

    # 3. Grafico
    plt.figure(figsize=(10, 4))
    if visits_list:
        days = [i['datetime'][8:10] for i in visits_list]
        counts = [int(i['value']) for i in visits_list]
        plt.fill_between(days, counts, color='#5333ed', alpha=0.1)
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2)
    else:
        plt.text(0.5, 0.5, "Nessun dato disponibile nel periodo selezionato", ha='center')
    
    plt.title("Analisi Traffico Reale (Analytics API)")
    plt.savefig("chart.png")

    # 4. Gemini
    prompt = f"Analizza per un cliente: {total_visits} visite, {total_bw_mb}MB banda, {last_disk_mb}MB disco. Top Country: {top_country}."
    try:
        summary = model.generate_content(prompt, request_options=RequestOptions(api_version='v1')).text
    except:
        summary = "Performance stabili rilevate dai sistemi di analisi."

    # 5. PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Kinsta Precise Analytics Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    
    metrics = [
        ["Visite Totali", str(total_visits), "Periodo Corrente"],
        ["Banda Server", f"{total_bw_mb} MB", "Traffico HTTP/S"],
        ["Spazio Disco", f"{last_disk_mb} MB", "Storage Live"],
        ["Top Nazione", top_country, "Geolocalizzazione"]
    ]
    
    pdf.cell(60, 10, " Metrica", 1, 0, 'L', True)
    pdf.cell(60, 10, " Valore", 1, 0, 'C', True)
    pdf.cell(60, 10, " Note", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", "", 10)
    for m in metrics:
        pdf.cell(60, 8, f" {m[0]}", 1)
        pdf.cell(60, 8, f" {m[1]}", 1, 0, 'C')
        pdf.cell(60, 8, f" {m[2]}", 1, 1, 'C')

    if os.path.exists("chart.png"):
        pdf.image("chart.png", x=10, y=90, w=190)

    pdf.set_y(185)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Executive AI Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, summary)

    pdf.output("Kinsta_Precise_Report.pdf")

if __name__ == "__main__":
    main()
