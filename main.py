import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google import generativeai as genai
from google.generativeai.types import RequestOptions
from fpdf import FPDF, XPos, YPos

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID") # <--- AGGIUNGI QUESTO NEI SECRETS
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaWeeklyAnalyst:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics/visits"

    def fetch_period(self, start_date, end_date):
        """Richiama i dati per un intervallo ISO specifico."""
        params = {
            "company_id": KINSTA_COMPANY_ID,
            "from": f"{start_date}T00:00:00.000Z",
            "to": f"{end_date}T23:59:59.000Z",
            "time_span": "7_days" # Anche se usiamo from/to, l'API richiede coerenza
        }
        print(f"Fetching: {start_date} to {end_date}")
        res = requests.get(self.base_url, headers=self.headers, params=params)
        
        if res.status_code == 200:
            # Secondo la documentazione, i dati sono in data.environment.visits.report
            return res.json().get('data', {}).get('environment', {}).get('visits', {}).get('report', [])
        else:
            print(f"Errore API: {res.status_code} - {res.text}")
            return []

def main():
    analyst = KinstaWeeklyAnalyst()

    # 1. Recupero le due settimane richieste
    # Settimana A: 29 Marzo - 04 Aprile
    current_week = analyst.fetch_period("2026-03-29", "2026-04-04")
    # Settimana B: 22 Marzo - 28 Marzo
    previous_week = analyst.fetch_period("2026-03-22", "2026-03-28")

    total_curr = sum(int(i.get('value', 0)) for i in current_week)
    total_prev = sum(int(i.get('value', 0)) for i in previous_week)
    
    print(f"Settimana Corrente: {total_curr} visite")
    print(f"Settimana Precedente: {total_prev} visite")

    # 2. Creazione Grafico Comparativo
    plt.figure(figsize=(10, 5))
    if current_week:
        days = [i['datetime'][8:10] for i in current_week]
        values = [int(i['value']) for i in current_week]
        plt.bar(days, values, color='#5333ed', label='29 Mar - 04 Apr')
    
    plt.title("Analisi Visite Settimanali")
    plt.ylabel("Numero Visite")
    plt.legend()
    plt.savefig("weekly_trend.png")

    # 3. Analisi AI
    prompt = f"Analizza il trend visite: questa settimana {total_curr}, scorsa settimana {total_prev}. Commenta l'andamento per il cliente."
    try:
        summary = model.generate_content(prompt, request_options=RequestOptions(api_version='v1')).text
    except:
        summary = "Analisi non disponibile."

    # 4. Generazione PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Kinsta Weekly Comparison Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Settimana 29 Mar - 04 Apr: {total_curr} visite", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 10, f"Settimana 22 Mar - 28 Mar: {total_prev} visite", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    if os.path.exists("weekly_trend.png"):
        pdf.image("weekly_trend.png", x=10, y=60, w=180)
    
    pdf.set_y(160)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, summary)
    
    pdf.output("Kinsta_Weekly_Comparison.pdf")

if __name__ == "__main__":
    main()
