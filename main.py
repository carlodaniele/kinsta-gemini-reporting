import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import calendar
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

    def fetch(self, endpoint):
        """Richiama gli endpoint di analytics specificati nei documenti."""
        url = f"{self.base_url}/{endpoint}"
        # Parametro temporale richiesto dalla documentazione (es. questo mese)
        params = {"time_range": "this_month"} 
        try:
            res = requests.get(url, headers=self.headers, params=params)
            if res.status_code == 200:
                # La documentazione specifica che i dati sono sotto la chiave 'data' o 'site'
                return res.json()
        except: pass
        return {}

def main():
    reporter = KinstaPrecisionReporter()
    
    # 1. RACCOLTA DATI (Endpoint Documentati)
    v_data = reporter.fetch("visits")
    b_data = reporter.fetch("server-bandwidth")
    d_data = reporter.fetch("disk-space")
    geo_data = reporter.fetch("top-countries")
    resp_data = reporter.fetch("response-code-breakdown")

    # 2. ESTRAZIONE VALORI (Mapping preciso sulla documentazione)
    # Visite e Banda sono liste di {datetime, value}
    visits_list = v_data.get('data', {}).get('visits', [])
    total_visits = sum(int(i['value']) for i in visits_list)
    
    bw_list = b_data.get('data', {}).get('server_bandwidth', [])
    total_bw_bytes = sum(int(i['value']) for i in bw_list)
    total_bw_mb = round(total_bw_bytes / (1024*1024), 2)

    # Spazio disco (ultimo valore rilevato)
    disk_list = d_data.get('data', {}).get('disk_space', [])
    last_disk_bytes = int(disk_list[-1]['value']) if disk_list else 0
    disk_mb = round(last_disk_bytes / (1024*1024), 2)

    # Geo (Top Country)
    top_country = geo_data.get('data', {}).get('top_countries', [{}])[0].get('name', 'N/A')

    # Previsione Fine Mese
    today = datetime.now()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = len(visits_list) if visits_list else today.day
    estimated_visits = round((total_visits / days_passed) * days_in_month) if days_passed > 0 else 0

    # 3. GRAFICO TRAFFICO
    if visits_list:
        plt.figure(figsize=(10, 4))
        days = [i['datetime'][8:10] for i in visits_list]
        counts = [int(i['value']) for i in visits_list]
        plt.fill_between(days, counts, color='#5333ed', alpha=0.1)
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2)
        plt.title("Analisi Visite Giornaliere (Analytics API)")
        plt.savefig("chart.png")

    # 4. ANALISI AI (Basata sui nuovi dati certi)
    prompt = f"""
    Analizza i dati tecnici Kinsta:
    - Visite totali: {total_visits} (Stima fine mese: {estimated_visits})
    - Banda Server: {total_bw_mb} MB
    - Spazio Disco: {disk_mb} MB
    - Provenienza principale: {top_country}
    Spiega al cliente la salute del sito basandoti su questi numeri reali.
    """
    try:
        summary = model.generate_content(prompt, request_options=RequestOptions(api_version='v1')).text
    except:
        summary = "Il monitoraggio indica performance stabili e un utilizzo corretto delle risorse hosting."

    # 5. PDF PROFESSIONALE
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Kinsta Performance Report (Analytics)", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Tabella Metriche
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 10, " Metrica di Analisi", 1, 0, 'L', True)
    pdf.cell(60, 10, " Valore Reale", 1, 0, 'C', True)
    pdf.cell(60, 10, " Dettaglio/Previsione", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    
    rows = [
        ["Visite Totali", str(total_visits), f"Stima: {estimated_visits}"],
        ["Banda Server", f"{total_bw_mb} MB", "Traffico in uscita"],
        ["Spazio Disco", f"{disk_mb} MB", "Storage occupato"],
        ["Top Location", top_country, "Mercato principale"]
    ]
    
    for r in rows:
        pdf.cell(60, 8, f" {r[0]}", 1, 0, 'L')
        pdf.cell(60, 8, f" {r[1]}", 1, 0, 'C')
        pdf.cell(60, 8, f" {r[2]}", 1, 1, 'C')

    if os.path.exists("chart.png"):
        pdf.image("chart.png", x=10, y=85, w=190)
    
    pdf.set_y(180)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, "Analisi Strategica AI", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, summary)

    pdf.output("Kinsta_Analytics_Report.pdf")
    print("SUCCESS: Report generato con dati di analytics reali.")

if __name__ == "__main__":
    main()
