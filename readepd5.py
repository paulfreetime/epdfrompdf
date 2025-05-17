import re
import fitz  # PyMuPDF
import pandas as pd


def try_gwp_epse_style(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)

    # Locate the GWP table by finding the header line
    match = re.search(
        r"GWP\s*-\s*total.*?\(kg CO2.*?equiv/FU\).*?(\d[\s\S]+?)GWP\s*-\s*fossil", text, re.IGNORECASE)
    if not match:
        return None

    data_block = match.group(1)
    lines = data_block.strip().split("\n")

    # Regex to find scientific notation values
    pattern = r"[\d,]+E[+-]\d+"
    gwp_values = []

    for line in lines:
        matches = re.findall(pattern, line)
        if len(matches) >= 18:
            gwp_values = matches[:18]  # First 18 stages
            break

    if not gwp_values:
        return None

    stages = [
        "A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7",
        "C1", "C2", "C3", "C4", "D", "Total"
    ]

    df = pd.DataFrame({"Stage": stages, "GWP_total_kgCO2eq": gwp_values})
    return df

# Example usage:
# df = try_gwp_epse_style("EPD_solid_wall_20220720_1900398_24_2023-02-14.pdf")
# if df is not None:
#     print(df)


def extract_and_store_epse_gwp(pdf_path, conn=None):
    df = try_gwp_epse_style(pdf_path)
    if df is None:
        print(f"No GWP data found in {pdf_path}")
        return

    print(df)

    if conn:
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO gwp_values (filename, stage, gwp_value)
                VALUES (?, ?, ?)
            """, (pdf_path, row['Stage'], row['GWP_total_kgCO2eq']))
        conn.commit()
