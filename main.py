import os
import requests
import matplotlib.pyplot as plt
from google import generativeai as genai
from fpdf import FPDF
from datetime import datetime

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaReportGenerator:
    def __init__(self):
        # Base URL for environments analytics
        self.base_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics"
        self.headers = {
            "Authorization": f"Bearer {KINSTA_API_KEY}",
            "Accept": "application/json"
        }
        # Added timezone as it's often required by Kinsta Analytics
        self.params = {
            "time_span": "last_7_days",
            "timezone": "UTC" 
        }

    def get_analytics_data(self, endpoint):
        """Fetch data from Kinsta with improved error handling."""
        url = f"{self.base_url}/{endpoint}"
        print(f"Calling: {url}...")
        response = requests.get(url, headers=self.headers, params=self.params)
        
        if response.status_code != 200:
            print(f"API Error Details: {response.text}")
        
        response.raise_for_status()
        return response.json()

    def create_visuals(self, visits_data):
        """Generate trend chart from visits data."""
        # Kinsta returns data in a 'data' list
        stats = visits_data.get('data', [])
        if not stats:
            print("No data points found for the chart.")
            return False

        dates = [item['datetime'][:10] for item in stats]
        values = [int(item['value']) for item in stats]

        plt.figure(figsize=(10, 5))
        plt.plot(dates, values, marker='o', color='#5333ed', linewidth=2)
        plt.fill_between(dates, values, color='#5333ed', alpha=0.1)
        plt.title("Weekly Traffic Insights", fontsize=14)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("visits_chart.png")
        return True

    def generate_ai_analysis(self, raw_data):
        """Gemini AI narrative generation."""
        prompt = f"Analyze these web hosting metrics from Kinsta: {raw_data}. Provide a professional 100-word summary."
        response = model.generate_content(prompt)
        return response.text

    def build_pdf(self, ai_text):
        """Final PDF assembly."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "Kinsta Performance Report", ln=True, align="C")
        
        if os.path.exists("visits_chart.png"):
            pdf.image("visits_chart.png", x=10, y=30, w=190)
        
        pdf.set_y(130)
        pdf.set_font("helvetica", "", 11)
        pdf.multi_cell(0, 7, ai_text)
        pdf.output("Kinsta_Weekly_Report.pdf")

def main():
    try:
        report = KinstaReportGenerator()
        
        # 1. Fetching all required metrics
        data_package = {
            "visits": report.get_analytics_data("visits"),
            "bandwidth": report.get_analytics_data("server-bandwidth"),
            "cdn": report.get_analytics_data("cdn-bandwidth"),
            "disk": report.get_analytics_data("disk-usage")
        }

        # 2. Visuals
        report.create_visuals(data_package['visits'])

        # 3. AI Analysis
        summary = report.generate_ai_analysis(data_package)

        # 4. PDF
        report.build_pdf(summary)
        print("Report generated successfully!")

    except Exception as e:
        print(f"Final Error: {e}")

if __name__ == "__main__":
    main()
