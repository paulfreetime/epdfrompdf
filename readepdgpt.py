import os
import re
import fitz  # PyMuPDF for OCR fallback
from openai import OpenAI

# Config

client = OpenAI(
    api_key=api_key,
    default_headers={"OpenAI-Beta": "assistants=v2"}
)


def extract_text_locally(path):
    try:
        doc = fitz.open(path)
        blocks = []
        for page in doc:
            blocks.extend(page.get_text("blocks"))
        # Sort top-down, left-right
        blocks = sorted(blocks, key=lambda b: (round(b[1]), b[0]))
        table = []
        for b in blocks:
            txt = b[4].strip()
            if txt:
                table.append(txt)
        print("\n📊 RAW EXTRACTED TABLE-LIKE TEXT:\n")
        for row in table:
            print(row)
        # Save to file so you can actually SEE the bastard output
        with open("gwp_raw_output.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(table))
        return "\n".join(table)
    except Exception as e:
        return f"❌ Error extracting blocks: {e}"


def upload_to_assistant(text):
    try:
        thread = client.beta.threads.create()
        content = (
            "Here's raw extracted table-like text from a PDF."
            " Parse it and extract all rows that contain GWP values, including scientific notation."
            " Keep the structure intact if you can.\n\n" + text
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
                return "❌ GPT failed like a clown."
            time.sleep(1)
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                for block in msg.content:
                    if block.type == "text":
                        return block.text.value
        return "❌ Assistant gave no useful shit."
    except Exception as e:
        return f"💥 Upload failed: {e}"


def main():
    for file in os.listdir(pdf_folder):
        if file.lower().endswith(".pdf"):
            path = os.path.join(pdf_folder, file)
            print(f"\n📄 {file}")
            text = extract_text_locally(path)
            if text.startswith("❌"):
                print(text)
                continue
            reply = upload_to_assistant(text)
            print("\n🤖 GPT's Interpretation:\n")
            print(reply)


if __name__ == "__main__":
    main()
