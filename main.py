import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time
from datetime import datetime
from google import generativeai as genai
from google.generativeai.types import RequestOptions
from fpdf import FPDF, XPos, YPos

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_SITE_ID = os.getenv("KINSTA_SITE_ID")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID") 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaPrecisionReporter:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        # PATH CORRETTO: /sites/{site_id}/environments/{env_id}/analytics/
        self.base_url = f"https://api.kinsta.com/v2/sites/{KINSTA_SITE_ID}/environments/{KINSTA_ENV_ID}/analytics"

    def fetch(self, endpoint):
        now = datetime.now()
        # Calcolo millisecondi (Start: inizio mese, End: ora)
        start_ms = int(time.mktime(datetime(now.year, now.month, 1).timetuple()) * 1000)
        end_ms = int(time.time() * 1000)
        
        url = f"{self.base_url}/{endpoint}"
        params = {"start": start_ms, "end": end_ms}
        
        res = requests.get(url, headers=self.headers, params=params)
        if res.status_code == 200:
            return res.json()
        print(f"Errore {endpoint}: {res.status_code} - {res.text}")
        return {}

def main():
    if not KINSTA_SITE_ID or not KINSTA_ENV_ID:
        print("ERRORE: Assicurati di aver impostato sia KINSTA_SITE_ID che KINSTA_ENV_ID!")
        return

    reporter = KinstaPrecisionReporter()
    
    # 1. Recupero Dati (Mapping su Documentazione)
    v_raw = reporter.fetch("visits")
    b_raw = reporter.fetch("server-bandwidth")
    d_raw = reporter.fetch("disk-space")

    # Estrazione: data -> environment -> [metric] -> report
    # Secondo i documenti: {"data": {"environment": {"visits": {"report": [...]}}}}
    v_report = v_raw.get('data', {}).get('environment', {}).get('visits', {}).get('report', [])
    b_report = b_raw.get('data', {}).get('environment', {}).get('server_bandwidth', {}).get('report', [])
    d_report = d_raw.get('data', {}).get('environment', {}).get('disk_space', {}).get('report', [])

    total_visits = sum(int(i.get('value', 0)) for i in v_report)
    total_bw_mb = round(sum(int(i.get('value', 0)) for i in b_report) / (1024*1024), 2)
    last_disk_mb = round(int(d_report[-1].get('value', 0)) / (1024*1024), 2) if d_report else 0

    print(f"Dati FINALMENTE estratti: {total_visits} visite, {total_bw_mb} MB banda")

    # 2. Generazione Grafico
    plt.figure(figsize=(10, 4))
    if v_report:
        days = [i['datetime'][8:10] for i in v_report]
        counts = [int(i['value']) for i in v_report]
        plt.fill_between(days, counts, color='#5333ed', alpha=0.1)
        plt.plot(days, counts, color='#5333ed', marker='o')
    plt.title("Daily Visits Trend (Analytics API)")
    plt.savefig("chart.png")

    # 3. Analisi AI e PDF
    try:
        analysis = model.generate_content(
            f"Analizza: {total_visits} visite, {total_bw_mb}MB banda. Report professionale.",
            request_options=RequestOptions(api_version='v1')
        ).text
    except:
        analysis = "Il sito mostra un utilizzo delle risorse regolare."

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Kinsta Precise Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Visite totali questo mese: {total_visits}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 10, f"Banda Server: {total_bw_mb} MB", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 10, f"Spazio Disco: {last_disk_mb} MB", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if os.path.exists("chart.png"):
        pdf.image("chart.png", x=10, y=70, w=180)

    pdf.set_y(165)
    pdf.multi_cell(0, 7, analysis)
    pdf.output("Kinsta_Final_Analytics.pdf")

if __name__ == "__main__":
    main()
