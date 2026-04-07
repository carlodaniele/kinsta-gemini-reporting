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

# --- Configurazione ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID") 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaPrecisionReporter:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        # L'URL base per le analytics NON include l'ID ambiente nel path
        self.base_url = "https://api.kinsta.com/v2/analytics"

    def fetch(self, endpoint):
        now = datetime.now()
        # Calcolo timestamp (start: inizio mese, end: ora)
        start_ms = int(time.mktime(datetime(now.year, now.month, 1).timetuple()) * 1000)
        end_ms = int(time.time() * 1000)
        
        url = f"{self.base_url}/{endpoint}"
        # L'environment_id va passato come PARAMETRO, non nel path
        params = {
            "environment_id": KINSTA_ENV_ID,
            "start": start_ms,
            "end": end_ms
        }
        
        res = requests.get(url, headers=self.headers, params=params)
        if res.status_code == 200:
            return res.json()
        print(f"Errore {endpoint}: {res.status_code} - {res.text}")
        return {}

def main():
    reporter = KinstaPrecisionReporter()
    
    # Recupero dati reali
    v_raw = reporter.fetch("visits")
    b_raw = reporter.fetch("server-bandwidth")
    d_raw = reporter.fetch("disk-space")

    # Mapping basato sulla risposta reale: data -> [metrica] -> report
    # Nota: Rimuoviamo 'site' o 'environment' dal path del JSON perché l'API restituisce i dati direttamente
    visits_list = v_raw.get('data', {}).get('visits', {}).get('report', [])
    bw_list = b_raw.get('data', {}).get('server_bandwidth', {}).get('report', [])
    disk_list = d_raw.get('data', {}).get('disk_space', {}).get('report', [])

    total_visits = sum(int(i.get('value', 0)) for i in visits_list)
    total_bw_mb = round(sum(int(i.get('value', 0)) for i in bw_list) / (1024*1024), 2)
    last_disk_mb = round(int(disk_list[-1].get('value', 0)) / (1024*1024), 2) if disk_list else 0

    print(f"Dati FINALMENTE estratti: {total_visits} visite, {total_bw_mb} MB banda")

    # Creazione Grafico
    plt.figure(figsize=(10, 4))
    if visits_list:
        days = [i['datetime'][8:10] for i in visits_list]
        counts = [int(i['value']) for i in visits_list]
        plt.fill_between(days, counts, color='#5333ed', alpha=0.1)
        plt.plot(days, counts, color='#5333ed', marker='o')
    plt.savefig("chart.png")

    # PDF con sintassi corretta
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Kinsta Analytics Finale", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Tabella
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 10, " Metrica", 1, new_x=XPos.RIGHT)
    pdf.cell(60, 10, " Valore", 1, new_x=XPos.RIGHT)
    pdf.cell(60, 10, " Dettaglio", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 10, " Visite Totali", 1, new_x=XPos.RIGHT)
    pdf.cell(60, 10, str(total_visits), 1, new_x=XPos.RIGHT)
    pdf.cell(60, 10, "Mese Corrente", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.image("chart.png", x=10, y=60, w=180)
    pdf.output("Kinsta_Success_Report.pdf")

if __name__ == "__main__":
    main()
