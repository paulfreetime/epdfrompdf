import os
import pdfplumber
from openai import OpenAI
import time

# Config

***REMOVED***

client = OpenAI(
    api_key=api_key,
    default_headers={"OpenAI-Beta": "assistants=v2"}
)


def extract_gwp_markdown_table(path):
    try:
        stages = ["A1", "A2", "A3", "A4", "A5", "B1", "B2",
                  "B3", "B4", "B5", "C1", "C2", "C3", "C4", "D"]
        gwp_row = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and row[0] and "GWP" in row[0]:
                            index = table.index(row)
                            try:
                                # search forward for actual values, skip empty rows
                                for offset in range(1, 5):
                                    next_row = table[index + offset]
                                    if any(cell and ("E+" in cell or "E-" in cell) for cell in next_row):
                                        gwp_row = [
                                            v.strip() if v else "MND" for v in next_row[1:len(stages)+1]]
                                        break
                            except:
                                continue
        header = "| Stage | GWP (kg CO2 eq/FU) |"
        separator = "|---|---|"
        rows = [f"| {stage} | {val} |" for stage, val in zip(stages, gwp_row)]
        markdown_table = "\n".join([header, separator] + rows)
        output_path = os.path.join(os.path.dirname(path), "gwp_clean_table.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_table)
        return markdown_table
    except Exception as e:
        return f"❌ Error parsing table: {e}"


def upload_to_assistant(text):
    try:
        thread = client.beta.threads.create()
        content = (
            "Here's a clean Markdown table of GWP values by stage from an EPD. Extract and explain the values per stage.\n\n" + text
        )
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=content
        )
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                return "❌ GPT failed."
            time.sleep(1)
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                for block in msg.content:
                    if block.type == "text":
                        return block.text.value
        return "❌ No reply from GPT."
    except Exception as e:
        return f"💥 Upload failed: {e}"


def main():
    for file in os.listdir(pdf_folder):
        if file.lower().endswith(".pdf"):
            path = os.path.join(pdf_folder, file)
            print(f"\n📄 {file}")
            markdown_table = extract_gwp_markdown_table(path)
            if markdown_table.startswith("❌"):
                print(markdown_table)
                continue
            print("\n📑 MARKDOWN TABLE:\n")
            print(markdown_table)
            reply = upload_to_assistant(markdown_table)
            print("\n🤖 GPT's Output:")
            print(reply)


if __name__ == "__main__":
    main()
