import os
import time
from openai import OpenAI

# Config
api_key = "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"
assistant_id = "asst_7HKlZKaXMHUA46FpsAMSBMkK"
folder = "C:/Code/EPDextract/EPDextract/epd"

# Proper client
client = OpenAI(
    api_key=api_key,
    default_headers={"OpenAI-Beta": "assistants=v2"}
)

def upload_file(path):
    with open(path, "rb") as f:
        return client.files.create(file=f, purpose="assistants")

def extract_from_pdf(path):
    try:
        file = upload_file(path)
        thread = client.beta.threads.create()

        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=(
                "Use PyMuPDF or pdfplumber to extract all visible text from this PDF. "
                "Search for all lines that contain the substring 'GWP' or 'GWP – total' or 'GWP-total', even with weird dashes. "
                "Return any line that has a GWP label and at least one numeric value in scientific notation like E-1 or E+0. "
                "Preserve the original line formatting and values. If that doesn't work try to Return any line that has a GWP label and at least one numeric value in scientific notation like E-1 or E+0."
                "If no values try unable to extract EPD data"
            ),
            attachments=[{
                "file_id": file.id,
                "tools": [{"type": "code_interpreter"}]
            }]
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )

        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                return "❌ Run failed."
            time.sleep(1)

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                for block in msg.content:
                    if block.type == "text":
                        return block.text.value

        return "❌ No assistant reply found."

    except Exception as e:
        return f"💥 Error: {e}"

def main():
    for file in os.listdir(folder):
        if file.lower().endswith(".pdf"):
            path = os.path.join(folder, file)
            print(f"\n📄 {file}")
            result = extract_from_pdf(path)
            print(result)

if __name__ == "__main__":
    main()
