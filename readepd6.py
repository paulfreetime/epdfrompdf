import pdfplumber
import re
from collections import defaultdict


def extract_all_gwp(pdf_path, filename, cursor):
    print(f"\n🔍 DEBUG: Running extract_all_gwp from readepd6 on {filename}")
    seen_counts = defaultdict(int)

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            text = page.extract_text()
            if not text:
                continue

            lines = text.splitlines()
            for line in lines:
                line = line.replace("–", "-")
                match = re.match(
                    r"^(A1-A3|A4|A5|B1-B7|C1|C2|C3|C4|D)\s+([-0-9E+.,\s]+)", line)
                if match:
                    module = match.group(1)
                    key = (filename, page_num, module)
                    seen_counts[key] += 1

                    if seen_counts[key] > 1:
                        continue  # Skip duplicates after first

                    raw_values = match.group(2).replace(",", ".")
                    values = re.findall(
                        r"-?\d+\.\d+E[-+]?\d+|-?\d+\.\d+", raw_values)
                    if not values:
                        continue
                    try:
                        float_val = float(values[0])

                        cursor.execute("""
                            INSERT INTO gwp_values (filename, page, module, value)
                            VALUES (?, ?, ?, ?)
                        """, (filename, page_num, module, float_val))

                        print(
                            f"[Page {page_num}] Saved {module} = {float_val}")
                    except Exception as e:
                        print(f"⚠️ Failed {module} = {values[0]} → {e}")
