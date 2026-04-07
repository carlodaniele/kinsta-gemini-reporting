import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google.genai import Client
from fpdf import FPDF, XPos, YPos
from kinsta_utils import fetch_kinsta_metric, format_bytes_to_mb

# --- Configuration & Localization ---
REPORT_LANG = "en" 
MODEL_ID = "gemini-2.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = Client(api_key=GEMINI_API_KEY)

# Exact date ranges for the current and previous week
PREV_RANGE = "Mar 22 - Mar 28"
CURR_RANGE = "Mar 29 - Apr 04"
DATES = ["2026-03-22", "2026-03-28", "2026-03-29", "2026-04-04"]
DAYS_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def main():
    # 1. DATA ACQUISITION
    # Fetching Visits for comparison
    total_vis_curr, data_vis_curr = fetch_kinsta_metric("visits", DATES[2], DATES[3])
    total_vis_prev, data_vis_prev = fetch_kinsta_metric("visits", DATES[0], DATES[1])

    # Fetching Bandwidth (Server) 
    _, data_bw_srv = fetch_kinsta_metric("bandwidth", DATES[2], DATES[3])
    
    # Ensuring 7 data points to avoid Matplotlib broadcast errors
    curr_vis_vals = []
    prev_vis_vals = []
    daily_bw_mb = []

    for i in range(7):
        # Align Visits
        curr_vis_vals.append(int(data_vis_curr[i]['value']) if i < len(data_vis_curr) else 0)
        prev_vis_vals.append(int(data_vis_prev[i]['value']) if i < len(data_vis_prev) else 0)
        # Align Bandwidth (converting to MB)
        daily_bw_mb.append(format_bytes_to_mb(data_bw_srv[i]['value']) if i < len(data_bw_srv) else 0)
    
    total_bw_mb = sum(daily_bw_mb)

    # 2. VISUALIZATION: Dual Chart Setup
    # Chart 1: Traffic Analysis
    plt.figure(figsize=(10, 4))
    plt.plot(DAYS_LABELS, curr_vis_vals, color='#5333ed', marker='o', linewidth=2, label=f"Current ({total_vis_curr})")
    plt.plot(DAYS_LABELS, prev_vis_vals, color='#a1a1a1', linestyle='--', marker='x', label=f"Previous ({total_vis_prev})")
    plt.fill_between(DAYS_LABELS, curr_vis_vals, color='#5333ed', alpha=0.1)
    plt.title(f"Traffic Analysis (Visits)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("traffic_chart.png")
    plt.close()

    # Chart 2: Bandwidth Consumption
    plt.figure(figsize=(10, 4))
    plt.bar(DAYS_LABELS, daily_bw_mb, color='#00c4b4', alpha=0.7, label='Daily MB')
    plt.title(f"Bandwidth Usage: {total_bw_mb} MB Total")
    plt.ylabel("Megabytes (MB)")
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.savefig("bandwidth_chart.png")
    plt.close()

    # 3. AI ANALYSIS (Gemini 2.5 Flash)
    try:
        prompt = f"""
        Act as a Senior Web Analyst. Analyze this Kinsta report in {REPORT_LANG}:
        - Traffic Growth: {total_vis_curr} vs {total_vis_prev} visits.
        - Infrastructure: {total_bw_mb} MB bandwidth consumed.
        - Daily patterns: Visits {curr_vis_vals}, Bandwidth {daily_bw_mb}.
        Correlate traffic peaks with resource usage. Max 4 professional sentences.
        """
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        summary = response.text
    except Exception:
        summary = f"Visits: {total_vis_curr}. Bandwidth: {total_bw_mb} MB. AI insights unavailable."

    # 4. PDF COMPOSITION
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 12, "Kinsta Executive Infrastructure Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Place Charts
    pdf.image("traffic_chart.png", x=10, y=25, w=185)
    pdf.image("bandwidth_chart.png", x=10, y=105, w=185)
    
    # Comparison Table
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
        pdf.cell(75, 6, f" {prev_vis_vals[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(75, 6, f" {curr_vis_vals[i]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # Executive Summary Section
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 8, "Executive Insights", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 5, summary)
    
    pdf.output("Kinsta_Infrastructure_Report.pdf")
    print("SUCCESS: Report generated with dual-metric analysis.")

if __name__ == "__main__":
    main()
