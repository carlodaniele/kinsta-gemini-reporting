import os
import requests
import matplotlib.pyplot as plt
from google import generativeai as genai
from fpdf import FPDF
from datetime import datetime

# --- Configuration from GitHub Secrets ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_SITE_ID = os.getenv("KINSTA_SITE_ID") # Use Site ID now, not Env ID
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Setup Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaSimpleReporter:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/{KINSTA_SITE_ID}/usage"

    def fetch_data(self, metric_path):
        """Fetch data from the specific usage endpoint."""
        url = f"{self.base_url}/{metric_path}"
        print(f"Fetching: {url}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_chart(self, visits_data):
        """Create a simple line chart from the visits data."""
        # The API returns a list of daily stats in 'data'
        stats = visits_data.get('data', [])
        if not stats:
            return False
            
        days = [item['datetime'][:10] for item in stats]
        counts = [int(item['value']) for item in stats]

        plt.figure(figsize=(10, 5))
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=2)
        plt.title("Daily Visits (This Month)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("chart.png")
        return True

    def get_ai_summary(self, data):
        """Ask Gemini to explain the data in plain English."""
        prompt = f"Summarize these website analytics for a client: {data}. Max 100 words."
        response = model.generate_content(prompt)
        return response.text

    def create_pdf(self, text):
        """Generate the final PDF report."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Kinsta Monthly Performance Report", ln=True, align="C")
        
        if os.path.exists("chart.png"):
            pdf.image("chart.png", x=10, y=30, w=180)
            
        pdf.set_y(130)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, text)
        pdf.output("Kinsta_Report.pdf")

def main():
    try:
        report = KinstaSimpleReporter()
        
        # Following your provided documentation endpoints:
        # /usage/visits/this-month
        # /usage/server-bandwidth/this-month
        print("Gathering data...")
        visits = report.fetch_data("visits/this-month")
        bandwidth = report.fetch_data("server-bandwidth/this-month")
        
        print("Creating chart...")
        report.create_chart(visits)
        
        print("Generating AI summary...")
        analysis = report.get_ai_summary({"visits": visits, "bandwidth": bandwidth})
        
        print("Saving PDF...")
        report.create_pdf(analysis)
        print("Done! Check your artifacts.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
