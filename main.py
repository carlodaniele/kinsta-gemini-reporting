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

# Configurazione Gemini con l'ultimo modello Flash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

class KinstaMintlifyAnalyst:
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
    analyst = KinstaMintlifyAnalyst()
    
    # Recupero dati
    total_curr, dataset_curr = analyst.fetch_visits("2026-03-29", "2026-04-04")
    total_prev, _ = analyst.fetch_visits("2026-03-22", "2026-03-28")

    # --- CHIAMATA AI (CORRETTA) ---
    prompt = f"""
    Analizza questo report di traffico web Kinsta:
    - Settimana 29 Mar - 04 Apr: {total_curr} visite.
    - Settimana precedente: {total_prev} visite.
    - Dati giornalieri: {dataset_curr}.
    
    Commenta il trend in modo professionale per un'agenzia web (max 4 righe).
    """
    
    try:
        response = model.generate_content(prompt)
        # Verifichiamo la presenza di una risposta valida
        if response and response.text:
            summary = response.text
        else:
            summary = "Analisi generata ma senza contenuto testuale. Verificare le impostazioni di sicurezza."
    except Exception as e:
        summary = f"Errore durante la chiamata a Gemini: {str(e)}"

    # --- GENERAZIONE PDF ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Kinsta Weekly Analytics Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Sezione Sintesi
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0)
    pdf.cell(0, 10, f"Visite Totali (Settimana Corrente): {total_curr}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 10, f"Visite Totali (Settimana Precedente): {total_prev}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # --- TABELLA GIORNALIERA ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 8, " Data", 1, 0, 'L', True)
    pdf.cell(95, 8, " Visite", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", "", 10)
    for entry in dataset_curr:
        clean_date = entry['key'][:10]
        pdf.cell(95, 7, f" {clean_date}", 1)
        pdf.cell(95, 7, f" {entry['value']}", 1, 1, 'C')

    # Sezione AI
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, "Executive Insights (AI Analysis)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 6, summary)
    
    pdf.output("Kinsta_Final_Report.pdf")
    print("SUCCESS: Report PDF generato con successo.")

if __name__ == "__main__":
    main()
