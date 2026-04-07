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

class KinstaReport(FPDF):
    def add_metric_page(self, title, chart_path, prev_vals, curr_vals, unit=""):
        """Creates a standardized page for a single metric."""
        self.add_page()
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(83, 51, 237)
        self.cell(0, 15, title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Upper: Chart
        self.image(chart_path, x=10, y=30, w=190)

        # Lower: Table
        self.set_y(140)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(0)

        # Header
        self.cell(40, 10, " Day", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
        self.cell(75, 10, f" {PREV_RANGE} {unit}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True, align='C')
        self.cell(75, 10, f" {CURR_RANGE} {unit}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align='C')

        # Data
        self.set_font("Helvetica", "", 11)
        for i in range(7):
            self.cell(40, 10, f" {DAYS_LABELS[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(75, 10, f" {prev_vals[i]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            self.cell(75, 10, f" {curr_vals[i]}", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

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
    plt.savefig(filename)
    plt.close()

def main():
    # 1. DATA ACQUISITION
    metrics = {
        "visits": {"title": "Site Visits", "unit": "(Visits)"},
        "bandwidth": {"title": "Server Bandwidth", "unit": "(MB)"},
        "cdn-bandwidth": {"title": "CDN Bandwidth", "unit": "(MB)"}
    }

    report_data = {}
    for key in metrics:
        total_curr, data_curr = fetch_kinsta_metric(key, DATES[2], DATES[3])
        total_prev, data_prev = fetch_kinsta_metric(key, DATES[0], DATES[1])

        # Prepare lists
        curr_vals = []
        prev_vals = []
        for i in range(7):
            c = data_curr[i]['value'] if i < len(data_curr) else 0
            p = data_prev[i]['value'] if i < len(data_prev) else 0

            if "bandwidth" in key:
                curr_vals.append(format_bytes_to_mb(c))
                prev_vals.append(format_bytes_to_mb(p))
            else:
                curr_vals.append(int(c))
                prev_vals.append(int(p))

        report_data[key] = {"curr": curr_vals, "prev": prev_vals, "total_curr": total_curr}

    # 2. GENERATE CHARTS & PDF
    pdf = KinstaReport()

    for key, info in metrics.items():
        chart_file = f"{key}_chart.png"
        generate_chart(
            DAYS_LABELS, 
            report_data[key]["curr"], 
            report_data[key]["prev"], 
            f"{info['title']} Trends", 
            "Units", 
            chart_file,
            is_bar=("bandwidth" in key)
        )
        pdf.add_metric_page(info["title"], chart_file, report_data[key]["prev"], report_data[key]["curr"], info["unit"])

    # 3. FINAL AI SUMMARY PAGE
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, "Executive Summary", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    try:
        prompt = f"Analyze this Kinsta report: Visits {sum(report_data['visits']['curr'])}, Server BW {sum(report_data['bandwidth']['curr'])} MB, CDN BW {sum(report_data['cdn-bandwidth']['curr'])} MB. Language: {REPORT_LANG}. Max 4 sentences."

        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        summary = response.text

    except:
        summary = "Analytical insights unavailable."

    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 8, summary)

    pdf.output("Kinsta_Final_Report_Paginated.pdf")

if __name__ == "__main__":
    main()
