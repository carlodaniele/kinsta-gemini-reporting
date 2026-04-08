import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google.genai import Client
from fpdf import FPDF, XPos, YPos
from datetime import datetime, timedelta
from kinsta_utils import fetch_kinsta_metric, format_bytes_to_mb, fetch_site_name

# --- Configuration ---
REPORT_LANG = "en" 
MODEL_ID = "gemini-2.5-flash" 
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

# Etichette per le tabelle: "01 Mon", "02 Tue"...
CURR_DAYS_LABELS = [(curr_start_dt + timedelta(days=i)).strftime("%d %a") for i in range(7)]
PREV_DAYS_LABELS = [(prev_start_dt + timedelta(days=i)).strftime("%d %a") for i in range(7)]
# Etichette per i grafici (solo numero per non affollare l'asse X)
X_AXIS_LABELS = [(curr_start_dt + timedelta(days=i)).strftime("%d") for i in range(7)]

class KinstaReport(FPDF):
    def __init__(self, site_name="Unknown Site"):
        super().__init__()
        self.site_name = site_name

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(150)
        # Nome del sito a sinistra
        self.cell(100, 10, f"Site: {self.site_name}", align="L")
        # Generato il... a destra
        self.cell(0, 10, f"Kinsta Analytics Report | Generated: {datetime.now().strftime('%Y-%m-%d')}", 
                  align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_metric_page(self, title, chart_path, prev_vals, curr_vals, unit=""):
        self.add_page()
        # Titolo Pagina
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(83, 51, 237)
        self.cell(0, 15, title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Sottotitolo con date
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(120)
        self.cell(0, 5, f"Comparison: {CURR_RANGE} vs {PREV_RANGE}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Spazio per il grafico
        self.image(chart_path, x=10, y=42, w=190)
        
        # Tabella dati
        self.set_y(150)
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(245, 245, 255) # Celeste tenue per header tabella
        self.set_text_color(83, 51, 237)
        
        # Header Tabella (Larghezze regolate per far stare il nome del giorno)
        col1, col2 = 35, 60
        self.cell(col1, 10, " Day (Prev)", border=1, align='C', fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(col2, 10, f"Value {unit}", border=1, align='C', fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(col1, 10, " Day (Curr)", border=1, align='C', fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(col2, 10, f"Value {unit}", border=1, align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50)
        for i in range(7):
            # Zebra striping (righe alternate)
            fill = (i % 2 == 0)
            if fill: self.set_fill_color(250, 250, 250)
            else: self.set_fill_color(255, 255, 255)
            
            self.cell(col1, 9, f" {PREV_DAYS_LABELS[i]}", border=1, align='C', fill=fill, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(col2, 9, f" {prev_vals[i]}", border=1, align='C', fill=fill, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(col1, 9, f" {CURR_DAYS_LABELS[i]}", border=1, align='C', fill=fill, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(col2, 9, f" {curr_vals[i]}", border=1, align='C', fill=fill, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

def generate_chart(labels, curr, prev, title, ylabel, filename, is_bar=False):
    plt.figure(figsize=(10, 5), dpi=100)
    ax = plt.gca()
    
    # Rimuoviamo i bordi superiore e destro per un look pulito
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['bottom'].set_color('#dddddd')

    if is_bar:
        # Grafico a barre per Bandwidth
        bars = plt.bar(labels, curr, color='#00c4b4', alpha=0.6, label='Current Period', width=0.6)
        # Aggiunta etichette sopra le barre
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.02, f'{height}', ha='center', va='bottom', fontsize=8, color='#00a194')
    else:
        # Grafico a linee per Visits
        plt.plot(labels, curr, color='#5333ed', marker='o', markersize=6, linewidth=3, label='Current', zorder=3)
        plt.plot(labels, prev, color='#a1a1a1', linestyle='--', marker='x', markersize=5, linewidth=1.5, label='Previous', alpha=0.6)
        # Riempimento sfumato sotto la linea
        plt.fill_between(labels, curr, color='#5333ed', alpha=0.1)
    
    plt.title(title, fontsize=14, pad=20, color='#333333', fontweight='bold')
    plt.ylabel(ylabel, color='#666666')
    plt.xlabel("Day of Month", color='#666666')
    plt.legend(frameon=False, loc='upper right')
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def main():
    # Recupero Nome Sito tramite API
    site_display_name = fetch_site_name()

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

    # Creazione PDF passando il nome del sito
    pdf = KinstaReport(site_name=site_display_name)
    
    for key, info in metrics.items():
        chart_file = f"{key}_chart.png"
        generate_chart(X_AXIS_LABELS, report_data[key]["curr"], report_data[key]["prev"], 
                       f"{info['title']} Trends", "Units", chart_file, is_bar=("bandwidth" in key))
        pdf.add_metric_page(info["title"], chart_file, report_data[key]["prev"], report_data[key]["curr"], info["unit"])

    # Executive Summary
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, "Executive Summary", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    curr_visits = sum(report_data['visits']['curr'])
    prev_visits = sum(report_data['visits']['prev'])
    curr_bw = sum(report_data['bandwidth']['curr'])
    prev_bw = sum(report_data['bandwidth']['prev'])

    try:
        summary_prompt = (
            f"Analyze Kinsta performance for site {site_display_name}. "
            f"Current Period ({CURR_RANGE}): {curr_visits} visits, {curr_bw:.2f}MB server bandwidth. "
            f"Previous Period ({PREV_RANGE}): {prev_visits} visits, {prev_bw:.2f}MB server bandwidth. "
            f"Compare these periods and identify trends. Language: {REPORT_LANG}. Max 4 sentences."
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
