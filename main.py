import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google.genai import Client
from fpdf import FPDF, XPos, YPos
# Importing our new custom helpers
from kinsta_utils import fetch_kinsta_metric, format_bytes_to_mb

# --- Configuration ---
REPORT_LANG = "en" 
MODEL_ID = "gemini-2.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = Client(api_key=GEMINI_API_KEY)

# Date ranges for the report [cite: 4]
PREV_RANGE = "Mar 22 - Mar 28"
CURR_RANGE = "Mar 29 - Apr 04"
DATES = ["2026-03-22", "2026-03-28", "2026-03-29", "2026-04-04"]

def main():
    # 1. DATA ACQUISITION
    # Fetching Visits [cite: 4, 11]
    total_vis_curr, data_vis_curr = fetch_kinsta_metric("visits", DATES[2], DATES[3])
    total_vis_prev, data_vis_prev = fetch_kinsta_metric("visits", DATES[0], DATES[1])

    # Fetching Bandwidth (Server + CDN)
    bw_srv_raw, _ = fetch_kinsta_metric("server-bandwidth", DATES[2], DATES[3])
    bw_cdn_raw, _ = fetch_kinsta_metric("cdn-bandwidth", DATES[2], DATES[3])
    total_bw_mb = format_bytes_to_mb(bw_srv_raw + bw_cdn_raw)

    # 2. VISUALIZATION
    plt.figure(figsize=(10, 5))
    days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    curr_vals = [int(d['value']) for d in data_vis_curr] if data_vis_curr else [0]*7
    prev_vals = [int(d['value']) for d in data_vis_prev] if data_vis_prev else [0]*7

    plt.plot(days_labels, curr_vals, color='#5333ed', marker='o', linewidth=2, label=f"Current Week ({total_vis_curr})")
    plt.plot(days_labels, prev_vals, color='#a1a1a1', linestyle='--', marker='x', label=f"Previous Week ({total_vis_prev})")
    plt.fill_between(days_labels, curr_vals, color='#5333ed', alpha=0.1)
    plt.title(f"Traffic Analysis: {total_vis_curr} Total Visits")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("report_chart.png")

    # 3. AI MULTI-METRIC ANALYSIS 
    try:
        prompt = f"""
        Analyze this Kinsta hosting report:
        - Visits: {total_vis_curr} (Current) vs {total_vis_prev} (Previous)
        - Bandwidth Usage: {total_bw_mb} MB (Total Server + CDN)
        - Traffic Peaks: {curr_vals}
        
        Provide a professional summary in {REPORT_LANG}. 
        Correlate traffic growth with bandwidth consumption. Max 4 sentences.
        """
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        summary = response.text
    except Exception as e:
        summary = f"Analysis unavailable. Metrics: {total_vis_curr} visits, {total_bw_mb} MB bandwidth."

    # 4. PDF GENERATION
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 15, "Kinsta Multi-Metric Executive Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.image("report_chart.png", x=10, y=35, w=185)
    
    # Combined Table [cite: 4]
    pdf.set_y(130)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 10, " Day", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
    pdf.cell(75, 10, f" {PREV_RANGE} (Visits)", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True, align='C')
    pdf.cell(75, 10, f" {CURR_RANGE} (Visits)", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align='C')
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0)
    for i in range(7):
        pdf.cell(40, 8, f" {days_labels[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(75, 8, f" {prev_vals[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(75, 8, f" {curr_vals[i]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # Bandwidth Info Box
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, f"Total Bandwidth Consumed (Current Week): {total_bw_mb} MB", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # AI Insights
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(83, 51, 237)
    pdf.cell(0, 10, "Executive Insights", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 7, summary)
    
    pdf.output("Kinsta_Full_Report.pdf")
    print(f"SUCCESS: Comprehensive report generated.")

if __name__ == "__main__":
    main()
