import logging
import os
import pdfplumber
from openai import OpenAI
import warnings
warnings.filterwarnings("ignore")

logging.getLogger("pdfminer").setLevel(logging.ERROR)

# eller sæt direkte: openai.api_key = "din-nøgle"


def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                if "GWP" in page_text and "CO2" in page_text:
                    text += page_text + "\n"
    return text


def ask_gpt_for_gwp(text):
    prompt = (
        "From the following EPD extract, find ONLY the GWP values from the row labeled something like: "
        "'GWP [kg CO2-eq.]'. Ignore other rows, units, and environmental categories. "
        "they can be in tables both vertical and horizontal, but may not be in tables"
        "If there is something called GWP total, GWP-total, GWP - total, then this is the data i need."
        "Map these values to the following modules in order: "
        "['A1-A3', 'A1-A3 (second)', 'A4', 'A5', 'C2', 'C3', 'C4', 'D'] "
        "and return as JSON:\n\n"
        "{\n  \"GWP\": {\n    \"A1-A3\": ..., \"A1-A3 (second)\": ..., \"A4\": ..., ..., \"D\": ...\n  }\n}\n\n"
        "keep trying till you find the data"
        "Try, try and try again"
        f"{text}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ GPT-fejl: {e}"


def process_all_pdfs(folder):
    for file in os.listdir(folder):
        if file.lower().endswith(".pdf"):
            full_path = os.path.join(folder, file)
            print(f"\n📄 Behandler: {file}")
            text = extract_text_from_pdf(full_path)
            if not text.strip():
                print("⚠️ Ingen relevant tekst fundet.")
                continue
            result = ask_gpt_for_gwp(text)

            print(result)


if __name__ == "__main__":
    process_all_pdfs(PDF_FOLDER)
