from readepd3 import try_final_fallback


def try_gwp_block_cipa_gres(pdf_path, filename, cursor):
    import re
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            lines = text.splitlines()
            for line in lines:
                if "GWP [kg CO2-Eq.]" in line:
                    clean_line = line.replace(",", ".")
                    parts = clean_line.split("GWP [kg CO2-Eq.]")
                    if len(parts) < 2:
                        continue
                    data_part = parts[1]

                    data_part = data_part.replace("- ", "-")
                    values = re.findall(
                        r"-?\d+(?:\.\d+)?(?:E[+-]?\d+)?", data_part)

                    modules = [
                        "A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5",
                        "B6", "B7", "C1", "C2", "C3/1", "C3/2",
                        "C4/1", "C4/2", "D/1"
                    ]

                    if len(values) > len(modules):
                        values = values[-len(modules):]

                    print(f"\n📄 FALLBACK CIPA GRES: {filename} [Page {i+1}]")
                    if len(values) != len(modules):
                        print(
                            f"❌ Mismatch — Found {len(values)}, expected {len(modules)}")
                        print("Line:", data_part)
                        return

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


def try_gwp_firesilicone(pdf_path, filename, cursor):
    import re
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            lines = text.splitlines()
            for line in lines:
                if "GWP-total" in line and "[kg CO2-Eq.]" in line:
                    clean_line = line.replace(",", ".").replace("- ", "-")
                    values = re.findall(
                        r"-?\d+(?:\.\d+)?(?:E[+-]?\d+)?", clean_line)

                    modules = ["A1-A3", "A4", "A5", "C1", "C2", "C3", "D"]

                    if len(values) > len(modules):
                        values = values[-len(modules):]

                    print(
                        f"\n📄 FALLBACK FIRESILICONE: {filename} [Page {i+1}]")
                    if len(values) != len(modules):
                        print(
                            f"❌ Mismatch — Found {len(values)}, expected {len(modules)}")
                        print("Line:", clean_line)
                        return

                    for mod, val in zip(modules, values):
                        try:
                            float_val = float(val)
                            print(f"  {mod:<5} = {float_val}")
                            cursor.execute(
                                "INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)",
                                (filename, i + 1, mod, float_val)
                            )
                        except Exception as e:
                            print(f"⚠️ {mod} = {val} → {e}")
                    return


def try_gwp_sevenval(pdf_path, filename, cursor):
    import re
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            lines = page.extract_text().splitlines() if page.extract_text() else []
            for idx, line in enumerate(lines):
                if "GWP-total" in line and "[kg CO2-Eq.]" in line:
                    full_text = line
                    # check next line too if available
                    if idx + 1 < len(lines):
                        full_text += " " + lines[idx + 1]
                    clean_line = full_text.replace(",", ".").replace("- ", "-")
                    values = re.findall(
                        r"-?\d+(?:\.\d+)?(?:E[+-]?\d+)?", clean_line)

                    modules = ["A1-A3", "A4", "A5", "C1", "C2", "C3", "D"]

                    if len(values) > len(modules):
                        values = values[-len(modules):]

                    print(f"\n📄 FALLBACK SEVENVAL: {filename} [Page {i+1}]")
                    if len(values) != len(modules):
                        print(
                            f"❌ Mismatch — Found {len(values)}, expected {len(modules)}")
                        print("Line:", clean_line)
                        return

                    for mod, val in zip(modules, values):
                        try:
                            float_val = float(val)
                            print(f"  {mod:<5} = {float_val}")
                            cursor.execute(
                                "INSERT INTO gwp_values (filename, page, module, value) VALUES (?, ?, ?, ?)",
                                (filename, i + 1, mod, float_val)
                            )
                        except Exception as e:
                            print(f"⚠️ {mod} = {val} → {e}")
                    return


def try_alternative_parsing(pdf_path, filename, cursor):
    if "cipa gres" in filename.lower():
        try_gwp_block_cipa_gres(pdf_path, filename, cursor)
    elif "firesilicone" in filename.lower():
        try_gwp_firesilicone(pdf_path, filename, cursor)
    else:
        try_gwp_sevenval(pdf_path, filename, cursor)
        try_final_fallback(pdf_path, filename, cursor)
