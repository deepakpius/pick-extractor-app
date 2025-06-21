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
                pick_number = lines[i + 1].strip()
                part_no = lines[i + 2].strip()
                next_line = lines[i + 3].strip()

                if next_line == "EA":
                    description = ""
                    ea_index = i + 3
                else:
                    next_next_line = lines[i + 4].strip()
                    if next_next_line == "EA":
                        description = next_line
                        ea_index = i + 4
                    else:
                        description = f"{next_line} {next_next_line}"
                        ea_index = i + 5

                unit = lines[ea_index].strip()
                qty_ordered = int(lines[ea_index + 1].strip())
                qty_committed = int(lines[ea_index + 2].strip())
                qty_bo = int(lines[ea_index + 3].strip())

                entries.append({
                    "PICK": pick_number,
                    "Part #": part_no,
                    "Description": description.strip(),
                    "Qty Ordered": qty_ordered,
                    "Qty Committed": qty_committed,
                    "Qty B/O": qty_bo
                })

                i = ea_index + 4
            except Exception as e:
                i += 1
        else:
            i += 1

    return sorted(entries, key=lambda x: int(re.match(r'\d+', x["PICK"]).group()))


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


uploaded_file = st.file_uploader("📄 Upload your PICKING TICKET PDF", type="pdf")

if uploaded_file:
    with st.spinner("Processing..."):
        data = parse_pdf(uploaded_file)

    if data:
        df = pd.DataFrame(data)
        st.success("✅ Extracted and sorted successfully!")
        st.dataframe(df, use_container_width=True)

        pdf_buffer = create_pdf(data)
        st.download_button("⬇️ Download Results as PDF", pdf_buffer, file_name="sorted_pick_entries.pdf", mime="application/pdf")

    else:
        st.warning("⚠️ No valid PICK entries found.")
