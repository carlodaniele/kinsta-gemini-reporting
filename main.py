import os
import requests
import matplotlib.pyplot as plt
from google import generativeai as genai
from fpdf import FPDF
from datetime import datetime

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_SITE_ID = os.getenv("KINSTA_SITE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaSimpleReporter:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        # Correct base URL for site-specific usage
        self.base_url = f"https://api.kinsta.com/v2/sites/{KINSTA_SITE_ID}/usage"

    def fetch_data(self, endpoint_path):
        """Fetch monthly usage data."""
        url = f"{self.base_url}/{endpoint_path}"
        print(f"Fetching: {url}")
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Warning: Could not fetch {endpoint_path}. Status: {response.status_code}")
            return None
        return response.json()

    def create_chart(self, visits_data):
        """Generate chart from visits data."""
        if not visits_data or 'data' not in visits_data:
            print("No visit data available for chart.")
            return False
            
        stats = visits_data['data']
        # Extract last 10 days for clarity in the chart
        days = [item['datetime'][:10] for item in stats][-10:]
        counts = [int(item['value']) for item in stats][-10:]

        plt.figure(figsize=(10, 5))
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2, label="Visits")
        plt.title("Web Traffic Trend (Last 10 Days)", fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig("chart.png")
        return True

    def get_ai_summary(self, data_package):
        """Ask Gemini to interpret the raw data."""
        prompt = (
            f"As a web agency analyst, explain these Kinsta hosting stats for 'This Month' to a client: {data_package}. "
            "Write 3 bullet points: Traffic, Bandwidth, and a Recommendation. Max 100 words."
        )
        response = model.generate_content(prompt)
        return response.text

    def create_pdf(self, text):
        """Build the final PDF report."""
        pdf = FPDF()
        pdf.add_page()
        
        # Branding Header
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(83, 51, 237)
        pdf.cell(0, 20, "Kinsta Performance Insights", ln=True, align="C")
        
        # Insert Chart
        if os.path.exists("chart.png"):
            pdf.image("chart.png", x=10, y=40, w=190)
        
        # AI Analysis Section
        pdf.set_y(145)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "Executive Summary", ln=True)
        
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, text)
        
        pdf.output("Kinsta_Weekly_Report.pdf")

def main():
    try:
        report = KinstaSimpleReporter()
        
        print("Gathering monthly usage stats...")
        # Fixed endpoints based on latest API documentation
        visits = report.fetch_data("visits/this-month")
        bandwidth = report.fetch_data("bandwidth/this-month")
        
        print("Creating visual assets...")
        report.create_chart(visits)
        
        print("Consulting Gemini AI...")
        summary = report.get_ai_summary({"visits": visits, "bandwidth": bandwidth})
        
        print("Generating final PDF...")
        report.create_pdf(summary)
        print("Success! Process completed.")

    except Exception as e:
        print(f"Unexpected Error: {e}")

if __name__ == "__main__":
    main()
