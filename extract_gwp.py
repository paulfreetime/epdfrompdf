import os
import pdfplumber
import re


def extract_gwp_totals(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        # DEBUG: Dump text to see what the hell we’re matching
        print("\n=== RAW TEXT DUMP ===")
        print(full_text)

        # Regex: Loosen it up, match any line with "GWP" and 9 numbers
        pattern = re.compile(
            r"GWP\s?.?total.*?(\d+\.\d+E[+-]?\d*).*?"  # A1-A3
            r"(\d+\.\d+E[+-]?\d*).*?"                 # A4
            r"(\d+\.\d+E[+-]?\d*).*?"                 # A5
            r"(?:MND|0E0).*?"                         # B stage (ignored)
            r"(?:0E0).*?"                             # C1
            r"(\d+\.\d+E[+-]?\d*).*?"                 # C2
            r"(\d+\.\d+E[+-]?\d*).*?"                 # C3
            r"(\d+\.\d+E[+-]?\d*).*?"                 # C4
            r"(-?\d+\.\d+E[+-]?\d*)"                  # D
            , re.IGNORECASE | re.DOTALL)

        match = pattern.search(full_text)
        if match:
            return [float(match.group(i)) for i in range(1, 9)] + [float(match.group(9))]
        else:
            return None

    except Exception as e:
        print(f"💥 Error reading {pdf_path}: {e}")
        return None


def main():
    folder_path = r"C:\Code\EPDextract\epd"
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            print(f"\n📄 {filename}")
            gwp = extract_gwp_totals(file_path)
            if gwp:
                stages = [
                    "A1-A3 (Production)", "A4 (Transport)", "A5 (Installation)",
                    "C2 (Waste Transport)", "C3 (Waste Processing)",
                    "C4 (Disposal)", "D (Recycling Credit)"
                ]
                print("\n✅ GWP-total values:")
                for i, val in enumerate(gwp):
                    label = stages[i] if i < len(stages) else f"Stage {i+1}"
                    print(f"{label:<25}: {val:.8E} kg CO₂ eq.")
            else:
                print("❌ GWP-total not found!")


if __name__ == "__main__":
    main()
