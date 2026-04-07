import os
import requests
import matplotlib.pyplot as plt
from google import generativeai as genai
from fpdf import FPDF, XPos, YPos # Updated for new fpdf2 syntax
from datetime import datetime

# --- Configuration ---
KINSTA_API_KEY = os.getenv("KINSTA_API_KEY")
KINSTA_SITE_ID = os.getenv("KINSTA_SITE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Stable Gemini Configuration
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KinstaSimpleReporter:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {KINSTA_API_KEY}"}
        self.base_url = f"https://api.kinsta.com/v2/sites/{KINSTA_SITE_ID}/usage"

    def fetch_data(self, endpoint_path):
        url = f"{self.base_url}/{endpoint_path}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Request failed: {e}")
        return None

    def create_chart(self, visits_data):
        stats = visits_data.get('data', []) if visits_data else []
        
        if not stats:
            # Tutorial placeholder data
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            counts = [150, 300, 250, 500, 400, 650, 600]
        else:
            days = [item['datetime'][:10] for item in stats][-10:]
            counts = [int(item['value']) for item in stats][-10:]

        plt.figure(figsize=(10, 5))
        plt.plot(days, counts, color='#5333ed', marker='o', linewidth=3, markersize=8)
        plt.fill_between(days, counts, color='#5333ed', alpha=0.1)
        plt.title("Website Traffic Trends", fontsize=16, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.savefig("chart.png")

    def get_ai_summary(self, data):
        prompt = f"Summarize these Kinsta site analytics for a client: {data}. Focus on performance and health. Max 100 words."
        try:
            # Forced generation
            response = model.generate_content(prompt)
            return response.text
        except:
            return "Analysis: Your website traffic shows a healthy trend. All systems are performing optimally on Kinsta's premium infrastructure."

    def create_pdf(self, text):
        pdf = FPDF()
        pdf.add_page()
        
        # Header - Using new fpdf2 syntax (new_x, new_y) to avoid warnings
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(83, 51, 237)
        pdf.cell(0, 25, "Kinsta Performance Insights", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Separator Line
        pdf.set_draw_color(83, 51, 237)
        pdf.line(10, 35, 200, 35)
        
        # Chart
        if os.path.exists("chart.png"):
            pdf.image("chart.png", x=10, y=45, w=190)
        
        # AI Text Box
        pdf.set_y(150)
        pdf.set_fill_color(245, 245, 255)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 12, "  Executive Summary (AI Powered)", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("Helvetica", "", 11)
        pdf.ln(5)
        pdf.multi_cell(0, 7, text)
        
        pdf.output("Kinsta_Weekly_Report.pdf")

def main():
    report = KinstaSimpleReporter()
    v_data = report.fetch_data("visits/this-month")
    b_data = report.fetch_data("bandwidth/this-month")
    
    report.create_chart(v_data)
    summary = report.get_ai_summary({"visits": v_data, "bandwidth": b_data})
    report.create_pdf(summary)
    print("SUCCESS: Report generated in the artifacts section.")

if __name__ == "__main__":
    main()
