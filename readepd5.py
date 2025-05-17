import re
import fitz  # PyMuPDF
import pandas as pd


def try_gwp_epse_style(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)

    with open("debug_epse_dump.txt", "w", encoding="utf-8") as f:
        f.write(text)

    lines = text.split("\n")
    gwp_line_index = -1

    with open("debug_lines.txt", "w", encoding="utf-8") as debug_file:
        for i in range(len(lines) - 4):
            window = lines[i].lower() + lines[i+1].lower() + lines[i+2].lower()
            debug_file.write(f"LINE {i}: {lines[i]}\n")
            if "gwp" in window and "total" in window and "kg co2" in window:
                gwp_line_index = i + 4  # value block starts 4 lines after header start
                break

    if gwp_line_index == -1 or gwp_line_index + 2 >= len(lines):
        print("❌ GWP - total line not found")
        return None

    data_block = " ".join(lines[gwp_line_index: gwp_line_index + 25])

    # data_block = " ".join(lines[gwp_line_index: gwp_line_index + 10])
    data_block = data_block.replace(",", ".")
    values = re.findall(r"-?\d+\.\d+E[+-]?\d+", data_block)

    if len(values) < 18:
        print(f"❌ Found {len(values)} GWP values, expected 18.")
        return None

    stages = [
        "A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7",
        "C1", "C2", "C3", "C4", "D", "Total"
    ]

    df = pd.DataFrame({"Stage": stages, "GWP_total_kgCO2eq": values[:18]})
    return df


def extract_and_store_epse_gwp(pdf_path, conn=None):
    df = try_gwp_epse_style(pdf_path)
    if df is None:
        print(f"❌ No GWP data found in {pdf_path}")
        return

    print(f"📄 Extracted EPSE GWP from {pdf_path}")
    print(df)

    if conn:
        cursor = conn.cursor()
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO gwp_values (filename, page, module, value)
                    VALUES (?, ?, ?, ?)
                """, (pdf_path, 1, row['Stage'], float(row['GWP_total_kgCO2eq'])))
            except Exception as e:
                print(
                    f"⚠️ DB insert failed for {row['Stage']} = {row['GWP_total_kgCO2eq']}: {e}")
        conn.commit()

# THIS MODULE IS TO BE CALLED FROM readepd.py — NOT STANDALONE
