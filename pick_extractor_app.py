import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
from fpdf import FPDF
import tempfile

st.set_page_config(page_title="PICK Ticket PDF Extractor", layout="wide")

st.title("📄 PICK Ticket PDF Extractor")
st.markdown("#### 📤 Upload your PICKING TICKET PDF")

uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

# Helper to safely encode text
def safe_text(text):
    return str(text).encode('latin-1', errors='replace').decode('latin-1')

# PDF Export with Row/Column Formatting
def generate_pdf(sorted_entries):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    headers = ["PICK", "Part #", "Description", "Qty Ordered", "Qty Committed", "Qty B/O"]
    widths = [20, 40, 80, 20, 20, 15]

    for h, w in zip(headers, widths):
        pdf.cell(w, 10, safe_text(h), border=1)
    pdf.ln()

    for row in sorted_entries:
        data = [
            row["pick"],
            row["part_no"],
            row["description"],
            row["qty_ordered"],
            row["qty_committed"],
            row["qty_bo"]
        ]
        for d, w in zip(data, widths):
            pdf.cell(w, 10, safe_text(d), border=1)
        pdf.ln()

    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmpfile.name)
    return tmpfile.name

# Extraction logic
def extract_picks_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    lines = []
    for page in doc:
        lines += page.get_text().splitlines()

    entries = []
    i = 0

    while i < len(lines):
        if lines[i].strip() == "PICK":
            try:
                pick_number = re.sub(r"[^\d]", "", lines[i + 1].strip())  # Keep only digits
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

                unit = lines[ea_index]
                qty_ordered = int(lines[ea_index + 1])
                qty_committed = int(lines[ea_index + 2])
                qty_bo = int(lines[ea_index + 3])

                entries.append({
                    "sort_key": int(pick_number),
                    "pick": pick_number,
                    "part_no": part_no,
                    "description": description.strip(),
                    "qty_ordered": qty_ordered,
                    "qty_committed": qty_committed,
                    "qty_bo": qty_bo
                })

                i = ea_index + 4
            except Exception as e:
                i += 1
        else:
            i += 1

    sorted_entries = sorted(entries, key=lambda x: x["sort_key"])
    return sorted_entries

# Main app logic
if uploaded_file:
    try:
        sorted_entries = extract_picks_from_pdf(uploaded_file)

        if sorted_entries:
            st.success("✅ Extracted and sorted successfully!")

            df = pd.DataFrame(sorted_entries)[["pick", "part_no", "description", "qty_ordered", "qty_committed", "qty_bo"]]
            df.columns = ["PICK", "Part #", "Description", "Qty Ordered", "Qty Committed", "Qty B/O"]
            st.dataframe(df, use_container_width=True)

            # PDF Export
            pdf_file = generate_pdf(sorted_entries)
            with open(pdf_file, "rb") as f:
                st.download_button("📄 Download Results as PDF", f, file_name="pick_summary.pdf", mime="application/pdf")

        else:
            st.warning("⚠️ No valid PICK entries found.")
    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
