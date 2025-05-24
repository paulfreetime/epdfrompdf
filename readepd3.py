import pdfplumber
import re
from readepd4 import try_gwp_blgv_signed

# === Fallback parsing for: EPD_20_0103_004-EN_BLGV_boardstandard_00 ===


def try_gwp_blgv_board(pdf_path, filename, cursor):
    print(f"➡️ Entering try_gwp_blgv_board for {filename}")  # Debug print

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            full_text = text.replace(",", ".").replace(
                "- ", "-").replace("\n", " ")

            if "GWP (kg CO2 equiv/FU)" not in full_text:
                continue

            label_index = full_text.find("GWP (kg CO2 equiv/FU)")
            after_label = full_text[label_index +
                                    len("GWP (kg CO2 equiv/FU)"):].strip()
            values_after = re.findall(
                r"-?\d+(?:\.\d+)?(?:E[+-]?\d+)?|MND", after_label)

            # Filter out MND before slicing
            filtered_values = [v for v in values_after if v != "MND"]

            modules = ["A1", "A2", "C1", "C2", "C3", "C4"]

            if len(filtered_values) < len(modules):
                print(
                    f"❌ Not enough usable values after label — Found {len(filtered_values)}, expected {len(modules)}")
                continue

            selected_values = filtered_values[:len(modules)]

            print(f"\n📄 FALLBACK BLGV BOARD: {filename} [Page {i+1}]")
            for mod, val in zip(modules, selected_values):
                try:
                    float_val = float(val)
                    print(f"  {mod:<4} = {float_val}")
                    cursor.execute(
                        "INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)",
                        (filename, i + 1, mod, float_val)
                    )
                except Exception as e:
                    print(f"⚠️ {mod} = {val} → {e}")
            return


def try_final_fallback(pdf_path, filename, cursor):
    if "blgv" in filename.lower():
        try_gwp_blgv_board(pdf_path, filename, cursor)
        try_gwp_blgv_signed(pdf_path, filename, cursor)
