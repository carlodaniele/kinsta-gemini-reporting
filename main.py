import os
import requests
import matplotlib
matplotlib.use('Agg') # Forza backend senza monitor
import matplotlib.pyplot as plt
import calendar # Import separato, risolve l'errore precedente
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

def main():
    # 1. Recupero dati da Kinsta
    url = f"https://api.kinsta.com/v2/sites/{KINSTA_SITE_ID}/usage/visits/this-month"
    headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
    
    print("Recupero dati visite...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Errore API: {response.text}")
        return

    data = response.json().get('site', {}).get('this_month_usage', {})
    visits_list = data.get('data', [])
    total_to_date = data.get('visits', 0)

    # 2. Logica di Previsione (Forecasting)
    today = datetime.now()
    # Calcoliamo quanti giorni mancano alla fine del mese
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = len(visits_list) if visits_list else today.day
    
    avg_daily = total_to_date / days_passed if days_passed > 0 else 0
    estimated_total = round(avg_daily * days_in_month)

    # 3. Creazione Grafico
    days = [item['datetime'][:10] for item in visits_list]
    counts = [int(item['value']) for item in visits_list]

    plt.figure(figsize=(10, 5))
    plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2, label='Visite Reali')
    plt.title(f"Andamento Visite - {today.strftime('%B %Y')}")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("trend.png")

    # 4. Analisi Gemini
    prompt = f"""
    Analizza brevemente questo traffico hosting:
    - Visite attuali: {total_to_date}
    - Previsione fine mese: {estimated_total}
    Scrivi 2 righe di commento professionale per il cliente.
    """
    try:
        analysis = model.generate_content(prompt, request_options=RequestOptions(api_version='v1')).text
    except:
        analysis = f"Il sito sta procedendo con una media di {round(avg_daily, 1)} visite al giorno."

    # 5. Generazione PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Report Previsionale Traffico", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Visite totali (al {today.strftime('%d/%m')}): {total_to_date}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"STIMA FINE MESE: {estimated_total} visite", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    if os.path.exists("trend.png"):
        pdf.image("trend.png", x=10, y=60, w=180)
    
    pdf.set_y(155)
    pdf.set_font("Helvetica", "I", 11)
    pdf.multi_cell(0, 7, analysis)
    
    pdf.output("Report_Kinsta.pdf")
    print("SUCCESS: Report generato.")

if __name__ == "__main__":
    main()
