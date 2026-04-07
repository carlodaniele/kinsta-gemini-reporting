import os
import requests
import matplotlib.pyplot as plt
from google import generativeai as genai
from fpdf import FPDF
from datetime import datetime

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
KINSTA_COMPANY_ID = os.getenv("KINSTA_COMPANY_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaReportGenerator:
    def __init__(self):
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics"
        self.headers = {
            "Authorization": f"Bearer {KINSTA_API_KEY}",
            "Accept": "application/json"
        }
        # Fixed parameters based on API validation error
        self.params = {
            "time_span": "7_days", # Correct enum value
            "company_id": KINSTA_COMPANY_ID, # Required parameter
            "timezone": "UTC"
        }

    def get_analytics_data(self, endpoint):
        """Fetch data with precise parameter handling."""
        url = f"{self.base_url}/{endpoint}"
        print(f"Requesting: {endpoint}...")
        response = requests.get(url, headers=self.headers, params=self.params)
        
        if response.status_code != 200:
            print(f"DEBUG - API Error for {endpoint}: {response.text}")
        
        response.raise_for_status()
        return response.json()

    def create_visuals(self, visits_data):
        """Generate trend chart from Kinsta visits data."""
        stats = visits_data.get('data', [])
        if not stats:
            print("No data points available to plot.")
            return False

        # Extraction with safety check
        dates = [item.get('datetime', '')[:10] for item in stats]
        values = [int(item.get('value', 0)) for item in stats]

        plt.figure(figsize=(10, 5))
        plt.plot(dates, values, marker='o', color='#5333ed', linewidth=2)
        plt.fill_between(dates, values, color='#5333ed', alpha=0.1)
        plt.title("Weekly Traffic Analysis (Unique Visits)", fontsize=14)
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("visits_chart.png")
        return True

    def generate_ai_analysis(self, raw_data):
        """Send raw JSON to Gemini for a human-readable summary."""
        prompt = (
            f"Analyze these Kinsta analytics: {raw_data}. "
            "Write a very brief professional summary for the client. "
            "Explain if the site performance is healthy. Max 100 words."
        )
        response = model.generate_content(prompt)
        return response.text

    def build_pdf(self, ai_text):
        """Create the final PDF document."""
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(83, 51, 237)
        pdf.cell(0, 15, "Kinsta Site Performance Report", ln=True, align="C")
        
        # Chart
        if os.path.exists("visits_chart.png"):
            pdf.image("visits_chart.png", x=10, y=30, w=190)
        
        # Summary
        pdf.set_y(135)
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "Executive Summary (AI Analysis):", ln=True)
        
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 7, ai_text)
        
        pdf.output("Kinsta_Weekly_Report.pdf")

def main():
    try:
        report = KinstaReportGenerator()
        
        # Collecting metrics as per documentation
        data = {
            "visits": report.get_analytics_data("visits"),
            "bandwidth": report.get_analytics_data("server-bandwidth"),
            "cdn": report.get_analytics_data("cdn-bandwidth"),
            "disk": report.get_analytics_data("disk-usage")
        }

        print("Generating visual assets...")
        report.create_visuals(data['visits'])

        print("Processing analysis with Gemini AI...")
        summary = report.generate_ai_analysis(data)

        print("Finalizing PDF...")
        report.build_pdf(summary)
        print("Success! Report is ready.")

    except Exception as e:
        print(f"Process failed: {e}")

if __name__ == "__main__":
    main()
