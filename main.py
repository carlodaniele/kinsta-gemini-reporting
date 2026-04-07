import os
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google.genai import Client
from fpdf import FPDF, XPos, YPos

# --- Configuration & Localization ---
# Reporting language set directly in the code
REPORT_LANG = "en" 

# Model version enforced as per instructions
MODEL_ID = "gemini-2.5-flash" 

# Localization dictionary for PDF elements
LOCALES = {
    "en": {
        "title": "Kinsta Executive Precision Report",
        "chart_title": "Weekly Visits Comparison (7 vs 7)",
        "legend_curr": "Current Week",
        "legend_prev": "Previous Week",
        "col_day": " Day",
        "insights": "Executive Insights",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    }
}

t = LOCALES.get(REPORT_LANG, LOCALES["en"])

# API Credentials from Environment
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini 2.5 Flash Client
client = Client(api_key=GEMINI_API_KEY)

class KinstaStrictAnalyst:
    """Handles data fetching from Kinsta Analytics API."""
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics/visits"

    def fetch_7_days(self, start, end):
        """Retrieves analytics data for a specific 7-day range."""
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
    
    # Define specific date ranges for clarity in the report
    prev_range = "Mar 22 - Mar 28"
    curr_range = "Mar 29 - Apr 04"
    
    # Fetching data for both periods
    total_curr, data_curr = analyst.fetch_7_days("2026-03-29", "2026-04-04")
    total_prev, data_prev = analyst.fetch_7_days("2026-03-22", "2026-03-28")

    # 1. Visualization: Generate comparison chart
    plt.figure(figsize=(10, 5))
    val_curr = [int(d['value']) for d in data_curr] if data_curr else [0]*7
    val_prev = [int(d['value']) for d in data_prev] if data_prev else [0]*7
    
    plt.plot(t["days"], val_curr, color='#5333ed', marker='o', linewidth=2, label=f"{t['legend_curr']} ({curr_range})")
    plt.plot(t["days"], val_prev, color='#a1a1a1', linestyle='--', marker='x', label=f"{t['legend_prev']} ({prev_range})")
    plt.fill_between(t["days"], val_curr, color='#5333ed', alpha=0.1)
    plt.title(t["chart_title"])
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("comparison_chart.png")

    # 2. AI Analysis: Using Gemini 2.5 Flash
    try:
        prompt = f"""
        Analyze this Kinsta traffic comparison and write in {REPORT_LANG}:
        - Current week ({curr_range}): {total_curr} visits
        - Previous week ({prev_range}): {total_prev} visits
        - Daily values: {val_curr}
        
        Provide a professional executive summary including growth % and peaks. Max 4 sentences.
        """
        # Call the specific gemini-2.5-flash model
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        summary = response.text
    except Exception as e:
        summary = f"Analysis for {curr_range} vs {prev_range} unavailable. Error: {str(e)}"

    # 3. Report Generation: PDF with dynamic date headers
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, t["title"], align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Insert Chart
    pdf.image("comparison_chart.png", x=10, y=35, w=185)
    
    # Table with specific date range headers
    pdf.set_y(130)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 10, t["col_day"], 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(75, 10, f" {prev_range} ({t['legend_prev']})", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True, align='C')
    pdf.cell(75, 10, f" {curr_range} ({t['legend_curr']})", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align='C')
    
    # Populate rows
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0)
    for i in range(7):
        pdf.cell(40, 8, f" {t['days'][i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(75, 8, f" {val_prev[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(75, 8, f" {val_curr[i]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # AI Insights Section
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, t["insights"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 7, summary)
    
    # Final Output
    pdf.output("Kinsta_Executive_Report.pdf")
    print(f"SUCCESS: Report generated using {MODEL_ID}.")

if __name__ == "__main__":
    main()
