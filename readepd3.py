import pdfplumber
import re

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

            values = re.findall(
                r"-?\d+(?:\.\d+)?(?:E[+-]?\d+)?|MND", full_text)

            # Slice values after the label occurrence
            label_index = full_text.find("GWP (kg CO2 equiv/FU)")
            after_label = full_text[label_index:]
            values_after = re.findall(
                r"-?\d+(?:\.\d+)?(?:E[+-]?\d+)?|MND", after_label)

            modules = [
                "A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5",
                "B6", "B7", "C1", "C2", "C3", "C4", "D"
            ]

            if len(values_after) < len(modules):
                print(
                    f"❌ Not enough values after label — Found {len(values_after)}, expected {len(modules)}")
                continue

            selected_values = values_after[:len(modules)]

            print(f"\n📄 FALLBACK BLGV BOARD: {filename} [Page {i+1}]")
            for mod, val in zip(modules, selected_values):
                if val == "MND":
                    continue
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
