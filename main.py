import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google.genai import Client
from fpdf import FPDF, XPos, YPos
from kinsta_utils import fetch_kinsta_metric, format_bytes_to_mb

# --- Configuration ---
REPORT_LANG = "en" 
MODEL_ID = "gemini-2.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = Client(api_key=GEMINI_API_KEY)

# Date ranges
PREV_RANGE = "Mar 22 - Mar 28"
CURR_RANGE = "Mar 29 - Apr 04"
DATES = ["2026-03-22", "2026-03-28", "2026-03-29", "2026-04-04"]
DAYS_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def main():
    # 1. DATA ACQUISITION
    # Visits
    total_vis_curr, data_vis_curr = fetch_kinsta_metric("visits", DATES[2], DATES[3])
    total_vis_prev, data_vis_prev = fetch_kinsta_metric("visits", DATES[0], DATES[1])

    # Bandwidth (Server + CDN) - We fetch daily datasets to plot them
    _, data_bw_srv = fetch_kinsta_metric("server-bandwidth", DATES[2], DATES[3])
    _, data_bw_cdn = fetch_kinsta_metric("cdn-bandwidth", DATES[2], DATES[3])
    
    # Calculate daily total bandwidth in MB
    daily_bw_mb = []
    for i in range(len(data_bw_srv)):
        srv = int(data_bw_srv[i]['value']) if i < len(data_bw_srv) else 0
        cdn = int(data_bw_cdn[i]['value']) if i < len(data_bw_cdn) else 0
        daily_bw_mb.append(format_bytes_to_mb(srv + cdn))
    
    total_bw_mb = sum(daily_bw_mb)

    # 2. VISUALIZATION: Two separate charts
    # Chart 1: Traffic Comparison
    plt.figure(figsize=(10, 4))
    curr_vals = [int(d['value']) for d in data_vis_curr] if data_vis_curr else [0]*7
    prev_vals = [int(d['value']) for d in data_vis_prev] if data_vis_prev else [0]*7
    plt.plot(DAYS_LABELS, curr_vals, color='#5333ed', marker='o', linewidth=2, label=f"Current ({total_vis_curr})")
    plt.plot(DAYS_LABELS, prev_vals, color='#a1a1a1', linestyle='--', marker='x', label=f"Previous ({total_vis_prev})")
    plt.fill_between(DAYS_LABELS, curr_vals, color='#5333ed', alpha=0.1)
    plt.title("Traffic Analysis (Visits)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("traffic_chart.png")
    plt.close()

    # Chart 2: Bandwidth Consumption (Daily MB)
    plt.figure(figsize=(10, 4))
    plt.bar(DAYS_LABELS, daily_bw_mb, color='#00c4b4', alpha=0.7, label='Daily MB (Server+CDN)')
    plt.title(f"Resource Usage: {total_bw_mb} MB Total Bandwidth")
    plt.ylabel("Megabytes (MB)")
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.savefig("bandwidth_chart.png")
    plt.close()

    # 3. AI ANALYSIS
    try:
        prompt = f"""
        Analyze this Kinsta report in {REPORT_LANG}:
        - Traffic: {total_vis_curr} visits (+{round(((total_vis_curr-total_vis_prev)/total_vis_prev)*100)}%)
        - Resources: {total_bw_mb} MB bandwidth used.
        - Daily visits: {curr_vals}
        - Daily bandwidth (MB): {daily_bw_mb}
        Correlate visits with resource usage and comment on efficiency. Max 4 sentences.
        """
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        summary = response.text
    except Exception:
        summary = f"Summary: {total_vis_curr} visits and {total_bw_mb} MB bandwidth consumed."

    # 4. PDF GENERATION
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 12, "Kinsta Executive Infrastructure Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Graphs Section
    pdf.image("traffic_chart.png", x=10, y=25, w=185)
    pdf.image("bandwidth_chart.png", x=10, y=105, w=185)
    
    # Table (Shifted down to accommodate two charts)
    pdf.set_y(185)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 8, " Day", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(75, 8, f" {PREV_RANGE} (Visits)", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True, align='C')
    pdf.cell(75, 8, f" {CURR_RANGE} (Visits)", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align='C')
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0)
    for i in range(7):
        pdf.cell(40, 6, f" {DAYS_LABELS[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(75, 6, f" {prev_vals[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(75, 6, f" {curr_vals[i]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # AI Executive Insights
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 8, "Executive Insights", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 5, summary)
    
    pdf.output("Kinsta_Infrastructure_Report.pdf")
    print("SUCCESS: Multi-chart report generated.")

if __name__ == "__main__":
    main()
