import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google import generativeai as genai
from fpdf import FPDF, XPos, YPos

# --- Configurazione ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

class KinstaFinalAnalyst:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics/visits"

    def fetch_visits(self, start_date, end_date):
        params = {
            "company_id": KINSTA_COMPANY_ID,
            "from": f"{start_date}T00:00:00.000Z",
            "to": f"{end_date}T23:59:59.000Z",
            "time_span": "30_days"
        }
        res = requests.get(self.base_url, headers=self.headers, params=params)
        if res.status_code == 200:
            raw = res.json()
            try:
                data_node = raw['analytics']['analytics_response']['data'][0]
                return data_node.get('total', 0), data_node.get('dataset', [])
            except: return 0, []
        return 0, []

def main():
    analyst = KinstaFinalAnalyst()
    
    # Recupero dati reali
    total_curr, dataset_curr = analyst.fetch_visits("2026-03-29", "2026-04-04")
    total_prev, _ = analyst.fetch_visits("2026-03-22", "2026-03-28")

    # 1. Generazione Grafico (Ripristinato)
    plt.figure(figsize=(10, 4))
    if dataset_curr:
        days = [d['key'][8:10] for d in dataset_curr]
        counts = [int(d['value']) for d in dataset_curr]
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2, label='Visite Giornaliere')
        plt.fill_between(days, counts, color='#5333ed', alpha=0.1)
        plt.title("Andamento Visite Settimanali (29 Mar - 04 Apr)")
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
    plt.tight_layout()
    plt.savefig("weekly_chart.png")

    # 2. Analisi AI
    prompt = f"""
    Analizza questo trend di traffico:
    - Settimana Corrente (29 Mar - 04 Apr): {total_curr} visite.
    - Settimana Precedente: {total_prev} visite.
    Dati giornalieri: {dataset_curr}.
    Commenta la crescita e i picchi giornalieri in modo professionale.
    """
    try:
        response = model.generate_content(prompt)
        summary = response.text if response.text else "Analisi generata."
    except:
        summary = "Analisi AI non disponibile al momento."

    # 3. Generazione PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, "Kinsta Executive Weekly Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Riepilogo Numerico
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0)
    pdf.cell(0, 10, f"Visite Settimana Corrente: {total_curr}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 10, f"Visite Settimana Precedente: {total_prev}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Grafico (Posizionato centralmente)
    pdf.image("weekly_chart.png", x=10, y=55, w=185)
    
    # Tabella Giornaliera (Spostata sotto il grafico)
    pdf.set_y(140)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 8, " Data", 1, 0, 'L', True)
    pdf.cell(95, 8, " Visite", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", "", 10)
    for entry in dataset_curr:
        pdf.cell(95, 7, f" {entry['key'][:10]}", 1)
        pdf.cell(95, 7, f" {entry['value']}", 1, 1, 'C')

    # Executive Summary
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, "Executive Insights (AI Analysis)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 6, summary)
    
    pdf.output("Kinsta_Final_Complete_Report.pdf")

if __name__ == "__main__":
    main()
