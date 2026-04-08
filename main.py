import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google.genai import Client
from fpdf import FPDF, XPos, YPos
from datetime import datetime, timedelta
from kinsta_utils import fetch_kinsta_metric, format_bytes_to_mb

# --- Configuration ---
REPORT_LANG = "en" 
# Nota: Assicurati che l'ID del modello sia corretto (es. gemini-2.0-flash)
MODEL_ID = "gemini-2.0-flash" 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = Client(api_key=GEMINI_API_KEY)

# --- Dynamic Date Logic ---
today = datetime.now()
curr_end_dt = today - timedelta(days=1)
curr_start_dt = today - timedelta(days=7)
prev_end_dt = today - timedelta(days=8)
prev_start_dt = today - timedelta(days=14)

CURR_RANGE = f"{curr_start_dt.strftime('%b %d')} - {curr_end_dt.strftime('%b %d')}"
PREV_RANGE = f"{prev_start_dt.strftime('%b %d')} - {prev_end_dt.strftime('%b %d')}"

DATES = [
    prev_start_dt.strftime("%Y-%m-%d"), 
    prev_end_dt.strftime("%Y-%m-%d"), 
    curr_start_dt.strftime("%Y-%m-%d"), 
    curr_end_dt.strftime("%Y-%m-%d")
]

CURR_DAYS = [(curr_start_dt + timedelta(days=i)).strftime("%d") for i in range(7)]
PREV_DAYS = [(prev_start_dt + timedelta(days=i)).strftime("%d") for i in range(7)]

class KinstaReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(150)
        self.cell(0, 10, f"Kinsta Analytics Report | Generated: {datetime.now().strftime('%Y-%m-%d')}", 
                  align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_metric_page(self, title, chart_path, prev_vals, curr_vals, unit=""):
        self.add_page()
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(83, 51, 237)
        self.cell(0, 20, title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.image(chart_path, x=10, y=35, w=190)
        
        self.set_y(145)
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(240, 240, 240)
        
        # Header Tabella - Fix Deprecation Warnings
        self.cell(30, 10, " Day (Prev)", border=1, align='C', fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(65, 10, f"Value {unit}", border=1, align='C', fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(30, 10, " Day (Curr)", border=1, align='C', fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(65, 10, f"Value {unit}", border=1, align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font("Helvetica", "", 10)
        for i in range(7):
            self.cell(30, 9, f" {PREV_DAYS[i]}", border=1, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(65, 9, f" {prev_vals[i]}", border=1, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(30, 9, f" {CURR_DAYS[i]}", border=1, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(65, 9, f" {curr_vals[i]}", border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

def generate_chart(labels, curr, prev, title, ylabel, filename, is_bar=False):
    plt.figure(figsize=(10, 5))
    if is_bar:
        plt.bar(labels, curr, color='#00c4b4', alpha=0.7, label='Current Period')
    else:
        plt.plot(labels, curr, color='#5333ed', marker='o', linewidth=2, label='Current')
        plt.plot(labels, prev, color='#a1a1a1', linestyle='--', marker='x', label='Previous')
        plt.fill_between(labels, curr, color='#5333ed', alpha=0.1)
    
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel("Day of Month")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def main():
    metrics = {
        "visits": {"title": "Site Visits", "unit": ""},
        "bandwidth": {"title": "Server Bandwidth", "unit": "(MB)"},
        "cdn-bandwidth": {"title": "CDN Bandwidth", "unit": "(MB)"}
    }
    
    report_data = {}
    for key in metrics:
        _, data_curr = fetch_kinsta_metric(key, DATES[2], DATES[3])
        _, data_prev = fetch_kinsta_metric(key, DATES[0], DATES[1])
        
        curr_vals = []
        prev_vals = []
        for i in range(7):
            c = float(data_curr[i]['value']) if i < len(data_curr) else 0
            p = float(data_prev[i]['value']) if i < len(data_prev) else 0
            
            if "bandwidth" in key:
                curr_vals.append(format_bytes_to_mb(c))
                prev_vals.append(format_bytes_to_mb(p))
            else:
                curr_vals.append(int(c))
                prev_vals.append(int(p))
                
        report_data[key] = {"curr": curr_vals, "prev": prev_vals}

    pdf = KinstaReport()
    for key, info in metrics.items():
        chart_file = f"{key}_chart.png"
        generate_chart(CURR_DAYS, report_data[key]["curr"], report_data[key]["prev"], f"{info['title']} Trends", "Units", chart_file, is_bar=("bandwidth" in key))
        pdf.add_metric_page(info["title"], chart_file, report_data[key]["prev"], report_data[key]["curr"], info["unit"])

    # --- Executive Summary con Prompt Corretto ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, "Executive Summary", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Calcolo totali per il prompt
    curr_visits = sum(report_data['visits']['curr'])
    prev_visits = sum(report_data['visits']['prev'])
    curr_bw = sum(report_data['bandwidth']['curr'])
    prev_bw = sum(report_data['bandwidth']['prev'])

    try:
        summary_prompt = (
            f"Analyze Kinsta performance. "
            f"Current Period ({CURR_RANGE}): {curr_visits} visits, {curr_bw:.2f}MB server bandwidth. "
            f"Previous Period ({PREV_RANGE}): {prev_visits} visits, {prev_bw:.2f}MB server bandwidth. "
            f"Compare these two periods. Language: {REPORT_LANG}. Max 4 sentences."
        )
        response = client.models.generate_content(model=MODEL_ID, contents=summary_prompt)
        summary = response.text
    except Exception as e:
        summary = f"Analytical insights unavailable. Error: {str(e)}"

    pdf.set_y(40)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 8, summary)
    
    report_filename = f"Kinsta_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    pdf.output(report_filename)
    print(f"Report generated: {report_filename}")

if __name__ == "__main__":
    main()
