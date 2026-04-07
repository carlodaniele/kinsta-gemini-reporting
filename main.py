import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import calendar
from datetime import datetime
from google import generativeai as genai
from google.generativeai.types import RequestOptions
from fpdf import FPDF, XPos, YPos

# --- Configurazione ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_SITE_ID = os.getenv("KINSTA_SITE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_kinsta_usage(time_span):
    url = f"https://api.kinsta.com/v2/sites/{KINSTA_SITE_ID}/usage/visits/{time_span}"
    headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
    res = requests.get(url, headers=headers)
    return res.json().get('site', {}).get('this_month_usage', {}) if res.status_code == 200 else {}

def main():
    print("Recupero dati comparativi...")
    current_data = get_kinsta_usage("this-month")
    last_data = get_kinsta_usage("last-month")

    # Dati correnti
    visits_list = current_data.get('data', [])
    total_current = current_data.get('visits', 0)
    total_last = last_data.get('visits', 0)
    
    # Calcolo scostamento
    if total_last > 0:
        change = ((total_current - total_last) / total_last) * 100
        change_text = f"{'+' if change > 0 else ''}{round(change, 1)}%"
    else:
        change_text = "N/A"

    # Previsione
    today = datetime.now()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = len(visits_list) if visits_list else today.day
    estimated = round((total_current / days_passed) * days_in_month) if days_passed > 0 else 0

    # Grafico (Trend giornaliero)
    if visits_list:
        plt.figure(figsize=(10, 4))
        days = [i['datetime'][8:10] for i in visits_list] # Solo il giorno DD
        counts = [int(i['value']) for i in visits_list]
        plt.fill_between(days, counts, color='#5333ed', alpha=0.2)
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2)
        plt.title(f"Andamento Visite Giornaliere (Giorno del Mese)")
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.savefig("trend.png")

    # Analisi Gemini
    prompt = f"""
    Analizza i dati traffico di Carlo's Company:
    - Visite mese attuale (ad oggi): {total_current}
    - Visite mese scorso: {total_last}
    - Scostamento: {change_text}
    - Previsione fine mese: {estimated}
    Scrivi un'analisi per il cliente evidenziando se il trend è positivo. Sii professionale.
    """
    try:
        analysis = model.generate_content(prompt, request_options=RequestOptions(api_version='v1')).text
    except:
        analysis = "Analisi non disponibile. Il traffico attuale è in fase di monitoraggio."

    # Generazione PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Report Comparativo Performance Web", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Tabella Comparativa
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(60, 10, "Periodo", 1, 0, 'C', True)
    pdf.cell(60, 10, "Visite Totali", 1, 0, 'C', True)
    pdf.cell(60, 10, "Previsione/Trend", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(60, 10, "Mese Scorso", 1, 0, 'C')
    pdf.cell(60, 10, str(total_last), 1, 0, 'C')
    pdf.cell(60, 10, "-", 1, 1, 'C')
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(60, 10, "Mese Corrente", 1, 0, 'C')
    pdf.cell(60, 10, str(total_current), 1, 0, 'C')
    pdf.cell(60, 10, f"{estimated} (est.)", 1, 1, 'C')

    # Spazio per il grafico
    if os.path.exists("trend.png"):
        pdf.image("trend.png", x=10, y=85, w=190)
    
    # Box Analisi AI
    pdf.set_y(180)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, "Executive Summary & AI Insights", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, analysis)

    pdf.output("Kinsta_Professional_Report.pdf")
    print("SUCCESS: Report professionale generato.")

if __name__ == "__main__":
    main()
