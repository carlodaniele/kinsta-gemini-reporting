import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# Passiamo alla nuova libreria ufficiale per evitare i FutureWarning
from google import genai 
from fpdf import FPDF, XPos, YPos

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inizializzazione nuovo client Google GenAI
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-1.5-flash-latest"

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
                # Struttura esatta dal JSON Mintlify caricato in precedenza
                data = res.json()['analytics']['analytics_response']['data'][0]
                dataset = data.get('dataset', [])[:7]
                return data.get('total', 0), dataset
            except: return 0, []
        return 0, []

def main():
    analyst = KinstaStrictAnalyst()
    
    # 1. Recupero Dati
    total_curr, data_curr = analyst.fetch_7_days("2026-03-29", "2026-04-04")
    total_prev, data_prev = analyst.fetch_7_days("2026-03-22", "2026-03-28")

    # 2. Grafico Comparativo
    plt.figure(figsize=(10, 5))
    labels = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    val_curr = [int(d['value']) for d in data_curr] if data_curr else [0]*7
    val_prev = [int(d['value']) for d in data_prev] if data_prev else [0]*7
    
    plt.plot(labels, val_curr, color='#5333ed', marker='o', linewidth=2, label='Settimana Attuale')
    plt.plot(labels, val_prev, color='#a1a1a1', linestyle='--', marker='x', label='Settimana Precedente')
    plt.title("Confronto Visite 7 vs 7 Giorni")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("comparison_chart.png")

    # 3. Analisi AI (Vera chiamata al modello)
    # Rimuoviamo il fallback statico per vedere l'errore reale se fallisce
    try:
        prompt_text = f"""
        Analizza questi dati di traffico Kinsta per un report di agenzia:
        - Totale settimana attuale: {total_curr}
        - Totale settimana precedente: {total_prev}
        - Dati giornalieri (Attuale): {val_curr}
        - Dati giornalieri (Precedente): {val_prev}
        
        Commenta il trend, i picchi e la variazione percentuale. 
        Sii tecnico e professionale. Massimo 100 parole.
        """
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt_text
        )
        summary = response.text
    except Exception as e:
        # Se fallisce, ora stampiamo l'errore tecnico per risolvere il problema
        summary = f"ERRORE CRITICO AI: {str(e)}"

    # 4. PDF Layout
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, "Kinsta 7-Day Precision Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.image("comparison_chart.png", x=10, y=40, w=185)
    
    # Tabella Comparativa
    pdf.set_y(135)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 8, " Giorno", 1, 0, 'L', True)
    pdf.cell(65, 8, " Settimana Precedente", 1, 0, 'C', True)
    pdf.cell(65, 8, " Settimana Attuale", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", "", 10)
    for i in range(7):
        pdf.cell(60, 7, f" Giorno {i+1}", 1)
        pdf.cell(65, 7, f" {val_prev[i]}", 1, 0, 'C')
        pdf.cell(65, 7, f" {val_curr[i]}", 1, 1, 'C')

    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, "Executive Insights", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, summary)
    
    pdf.output("Kinsta_Final_Report_V2.pdf")

if __name__ == "__main__":
    main()
