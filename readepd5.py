import re
import fitz  # PyMuPDF
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
import inspect
import pdfplumber


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


def ocr_extract_gwp_from_pdf(pdf_path, cursor=None, filename=None):
    caller = inspect.stack()[1].filename
    print(f"🧠 CALLED FROM: {caller}")
    print(f"🧠 DEBUG: filename passed = {repr(filename)}")

    images = convert_from_path(pdf_path)
    full_text = ''
    for img in images:
        full_text += pytesseract.image_to_string(img, lang='eng')

    gwp_lines = [line for line in full_text.split(
        '\n') if 'GWP' in line and re.search(r'\d+[.,]\d+E[+-]\d+', line)]
    modules = ['A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B2', 'C1', 'D']

    for line in gwp_lines:
        label_match = re.match(r'[^a-zA-Z]*([Gg][Ww][Pp][^\s]*)', line)
        label = label_match.group(1).strip() if label_match else 'GWP-unknown'

        values = re.findall(r'[-+]?\d+[.,]?\d*E[+-]?\d+', line)
        if not values or len(values) < 3:
            continue

        values = [v.replace(",", ".") for v in values]
        for i, value in enumerate(values[:len(modules)]):
            module = modules[i]
            try:
                cursor.execute(
                    "INSERT INTO gwp_values (filename, indicator, module, value) VALUES (?, ?, ?, ?)",
                    (filename, label, module, float(value))
                )
            except Exception as e:
                print(f"[DB INSERT FAIL] {e}")

        print(f"[INSERTED] {label}: {values[:len(modules)]}")
        if cursor:
            cursor.connection.commit()

        break  # ⛔ Only insert the first GWP line and get the fuck out

# THIS MODULE IS TO BE CALLED FROM readepd.py — NOT STANDALONE


def extract_text_based_gwp_from_pdf(pdf_path, cursor=None, filename=None):
    print(f"\n🧠 STARTING CONTEXT + NEXT-LINE GWP SCAN for: {filename}")
    modules = ['A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7',
               'C1', 'C2', 'C3', 'C4', 'D']

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📄 PDF opened: {pdf_path}")
            print(f"📄 Total pages: {len(pdf.pages)}")

            for page_index, page in enumerate(pdf.pages):
                print(f"\n➡️ Scanning page {page_index + 1}")
                text = page.extract_text()
                if not text:
                    print("⚠️ No text extracted")
                    continue

                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if "gwp" in line.lower() or "kg co2" in line.lower():
                        print(f"📌 CONTEXT LINE: {line}")
                        if i + 1 >= len(lines):
                            continue
                        next_line = lines[i + 1]
                        print(f"👉 NEXT LINE: {next_line}")

                        floats = re.findall(r'[-+]?\d+\.\d+', next_line)
                        if len(floats) >= 6:
                            print(f"✅ GWP FLOATS: {floats}")

                            for j, val in enumerate(floats[:len(modules)]):
                                try:
                                    float_val = float(val)
                                    cursor.execute(
                                        "INSERT INTO gwp_values (filename, indicator, module, value) VALUES (?, ?, ?, ?)",
                                        (filename, "GWP",
                                         modules[j], float_val)
                                    )
                                    print(
                                        f"[INSERTED] GWP {modules[j]} = {val}")
                                except Exception as e:
                                    print(
                                        f"💥 INSERT FAIL {modules[j]} = {val} → {e}")

                            if cursor:
                                cursor.connection.commit()
                                print("🧾 COMMIT DONE")
                            return

            print("❌ No usable GWP value block found in next lines")

    except Exception as e:
        print(f"💣 TOTAL FAILURE: {e}")
