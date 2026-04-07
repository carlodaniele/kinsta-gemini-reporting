import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google.genai import Client
from fpdf import FPDF, XPos, YPos
from datetime import datetime, timedelta, timezone
from kinsta_utils import fetch_kinsta_metrics_combined, format_bytes_to_mb

# --- Configuration ---
REPORT_LANG = "en" 
MODEL_ID = "gemini-2.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = Client(api_key=GEMINI_API_KEY)

# --- Logic Date UTC (Blindata per Kinsta) ---
# Usiamo timezone.utc per far coincidere la "mezzanotte" con quella dei server Kinsta
today = datetime.now(timezone.utc)
curr_end_dt = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
curr_start_dt = curr_end_dt - timedelta(days=6)
prev_end_dt = curr_start_dt - timedelta(days=1)
prev_start_dt = prev_end_dt - timedelta(days=6)

DATES = [
    prev_start_dt.strftime("%Y-%m-%d"), 
    prev_end_dt.strftime("%Y-%m-%d"), 
    curr_start_dt.strftime("%Y-%m-%d"), 
    curr_end_dt.strftime("%Y-%m-%d")
]

# Numeri dei giorni per asse X e Tabella
CURR_DAYS_LABELS = [(curr_start_dt + timedelta(days=i)).strftime("%d") for i in range(7)]
PREV_DAYS_LABELS = [(prev_start_dt + timedelta(days=i)).strftime("%d") for i in range(7)]

class KinstaReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(150)
        self.cell(0, 10, f"Kinsta Analytics Report | Generated: {datetime.now().strftime('%Y-%m-%d')}", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_metric_page(self, title, chart_path, prev_vals, curr_vals, unit=""):
        self.add_page()
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(83, 51, 237)
        self.cell(0, 20, title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.image(chart_path, x=10, y=35, w=190)
        
        self.set_y(145)
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(240, 240, 240)
        
        # Header Tabella con numeri giorno
        self.cell(30, 10, " Day (Prev)", 1, 0, 'C', True)
        self.cell(65, 10, f"Value {unit}", 1, 0, 'C', True)
        self.cell(30, 10, " Day (Curr)", 1, 0, 'C', True)
        self.cell(65, 10, f"Value {unit}", 1, 1, 'C', True)
        
        self.set_font("Helvetica", "", 10)
        for i in range(7):
            self.cell(30, 9, f" {PREV_DAYS_LABELS[i]}", 1, 0, 'C')
            self.cell(65, 9, f" {prev_vals[i]}", 1, 0, 'C')
            self.cell(30, 9, f" {CURR_DAYS_LABELS[i]}", 1, 0, 'C')
            self.cell(65, 9, f" {curr_vals[i]}", 1, 1, 'C')

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
    # Gruppi di metriche: "total_bandwidth" somma 3 endpoint diversi
    metrics_groups = {
        "visits": {"endpoints": ["visits"], "title": "Site Visits", "unit": ""},
        "total_bandwidth": {
            "endpoints": ["bandwidth", "cdn-bandwidth", "edge-bandwidth"], 
            "title": "Total Bandwidth", 
            "unit": "(MB)"
        }
    }
    
    report_data = {}
    for key, info in metrics_groups.items():
        # Otteniamo i dizionari mappati per data
        map_curr = fetch_kinsta_metrics_combined(info['endpoints'], DATES[2], DATES[3])
        map_prev = fetch_kinsta_metrics_combined(info['endpoints'], DATES[0], DATES[1])
        
        curr_vals = []
        prev_vals = []
        
        for i in range(7):
            # Calcoliamo la stringa data esatta per cercare nel dizionario
            d_curr = (curr_start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            d_prev = (prev_start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            
            val_c = map_curr.get(d_curr, 0)
            val_p = map_prev.get(d_prev, 0)
            
            if "bandwidth" in key:
                curr_vals.append(format_bytes_to_mb(val_c))
                prev_vals.append(format_bytes_to_mb(val_p))
            else:
                curr_vals.append(int(val_c))
                prev_vals.append(int(val_p))
                
        report_data[key] = {"curr": curr_vals, "prev": prev_vals}

    # Creazione PDF
    pdf = KinstaReport()
    for key, info in metrics_groups.items():
        chart_file = f"{key}_chart.png"
        generate_chart(CURR_DAYS_LABELS, report_data[key]["curr"], report_data[key]["prev"], 
                       f"{info['title']} Trends", "Units", chart_file, is_bar=("bandwidth" in key))
        pdf.add_metric_page(info["title"], chart_file, report_data[key]["prev"], report_data[key]["curr"], info["unit"])

    # AI Summary
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, "Executive Summary", align="C", ln=1)
    
    try:
        summary_prompt = f"Analyze performance. Current: Visits {sum(report_data['visits']['curr'])}, BW {sum(report_data['total_bandwidth']['curr'])}MB. Language: {REPORT_LANG}. Max 3 sentences."
        response = client.models.generate_content(model=MODEL_ID, contents=summary_prompt)
        summary = response.text
    except:
        summary = "Summary unavailable."

    pdf.set_y(40)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 8, summary)
    
    report_filename = f"Kinsta_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    pdf.output(report_filename)
    print(f"Success: {report_filename}")

if __name__ == "__main__":
    main()
