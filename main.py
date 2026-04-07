import os
import requests
import matplotlib.pyplot as plt
from google import generativeai as genai
from fpdf import FPDF
from datetime import datetime

# --- Configuration and Environment Variables ---
# These should be set in GitHub Secrets for security
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_ENV_ID = os.getenv("KINSTA_ENV_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaReportGenerator:
    def __init__(self):
        self.api_url = f"https://api.kinsta.com/v2/sites/environments/{KINSTA_ENV_ID}/analytics"
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.params = {"time_span": "last_7_days"}

    def get_analytics_data(self, endpoint):
        """Fetch data from specific Kinsta Analytics endpoints."""
        response = requests.get(f"{self.api_url}/{endpoint}", headers=self.headers, params=self.params)
        response.raise_for_status()
        return response.json()

    def create_visuals(self, visits_data):
        """Generate a trend chart for the last 7 days of visits."""
        # Parsing data from Kinsta API format: {"data": [{"datetime": "...", "value": "..."}]}
        dates = [item['datetime'][:10] for item in visits_data['data']]
        values = [int(item['value']) for item in visits_data['data']]

        plt.figure(figsize=(10, 5))
        plt.plot(dates, values, marker='o', linestyle='-', color='#5333ed', linewidth=2)
        plt.fill_between(dates, values, color='#5333ed', alpha=0.1)
        plt.title("Weekly Website Traffic (Unique Visits)", fontsize=14)
        plt.xlabel("Date")
        plt.ylabel("Visits")
        plt.xticks(rotation=45)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig("visits_chart.png")

    def generate_ai_analysis(self, raw_data):
        """Use Gemini to transform technical metrics into a client-friendly narrative."""
        prompt = (
            f"As a web performance expert, analyze these Kinsta hosting metrics: {raw_data}. "
            "Write a concise weekly summary (max 150 words) for a non-technical client. "
            "Focus on traffic trends, bandwidth usage (Server vs CDN), and disk space health. "
            "Maintain a professional and reassuring tone."
        )
        response = model.generate_content(prompt)
        return response.text

    def build_pdf(self, ai_text):
        """Assemble the final PDF report with branding, charts, and AI text."""
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("helvetica", "B", 20)
        pdf.set_text_color(83, 51, 237) # Kinsta-ish Purple
        pdf.cell(0, 20, "Weekly Performance Insights", ln=True, align="C")
        
        # Add Chart
        pdf.image("visits_chart.png", x=10, y=40, w=190)
        
        # Add AI Content
        pdf.set_y(145)
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "Executive Summary", ln=True)
        
        pdf.set_font("helvetica", "", 11)
        pdf.multi_cell(0, 7, ai_text)
        
        # Footer
        pdf.set_y(-20)
        pdf.set_font("helvetica", "I", 8)
        pdf.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d')} | Powered by Kinsta API & Gemini AI", align="C")
        
        pdf.output("Kinsta_Weekly_Report.pdf")

def main():
    try:
        report = KinstaReportGenerator()
        
        print("Fetching data from Kinsta API...")
        # Following strictly the documentation provided
        analytics = {
            "visits": report.get_analytics_data("visits"),
            "server_bandwidth": report.get_analytics_data("server-bandwidth"),
            "cdn_bandwidth": report.get_analytics_data("cdn-bandwidth"),
            "disk_usage": report.get_analytics_data("disk-usage")
        }

        print("Generating chart...")
        report.create_visuals(analytics['visits'])

        print("Consulting Gemini AI for analysis...")
        summary = report.generate_ai_analysis(analytics)

        print("Finalizing PDF report...")
        report.build_pdf(summary)
        
        print("Success! Report saved as Kinsta_Weekly_Report.pdf")

    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()
