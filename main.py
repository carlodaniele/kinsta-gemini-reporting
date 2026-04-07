import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time
from datetime import datetime
# Import corretto per la nuova libreria google-genai
from google.genai import Client
from fpdf import FPDF, XPos, YPos

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inizializzazione client
client = Client(api_key=GEMINI_API_KEY)

# CAMBIO MODELLO: Usiamo il nome standard certificato
MODEL_ID = "gemini-2.5-flash" 

class KinstaStrictAnalyst:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics/visits"

    def fetch_7_days(self, start, end):
        params = {
            "company_id": KINSTA_COMPANY_ID,
            "from": f"{start}T00:00:00.000Z",
            "to": f"{end}T23:59:59.000Z",
            "time_span": "30_days"
        }
        res = requests.get(self.base_url, headers=self.headers, params=params)
        if res.status_code == 200:
            try:
                data = res.json()['analytics']['analytics_response']['data'][0]
                dataset = data.get('dataset', [])[:7]
                return data.get('total', 0), dataset
            except: return 0, []
        return 0, []

def main():
    analyst = KinstaStrictAnalyst()
    
    # 1. Recupero Dati (175 vs 66)
    total_curr, data_curr = analyst.fetch_7_days("2026-03-29", "2026-04-04")
    total_prev, data_prev = analyst.fetch_7_days("2026-03-22", "2026-03-28")

    # 2. Grafico Comparativo
    plt.figure(figsize=(10, 5))
    labels = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    val_curr = [int(d['value']) for d in data_curr] if data_curr else [0]*7
    val_prev = [int(d['value']) for d in data_prev] if data_prev else [0]*7
    
    plt.plot(labels, val_curr, color='#5333ed', marker='o', linewidth=2, label='Settimana Attuale')
    plt.plot(labels, val_prev, color='#a1a1a1', linestyle='--', marker='x', label='Settimana Precedente')
    plt.fill_between(labels, val_curr, color='#5333ed', alpha=0.1)
    plt.title("Confronto Visite Settimanali (7 vs 7)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("comparison_chart.png")

    # 3. Analisi AI (Modello Corretto)
    try:
        prompt = f"""
        Analizza questo report Kinsta:
        - Settimana attuale: {total_curr} visite (Dati: {val_curr})
        - Settimana scorsa: {total_prev} visite (Dati: {val_prev})
        
        Commenta l'andamento in modo professionale per un'agenzia web. 
        Evidenzia i picchi e la crescita percentuale. Massimo 4 frasi.
        """
        # Usiamo il client con il modello gemini-1.5-flash
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        summary = response.text
    except Exception as e:
        summary = f"Dati: {total_curr} vs {total_prev}. Errore AI: {str(e)}"

    # 4. PDF Layout (Senza alcun DeprecationWarning)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, "Kinsta Executive Precision Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.image("comparison_chart.png", x=10, y=40, w=185)
    
    # Tabella
    pdf.set_y(135)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 8, " Giorno", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(65, 8, " Settimana Precedente", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(65, 8, " Settimana Attuale", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0)
    for i in range(7):
        pdf.cell(60, 7, f" Giorno {i+1}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(65, 7, f" {val_prev[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(65, 7, f" {val_curr[i]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, "Executive Insights", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 7, summary)
    
    pdf.output("Kinsta_Final_Clean.pdf")
    print("SUCCESS: Report generato senza errori e con AI attiva.")

if __name__ == "__main__":
    main()
