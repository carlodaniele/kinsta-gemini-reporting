import os
import requests
import matplotlib.pyplot as plt
from google import generativeai as genai
from fpdf import FPDF

# Configurazione dai Secrets di GitHub
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
ENV_ID = os.getenv("KINSTA_ENV_ID") # L'ID dell'ambiente (es. live)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaAnalytics:
    def __init__(self, api_key, env_id):
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{env_id}/analytics"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.params = {"time_span": "last_7_days"}

    def fetch_metric(self, endpoint):
        response = requests.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=self.params)
        response.raise_for_status()
        return response.json()

def run_test():
    kinsta = KinstaAnalytics(KINSTA_API_KEY, ENV_ID)
    
    # Recupero dati puntuali dai 4 endpoint della documentazione
    data = {
        "visite": kinsta.fetch_metric("visits"),
        "banda_server": kinsta.fetch_metric("server-bandwidth"),
        "banda_cdn": kinsta.fetch_metric("cdn-bandwidth"),
        "disco": kinsta.fetch_metric("disk-usage")
    }

    # Estrazione dati per il grafico (Visite giornaliere)
    # Basato sulla struttura tipica Kinsta: {"data": [{"datetime": ..., "value": ...}]}
    visite_giornaliere = [int(item['value']) for item in data['visite']['data']]
    giorni = [item['datetime'][:10] for item in data['visite']['data']] # Prende solo YYYY-MM-DD

    # Creazione Grafico
    plt.figure(figsize=(10, 5))
    plt.fill_between(giorni, visite_giornaliere, color="#5333ed", alpha=0.3)
    plt.plot(giorni, visite_giornaliere, color="#5333ed", linewidth=2)
    plt.title("Visite Uniche - Ultimi 7 Giorni")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("chart_visite.png")

    # Analisi Gemini
    prompt = f"""
    Analizza questi dati tecnici di Kinsta per un cliente di un'agenzia web.
    Semplifica i termini tecnici (Banda, Spazio Disco, Visite).
    Dati: {data}
    Scrivi un commento professionale di massimo 150 parole.
    """
    ai_response = model.generate_content(prompt)

    # Generazione PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 20, "Report Settimanale Performance", ln=True, align="C")
    
    pdf.image("chart_visite.png", x=10, y=40, w=190)
    
    pdf.set_y(140)
    pdf.set_font("helvetica", "", 12)
    pdf.multi_cell(0, 8, ai_response.text)
    
    pdf.output("Report_Kinsta_Gemini.pdf")

if __name__ == "__main__":
    run_test()
