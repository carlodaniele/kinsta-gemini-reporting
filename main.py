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
# ATTENZIONE: Qui devi inserire l'Environment ID (es. 586...-...)
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID") 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaPrecisionReporter:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        # Endpoint corretto: /environments/{env_id}/analytics
        self.base_url = f"https://api.kinsta.com/v2/environments/{KINSTA_ENV_ID}/analytics"

    def get_time_range(self):
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
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
    if not KINSTA_ENV_ID:
        print("ERRORE: Devi impostare KINSTA_ENV_ID nei Secrets di GitHub!")
        return

    reporter = KinstaPrecisionReporter()
    
    # 1. Recupero Dati Analytics
    v_raw = reporter.fetch("visits")
    b_raw = reporter.fetch("server-bandwidth")
    d_raw = reporter.fetch("disk-space")

    # 2. Estrazione (Percorso corretto: data -> environment -> [metric] -> report)
    env_data = v_raw.get('data', {}).get('environment', {})
    visits_list = env_data.get('visits', {}).get('report', [])
    
    bw_data = b_raw.get('data', {}).get('environment', {})
    bw_list = bw_data.get('server_bandwidth', {}).get('report', [])
    
    dk_data = d_raw.get('data', {}).get('environment', {})
    disk_list = dk_data.get('disk_space', {}).get('report', [])

    total_visits = sum(int(i.get('value', 0)) for i in visits_list)
    total_bw_mb = round(sum(int(i.get('value', 0)) for i in bw_list) / (1024*1024), 2)
    last_disk_mb = round(int(disk_list[-1].get('value', 0)) / (1024*1024), 2) if disk_list else 0

    print(f"Dati estratti: {total_visits} visite, {total_bw_mb} MB banda")

    # 3. Grafico
    plt.figure(figsize=(10, 4))
    if visits_list:
        days = [i['datetime'][8:10] for i in visits_list]
        counts = [int(i['value']) for i in visits_list]
        plt.fill_between(days, counts, color='#5333ed', alpha=0.1)
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2)
    else:
        plt.text(0.5, 0.5, "Nessun dato trovato per l'ambiente fornito", ha='center')
    plt.title("Analisi Traffico Ambiente Live")
    plt.savefig("chart.png")

    # 4. Gemini & PDF (Sintassi moderna senza warning)
    prompt = f"Analizza: {total_visits} visite, {total_bw_mb}MB banda, {last_disk_mb}MB disco."
    try:
        summary = model.generate_content(prompt, request_options=RequestOptions(api_version='v1')).text
    except:
        summary = "Monitoraggio performance completato."

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Kinsta Environment Analytics", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    
    pdf.cell(60, 10, " Metrica", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(60, 10, " Valore", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(60, 10, " Dettaglio", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    
    pdf.set_font("Helvetica", "", 10)
    data_rows = [
        ["Visite Totali", str(total_visits), "Mese Corrente"],
        ["Banda Server", f"{total_bw_mb} MB", "HTTP Traffic"],
        ["Spazio Disco", f"{last_disk_mb} MB", "Storage Live"]
    ]
    for r in data_rows:
        pdf.cell(60, 8, f" {r[0]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(60, 8, f" {r[1]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(60, 8, f" {r[2]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if os.path.exists("chart.png"):
        pdf.image("chart.png", x=10, y=90, w=190)

    pdf.set_y(190)
    pdf.multi_cell(0, 6, summary)
    pdf.output("Kinsta_Env_Report.pdf")

if __name__ == "__main__":
    main()
