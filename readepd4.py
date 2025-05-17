import pdfplumber
import os
import re
import sqlite3

FOLDER = "pdfs"
DB_NAME = "gwp_data.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gwp_values (
            filename TEXT,
            page INTEGER,
            module TEXT,
            value REAL
        )
    ''')
    conn.commit()
    return conn


def extract_gwp_values(pdf_path, filename, cursor):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue

                full_text = text.replace(",", ".").replace(
                    "- ", "-").replace("\n", " ")

                # extract ALL scientific numbers from the page
                values = re.findall(
                    r"-?\d+(?:\.\d+)?(?:E[+-]?\d+)?", full_text)
                values = [v for v in values if v.upper() != "MND"]

                modules = ["A1", "A2", "C1", "C2", "C3", "C4"]

                if len(values) < len(modules):
                    print(f"TOO FEW VALUES on page {i+1}: got {len(values)}")
                    continue

                for mod, val in zip(modules, values[:len(modules)]):
                    try:
                        cursor.execute(
                            "INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)",
                            (filename, i + 1, mod, float(val))
                        )
                        print(f"{filename} [Page {i+1}] {mod} = {float(val)}")
                    except Exception as e:
                        print(f"ERROR: {mod} = {val} in {filename}: {e}")
                return
    except Exception as e:
        print(f"FAILED TO PROCESS {filename}: {e}")


def try_gwp_blgv_signed(pdf_path, filename, cursor):
    print(f"[RUNNING] try_gwp_blgv_signed for {filename}")
    extract_gwp_values(pdf_path, filename, cursor)


def main():
    if not os.path.exists(FOLDER):
        print("FOLDER DOES NOT EXIST.")
        return

    conn = init_db()
    cursor = conn.cursor()

    for filename in os.listdir(FOLDER):
        if not filename.lower().endswith(".pdf"):
            continue

        path = os.path.join(FOLDER, filename)
        rows_before = cursor.execute(
            "SELECT COUNT(*) FROM gwp_values").fetchone()[0]

        try_gwp_blgv_signed(path, filename, cursor)

        rows_after = cursor.execute(
            "SELECT COUNT(*) FROM gwp_values").fetchone()[0]
        if rows_after == rows_before:
            print(f"NO GWP FOUND IN {filename}")

    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM gwp_values")
    print(f"TOTAL ROWS: {cursor.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
