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
# Ripristinato il modello che usi con successo
MODEL_ID = "gemini-2.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = Client(api_key=GEMINI_API_KEY)

# --- Dynamic Date Logic (Auto-updating) ---
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

DAYS_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

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
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(0)
        
        self.cell(40, 10, " Day", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
        self.cell(75, 10, f" {PREV_RANGE} {unit}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True, align='C')
        self.cell(75, 10, f" {CURR_RANGE} {unit}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align='C')
        
        self.set_font("Helvetica", "", 10)
        for i in range(7):
            self.cell(40, 9, f" {DAYS_LABELS[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(75, 9, f" {prev_vals[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            self.cell(75, 9, f" {curr_vals[i]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

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
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def main():
    metrics = {
        "visits": {"title": "Site Visits", "unit": "(Visits)"},
        "bandwidth": {"title": "Server Bandwidth", "unit": "(MB)"},
        "cdn-bandwidth": {"title": "CDN Bandwidth", "unit": "(MB)"}
    }
    
    report_data = {}
    for key in metrics:
        _, data_curr = fetch_kinsta_metric(key, DATES[2], DATES[3])
        _, data_prev = fetch_kinsta_metric(key, DATES[0], DATES[1])
        
        # Inizializziamo le liste con 0 per tutti i 7 giorni
        curr_vals = [0] * 7
        prev_vals = [0] * 7
        
        # Mappa dei giorni per l'allineamento (0=Mon, 6=Sun)
        # Kinsta restituisce timestamp ISO, usiamo datetime per capire il giorno
        def fill_list_by_weekday(target_list, source_data, is_bw):
            for item in source_data:
                dt = datetime.fromisoformat(item['datetime'].replace('Z', '+00:00'))
                weekday = dt.weekday() # 0 è Lunedì
                val = float(item['value'])
                
                if weekday < 7:
                    if is_bw:
                        target_list[weekday] += format_bytes_to_mb(val)
                    else:
                        target_list[weekday] += int(val)

        fill_list_by_weekday(curr_vals, data_curr, "bandwidth" in key)
        fill_list_by_weekday(prev_vals, data_prev, "bandwidth" in key)
                
        report_data[key] = {"curr": curr_vals, "prev": prev_vals}

    pdf = KinstaReport()
    for key, info in metrics.items():
        chart_file = f"{key}_chart.png"
        generate_chart(DAYS_LABELS, report_data[key]["curr"], report_data[key]["prev"], f"{info['title']} Trends", "Units", chart_file, is_bar=("bandwidth" in key))
        pdf.add_metric_page(info["title"], chart_file, report_data[key]["prev"], report_data[key]["curr"], info["unit"])

    # AI Summary con modello 2.5-flash
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, "Executive Summary", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    try:
        summary_prompt = f"""
        Analyze Kinsta performance for {CURR_RANGE} vs {PREV_RANGE}.
        Current metrics: Visits {sum(report_data['visits']['curr'])}, Server BW {sum(report_data['bandwidth']['curr'])}MB, CDN BW {sum(report_data['cdn-bandwidth']['curr'])}MB.
        Previous metrics: Visits {sum(report_data['visits']['prev'])}, Server BW {sum(report_data['bandwidth']['prev'])}MB, CDN BW {sum(report_data['cdn-bandwidth']['prev'])}MB.
        Role: Web Strategist. Tone: Data-driven and concise. Language: {REPORT_LANG}. Max 4 sentences.
        """
        response = client.models.generate_content(model=MODEL_ID, contents=summary_prompt)
        summary = response.text
    except Exception as e:
        summary = f"Summary generation failed. Error details: {str(e)}"

    pdf.set_y(40)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 8, summary)
    
    report_filename = f"Kinsta_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    pdf.output(report_filename)
    print(f"Success: {report_filename} generated.")

if __name__ == "__main__":
    main()
