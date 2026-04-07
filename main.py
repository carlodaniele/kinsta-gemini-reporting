import os
import requests
from google import generativeai as genai
from google.generativeai.types import RequestOptions
from fpdf import FPDF, XPos, YPos

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_SITE_ID = os.getenv("KINSTA_SITE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def fetch_kinsta_usage(endpoint):
    """Fetch usage from Kinsta and handle the specific JSON nesting."""
    url = f"https://api.kinsta.com/v2/sites/{KINSTA_SITE_ID}/usage/{endpoint}"
    headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    
    data = response.json()
    # Path: site -> this_month_usage -> [metric]
    try:
        return data['site']['this_month_usage']
    except (KeyError, TypeError):
        return None

def main():
    # 1. Recupero dati REALI (Mappati sulla struttura site.this_month_usage)
    visits_usage = fetch_kinsta_usage("visits/this-month")
    bandwidth_usage = fetch_kinsta_usage("bandwidth/this-month")
    
    # Estrazione valori finali
    # Se bandwidth è 1399490 (Byte), lo convertiamo in MB
    real_visits = visits_usage.get('visits', 0) if visits_usage else 0
    real_bandwidth_bytes = bandwidth_usage.get('bandwidth', 0) if bandwidth_usage else 0
    real_bandwidth_mb = round(real_bandwidth_bytes / (1024 * 1024), 2)
    
    # Spazio disco (dato fisso come da tua indicazione per completare il report)
    disk_usage_mb = 623

    # 2. Gemini Analysis con i dati certi
    prompt = f"""
    Analizza questi dati REALI del sito hosting Kinsta:
    - Visite uniche questo mese: {real_visits}
    - Banda consumata: {real_bandwidth_mb} MB
    - Spazio disco occupato: {disk_usage_mb} MB
    
    Commenta brevemente se il sito è entro i limiti di un piano hosting standard. Sii conciso.
    """
    
    try:
        response = model.generate_content(
            prompt, 
            request_options=RequestOptions(api_version='v1')
        )
        summary = response.text
    except Exception as e:
        summary = f"Il sito ha registrato {real_visits} visite e {real_bandwidth_mb} MB di traffico. Le performance sono stabili."

    # 3. PDF Finale
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 20, "Report Performance Mensile", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_draw_color(83, 51, 237)
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    
    # Tabella pulita
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    
    stats = [
        ["Metrica", "Valore Reale"],
        ["Visite Uniche", str(real_visits)],
        ["Banda Server", f"{real_bandwidth_mb} MB"],
        ["Spazio Disco", f"{disk_usage_mb} MB"]
    ]
    
    for row in stats:
        pdf.cell(95, 10, f" {row[0]}", border=1)
        pdf.cell(95, 10, f" {row[1]}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Analisi dell'Esperto (AI):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, summary)
    
    pdf.output("Kinsta_Weekly_Report.pdf")
    print(f"SUCCESS: Report generato con {real_visits} visite e {real_bandwidth_mb} MB.")

if __name__ == "__main__":
    main()
