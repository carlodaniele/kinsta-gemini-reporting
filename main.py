import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time
from datetime import datetime
from google.genai import Client
from fpdf import FPDF, XPos, YPos

# --- Configuration & Localization ---
# Set your preferred language here: 'en' for English, 'it' for Italian, etc.
REPORT_LANG = "en" 

# Localized strings for PDF and Charts
LOCALES = {
    "en": {
        "title": "Kinsta Executive Precision Report",
        "chart_title": "Weekly Visits Comparison (7 vs 7)",
        "legend_curr": "Current Week",
        "legend_prev": "Previous Week",
        "col_day": " Day",
        "col_prev": " Previous Week",
        "col_curr": " Current Week",
        "insights": "Executive Insights",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    },
    "it": {
        "title": "Report di Precisione Kinsta",
        "chart_title": "Confronto Visite Settimanali (7 vs 7)",
        "legend_curr": "Settimana Attuale",
        "legend_prev": "Settimana Precedente",
        "col_day": " Giorno",
        "col_prev": " Settimana Precedente",
        "col_curr": " Settimana Attuale",
        "insights": "Analisi Strategica",
        "days": ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    }
}

# Select translation based on REPORT_LANG (fallback to English)
t = LOCALES.get(REPORT_LANG, LOCALES["en"])

# API Credentials from Environment Variables
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini 2.0 Flash Client
client = Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-2.0-flash"

class KinstaStrictAnalyst:
    """Handles API requests to Kinsta Analytics endpoints."""
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics/visits"

    def fetch_7_days(self, start, end):
        """Fetches a 7-day dataset for a specific date range."""
        params = {
            "company_id": KINSTA_COMPANY_ID,
            "from": f"{start}T00:00:00.000Z",
            "to": f"{end}T23:59:59.000Z",
            "time_span": "30_days"
        }
        res = requests.get(self.base_url, headers=self.headers, params=params)
        if res.status_code == 200:
            try:
                # Target the exact Mintlify JSON structure: analytics -> analytics_response -> data
                data = res.json()['analytics']['analytics_response']['data'][0]
                dataset = data.get('dataset', [])[:7]
                return data.get('total', 0), dataset
            except: return 0, []
        return 0, []

def main():
    analyst = KinstaStrictAnalyst()
    
    # 1. Fetching Data for Comparison (Current week vs Previous week)
    total_curr, data_curr = analyst.fetch_7_days("2026-03-29", "2026-04-04")
    total_prev, data_prev = analyst.fetch_7_days("2026-03-22", "2026-03-28")

    # 2. Generating Comparison Chart
    plt.figure(figsize=(10, 5))
    val_curr = [int(d['value']) for d in data_curr] if data_curr else [0]*7
    val_prev = [int(d['value']) for d in data_prev] if data_prev else [0]*7
    
    plt.plot(t["days"], val_curr, color='#5333ed', marker='o', linewidth=2, label=t["legend_curr"])
    plt.plot(t["days"], val_prev, color='#a1a1a1', linestyle='--', marker='x', label=t["legend_prev"])
    plt.fill_between(t["days"], val_curr, color='#5333ed', alpha=0.1)
    plt.title(t["chart_title"])
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("comparison_chart.png")

    # 3. Dynamic AI Analysis with Language Enforcement
    try:
        # We instruct Gemini to respond in the specific language defined in REPORT_LANG
        prompt = f"""
        Act as a Senior Web Analyst. Analyze this Kinsta traffic comparison and write your response ONLY in: {REPORT_LANG}.
        - Current week: {total_curr} visits (Daily: {val_curr})
        - Previous week: {total_prev} visits (Daily: {val_prev})
        
        Focus on growth percentage, daily peaks, and strategic impact. Max 4 sentences.
        """
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        summary = response.text
    except Exception as e:
        summary = f"Summary: {total_curr} vs {total_prev}. AI analysis currently unavailable."

    # 4. Building the PDF Report
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, t["title"], align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Add Chart Image
    pdf.image("comparison_chart.png", x=10, y=40, w=185)
    
    # Table Header
    pdf.set_y(135)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 8, t["col_day"], 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(65, 8, t["col_prev"], 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(65, 8, t["col_curr"], 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    
    # Table Rows
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0)
    for i in range(7):
        pdf.cell(60, 7, f" {t['days'][i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(65, 7, f" {val_prev[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(65, 7, f" {val_curr[i]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # AI Executive Summary Section
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, t["insights"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 7, summary)
    
    # Output the final file
    pdf.output("Kinsta_Executive_Report.pdf")
    print(f"SUCCESS: Report generated in '{REPORT_LANG}' language.")

if __name__ == "__main__":
    main()
