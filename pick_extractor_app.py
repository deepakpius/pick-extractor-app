import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import tempfile
from fpdf import FPDF
import re
import os

def extract_picks_from_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    lines = []
    for page in doc:
        lines += page.get_text().splitlines()

    entries = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "PICK":
            try:
                pick_raw = lines[i + 1].strip()
                pick_match = re.search(r"\d+", pick_raw)
                pick_number = pick_match.group() if pick_match else "0"

                part_no = lines[i + 2].strip()
                next_line = lines[i + 3].strip()

                if next_line == "EA":
                    description = ""
                    ea_index = i + 3
                elif lines[i + 4].strip() == "EA":
                    description = next_line
                    ea_index = i + 4
                elif lines[i + 5].strip() == "EA":
                    description = f"{next_line} {lines[i + 4].strip()}"
                    ea_index = i + 5
                else:
                    raise ValueError("Expected 'EA' not found")

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
                print(f"Skipping block at line {i} due to error: {e}")
                i += 1
        else:
            i += 1

    return sorted(entries, key=lambda x: int(x["PICK"]))

def generate_pdf_table(entries):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=10)

    col_widths = [20, 35, 70, 20, 25, 20]
    headers = ["PICK", "Part #", "Description", "Qty Ordered", "Qty Committed", "Qty B/O"]

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1)
    pdf.ln()

    for entry in entries:
        row = [
            entry['PICK'],
            entry['Part #'],
            entry['Description'],
            str(entry['Qty Ordered']),
            str(entry['Qty Committed']),
            str(entry['Qty B/O'])
        ]
        for i, item in enumerate(row):
            pdf.cell(col_widths[i], 10, item.encode('latin-1', 'replace').decode('latin-1'), border=1)
        pdf.ln()

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp_file.name)
    return tmp_file.name

# Streamlit UI
st.set_page_config(page_title="PICK Ticket PDF Extractor", layout="centered")
st.title("📄 PICK Ticket PDF Extractor")

uploaded_file = st.file_uploader("Upload your PICKING TICKET PDF", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("🔍 Extracting data from PDF..."):
        try:
            sorted_entries = extract_picks_from_pdf(uploaded_file)
            if sorted_entries:
                df = pd.DataFrame(sorted_entries)
                st.success("✅ Extracted and sorted successfully!")
                st.dataframe(df, use_container_width=True)

                pdf_path = generate_pdf_table(sorted_entries)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Results as PDF",
                        data=f,
                        file_name="picking_ticket_output.pdf",
                        mime="application/pdf"
                    )

                os.remove(pdf_path)
            else:
                st.warning("⚠️ No valid PICK entries found in the uploaded PDF.")
        except Exception as e:
            st.error(f"❌ Error processing PDF: {e}")
