import fitz  # PyMuPDF
import re
import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="📦 PICK Ticket Extractor", layout="wide")
st.title("📄 PICK Ticket PDF Extractor")

def parse_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    lines = []
    for page in doc:
        lines += page.get_text().splitlines()

    entries = []
    i = 0

    while i < len(lines):
        if lines[i].strip() == "PICK":
            try:
                pick_raw = lines[i + 1].strip()
                _ = lines[i + 2].strip()  # often '0'
                part_no = lines[i + 3].strip()

                # Find where 'EA' is
                ea_index = -1
                for j in range(i + 4, i + 10):
                    if lines[j].strip() == "EA":
                        ea_index = j
                        break
                if ea_index == -1:
                    raise ValueError("EA not found")

                # Combine all lines between part_no and EA as description
                description_lines = [lines[k].strip() for k in range(i + 4, ea_index)]
                description = " ".join(description_lines)

                qty_ordered = int(lines[ea_index + 1].strip())
                qty_committed = int(lines[ea_index + 2].strip())
                qty_bo = int(lines[ea_index + 3].strip())

                first_pick_number = re.findall(r'\d+', pick_raw)[0]

                entries.append({
                    "PICK": first_pick_number,
                    "Part #": part_no,
                    "Description": description,
                    "Qty Ordered": qty_ordered,
                    "Qty Committed": qty_committed,
                    "Qty B/O": qty_bo,
                    "sort_key": int(first_pick_number)
                })

                i = ea_index + 4
            except Exception as e:
                print(f"Skipping block at line {i} due to error: {e}")
                i += 1
        else:
            i += 1

    return sorted(entries, key=lambda x: x["sort_key"])

def create_pdf(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "📦 Sorted PICK Entries")
    y -= 30

    c.setFont("Helvetica", 10)
    for entry in data:
        text = (f"PICK {entry['PICK']} | Part #: {entry['Part #']} | "
                f"Description: {entry['Description']} | "
                f"Qty: {entry['Qty Ordered']} / {entry['Qty Committed']} / {entry['Qty B/O']}")
        c.drawString(40, y, text)
        y -= 18
        if y < 50:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 10)

    c.save()
    buffer.seek(0)
    return buffer

# === Streamlit App ===
uploaded_file = st.file_uploader("📄 Upload your PICKING TICKET PDF", type="pdf")

if uploaded_file:
    with st.spinner("Processing..."):
        data = parse_pdf(uploaded_file)

    if data:
        df = pd.DataFrame(data).drop(columns=["sort_key"])
        st.success("✅ Extracted and sorted successfully!")
        st.dataframe(df, use_container_width=True)

        pdf_buffer = create_pdf(data)
        st.download_button("⬇️ Download Results as PDF", pdf_buffer, file_name="sorted_pick_entries.pdf", mime="application/pdf")
    else:
        st.warning("⚠️ No valid PICK entries found.")
