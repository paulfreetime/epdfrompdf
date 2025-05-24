import pdfplumber
import re
import sys
import contextlib
import warnings
import logging
import pyodbc
import os
from readepd2 import try_alternative_parsing
from readepd5 import extract_and_store_epse_gwp
from readepd6 import extract_all_gwp


logging.getLogger("pdfminer").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

FOLDER = "C:/code/EPDextract/EPDextract/epd"

# === MSSQL SETTINGS ===
MSSQL_SERVER = "192.168.3.151"
MSSQL_DATABASE = "EPDauto"
MSSQL_USERNAME = "sa"
MSSQL_PASSWORD = "Tun12345"


@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


def init_db():
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={MSSQL_SERVER},1433;"
        f"DATABASE={MSSQL_DATABASE};"
        f"UID={MSSQL_USERNAME};"
        f"PWD={MSSQL_PASSWORD};"
        "TrustServerCertificate=yes;"
        "Encrypt=no;"
    )
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("""
        IF OBJECT_ID('gwp_values', 'U') IS NULL
        CREATE TABLE gwp_values (
            id INT IDENTITY(1,1) PRIMARY KEY,
            filename NVARCHAR(255),
            indicator NVARCHAR(255),
            page INT,
            module NVARCHAR(20),
            value FLOAT
        )
    """)
    conn.commit()
    return conn


def extract_gwp_table(pdf_path, filename, cursor):
    with suppress_stderr(), pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            text = page.extract_text()
            lines = text.splitlines() if text else []

            inserted = False

            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or not row[0]:
                        continue
                    if "gwp-total" in row[0].lower():
                        print(f"\n📄 FILE: {filename}")
                        print(
                            f"[Page {page_num}] GWP-PDF-TABLE MODE:\nRow: {row}")

                        modules = ["A1-A3", "A4", "A5", "B1-B7",
                                   "C1", "C2", "C3", "C4", "D"]
                        raw_values = row[3:]
                        values = [v.replace(",", ".") for v in raw_values if v and re.fullmatch(
                            r"-?\d+(\.\d+)?E[-+]?\d+", v)]

                        if len(values) != len(modules):
                            print("❌ Table value/module mismatch")
                            continue

                        print("\n📊 Parsed GWP-total values (table):")
                        for mod, val in zip(modules, values):
                            try:
                                float_val = float(val)
                                print(f"  {mod:<6} = {float_val}")
                                cursor.execute("INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)", (
                                    filename, page_num, mod, float_val))
                                inserted = True
                            except Exception as e:
                                print(f"⚠️ Skipped {mod} = {val}: {e}")

            for idx, line in enumerate(lines):
                if "GWP-total" in line and "kg CO2" in line:
                    print(f"\n📄 FILE: {filename}")
                    print(
                        f"[Page {page_num}] GWP-MATRIX MODE:\nHeader: {line}")
                    if idx + 2 >= len(lines):
                        print("❌ No data line after header")
                        continue
                    data_line = lines[idx + 2]
                    print(f"Data Line: {data_line}")

                    modules = ["A1-A3", "A4", "A5", "B1-B7",
                               "C1", "C2", "C3", "C4", "D"]
                    parts = data_line.replace(",", ".").split()
                    values = [p for p in parts if re.fullmatch(
                        r"-?\d+\.\d+E[-+]?\d+", p)]

                    if len(values) != len(modules):
                        print("❌ Matrix mismatch")
                        continue

                    print("\n📊 Parsed GWP-total values (matrix):")
                    for mod, val in zip(modules, values):
                        try:
                            float_val = float(val)
                            print(f"  {mod:<6} = {float_val}")
                            cursor.execute("INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)", (
                                filename, page_num, mod, float_val))
                            inserted = True
                        except Exception as e:
                            print(f"⚠️ {mod} = {val} → {e}")

            for idx, line in enumerate(lines):
                if "GWP – total" in line or "GWP - total" in line:
                    raw = re.sub(r'\s+', ' ', line.strip())
                    print(f"\n📄 FILE: {filename}")
                    print(f"[Page {page_num}] GWP BLOCK MODE\nLINE: {raw}")

                    modules = ["A1", "A2", "A3", "A1-A3", "A4", "A5", "B1", "B2",
                               "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4", "D"]
                    tokens = raw.replace(",", ".").split()
                    if "CO2e" not in tokens:
                        print("❌ CO2e not found")
                        continue
                    values = tokens[tokens.index("CO2e") + 1:]

                    print("\n📊 Parsed GWP-total values (block):")
                    for mod, val in zip(modules, values):
                        if val.upper() == "MND":
                            continue
                        try:
                            float_val = float(val)
                            print(f"  {mod:<6} = {float_val}")
                            cursor.execute("INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)", (
                                filename, page_num, mod, float_val))
                            inserted = True
                        except Exception as e:
                            print(f"⚠️ Skip {mod} = {val} → {e}")
            if inserted:
                return


def extract_gwp_horizontal_matrix(pdf_path, filename, cursor):
    with suppress_stderr(), pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            text = page.extract_text()
            if not text:
                continue
            lines = text.splitlines()
            for line in lines:
                if re.search(r"\bGWP[-\s]?TOT", line, re.IGNORECASE):
                    print(f"\n📄 FILE: {filename}")
                    print(
                        f"[Page {page_num}] GWP-HORIZONTAL MODE\nLINE: {line}")

                    modules = ["A1-A3", "A4", "A5", "C2", "C4", "D"]
                    clean_line = line.replace(",", ".").replace("*", "")
                    tokens = clean_line.split()
                    float_candidates = [
                        t for t in tokens if re.fullmatch(r"-?\d+(\.\d+)?", t)]

                    if len(float_candidates) < len(modules):
                        print("❌ Not enough values found for GWP-HORIZONTAL")
                        continue

                    values = float_candidates[:len(modules)]

                    print("\n📊 Parsed GWP-total values (horizontal matrix):")
                    for mod, val in zip(modules, values):
                        try:
                            float_val = float(val)
                            print(f"  {mod:<6} = {float_val}")
                            cursor.execute("INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)", (
                                filename, page_num, mod, float_val))
                        except Exception as e:
                            print(f"⚠️ {mod} = {val} → {e}")
                    return


def extract_gwp_from_lca_matrix(pdf_path, filename, cursor):
    with suppress_stderr(), pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            text = page.extract_text()
            if not text:
                continue

            lines = text.splitlines()

            for idx, line in enumerate(lines):
                if re.search(r"^GWP\s*\[kg CO2", line, re.IGNORECASE):
                    print(f"\n📄 FILE: {filename}")
                    print(
                        f"[Page {page_num}] GWP-LCA-MATRIX MODE\nLINE: {line}")

                    # LCA matrix GWP values are in the next line
                    if idx + 1 >= len(lines):
                        print("❌ No data line after GWP header")
                        continue

                    data_line = lines[idx + 1].replace(",", ".")
                    values = re.findall(r"-?\d+\.\d+E[+-]?\d+", data_line)

                    modules = [
                        "A1-A3", "A1-A3 (2nd)", "A4", "A5", "C2", "C3", "C4", "D"]

                    if len(values) < len(modules):
                        print("❌ Not enough values found in GWP matrix")
                        print(f"Found: {values}")
                        continue

                    print("\n📊 Parsed GWP values (LCA matrix):")
                    for mod, val in zip(modules, values):
                        try:
                            float_val = float(val)
                            print(f"  {mod:<12} = {float_val}")
                            cursor.execute(
                                "INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)",
                                (filename, page_num, mod, float_val)
                            )
                        except Exception as e:
                            print(f"⚠️ Skip {mod} = {val} → {e}")
                    return


def extract_gwp_from_epd_matrix(pdf_path, filename, cursor):
    with suppress_stderr(), pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.splitlines()

            for idx, line in enumerate(lines):
                if re.match(r"^\s*GWP[-\s]*total\s*\[kg CO2.*?\]", line, re.IGNORECASE):
                    print(f"\n📄 FILE: {filename}")
                    print(f"[Page {i+1}] GWP-MODEL-EPD MATRIX\nLINE: {line}")

                    # Antag at værdier er på næste linje
                    if idx + 1 >= len(lines):
                        continue

                    data_line = lines[idx + 1].replace(",", ".")
                    values = re.findall(r"-?\d+\.\d+E[+-]?\d+", data_line)

                    modules = ["A1-A3", "A4", "A5", "C1", "C2", "C3", "D"]
                    if len(values) < len(modules):
                        print("❌ Not enough GWP values found")
                        print("Found:", values)
                        continue

                    print("\n📊 Parsed GWP values:")
                    for mod, val in zip(modules, values):
                        try:
                            float_val = float(val)
                            print(f"  {mod:<6} = {float_val}")
                            cursor.execute(
                                "INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)",
                                (filename, i + 1, mod, float_val)
                            )
                        except Exception as e:
                            print(f"⚠️ {mod} = {val} → {e}")
                    return


def main():
    print(f"\n🧪 Scanning folder: {FOLDER}")
    if not os.path.exists(FOLDER):
        print("❌ FOLDER path is wrong!")
        return

    conn = init_db()
    cursor = conn.cursor()
    files_found = 0

    for filename in os.listdir(FOLDER):
        if filename.lower().endswith(".pdf"):
            files_found += 1
            path = os.path.join(FOLDER, filename)

            if "solid_wall" in filename.lower():
                from readepd5 import extract_and_store_epse_gwp
                extract_and_store_epse_gwp(path, cursor.connection)
                continue

            success = False
            rows_before = cursor.execute(
                "SELECT COUNT(*) FROM gwp_values").fetchone()[0]

            extract_gwp_table(path, filename, cursor)
            extract_gwp_horizontal_matrix(path, filename, cursor)
            extract_gwp_from_lca_matrix(path, filename, cursor)
            extract_all_gwp(path, filename, cursor)

            rows_after = cursor.execute(
                "SELECT COUNT(*) FROM gwp_values").fetchone()[0]

            if rows_after == rows_before:
                print(f"🔁 Trying fallback extraction for {filename}")
                success = try_alternative_parsing(path, filename, cursor)

            if rows_after == rows_before:
                cursor.execute("INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)",
                               (filename, -1, 'NOT_FOUND', 0.0))
                print(f"❗ No values found in {filename}, inserted dummy row.")

            if not success:
                from readepd5 import extract_text_based_gwp_from_pdf
                print(
                    f"[Fallback] Trying text-based GWP extraction for {filename}")
                extract_text_based_gwp_from_pdf(path, cursor, filename)

                print(
                    f"[OCR Fallback] All parsing failed for {filename}. Using OCR…")
                from readepd5 import ocr_extract_gwp_from_pdf
                ocr_extract_gwp_from_pdf(path, cursor, filename)

    if files_found == 0:
        print("❌ No PDF files found in folder!")

    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM gwp_values")
    count = cursor.fetchone()[0]
    print(f"\n✅ TOTAL ROWS IN DB NOW: {count}")
    conn.close()


if __name__ == "__main__":
    main()
