import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google import generativeai as genai
from google.generativeai.types import RequestOptions
from fpdf import FPDF, XPos, YPos

# --- Configurazione ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaMintlifyAnalyst:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics"

    def fetch_visits(self, start_date, end_date):
        """Estrae le visite seguendo lo schema: analytics -> analytics_response -> data -> dataset"""
        params = {
            "company_id": KINSTA_COMPANY_ID,
            "from": f"{start_date}T00:00:00.000Z",
            "to": f"{end_date}T23:59:59.000Z",
            "time_span": "30_days"
        }
        url = f"{self.base_url}/visits"
        res = requests.get(url, headers=self.headers, params=params)
        
        if res.status_code == 200:
            raw = res.json()
            try:
                # Navigazione precisa nel JSON fornito
                analytics_data = raw['analytics']['analytics_response']['data'][0]
                total = analytics_data.get('total', 0)
                dataset = analytics_data.get('dataset', [])
                return total, dataset
            except (KeyError, IndexError):
                print(f"Struttura JSON imprevista per il periodo {start_date}")
                return 0, []
        return 0, []

def main():
    analyst = KinstaMintlifyAnalyst()

    # 1. Recupero Dati (Settimana Corrente e Precedente)
    total_curr, dataset_curr = analyst.fetch_visits("2026-03-29", "2026-04-04")
    total_prev, _ = analyst.fetch_visits("2026-03-22", "2026-03-28")

    print(f"Dati Verificati: Corrente {total_curr}, Precedente {total_prev}")

    # 2. Creazione Grafico con dati REALI dal dataset
    plt.figure(figsize=(10, 5))
    if dataset_curr:
        # 'key' è la data, 'value' è il numero di visite come stringa
        days = [d['key'][8:10] for d in dataset_curr]
        counts = [int(d['value']) for d in dataset_curr]
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2)
        plt.fill_between(days, counts, color='#5333ed', alpha=0.1)
    else:
        plt.text(0.5, 0.5, "Nessun dato nel dataset", ha='center')
    
    plt.title("Visite Settimanali (Dati Reali API)")
    plt.savefig("weekly_chart.png")

    # 3. Analisi Gemini
    prompt = f"Analizza il trend visite del sito: questa settimana {total_curr}, scorsa {total_prev}. Commento tecnico breve."
    try:
        summary = model.generate_content(prompt, request_options=RequestOptions(api_version='v1')).text
    except:
        summary = "Analisi non disponibile."

    # 4. PDF Layout
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Kinsta Weekly Analytics Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Periodo 29 Mar - 04 Apr: {total_curr} visite totali", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 10, f"Periodo 22 Mar - 28 Mar: {total_prev} visite totali", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    if os.path.exists("weekly_chart.png"):
        pdf.image("weekly_chart.png", x=10, y=60, w=180)
    
    pdf.set_y(160)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, summary)
    
    pdf.output("Kinsta_Final_Success.pdf")
    print("SUCCESS: Report generato basandosi sulla struttura Mintlify.")

if __name__ == "__main__":
    main()
