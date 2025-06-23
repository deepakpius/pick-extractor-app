import streamlit as st
import fitz  # PyMuPDF
import re
import pandas as pd
import tempfile
from fpdf import FPDF

st.set_page_config(page_title="Deks Industries", layout="wide")
#st.title("📄 Picking Ticket Sorter")

# Display logo and title
col1, col2 = st.columns([1, 6])
with col1:
    st.image("https://d1hbpr09pwz0sk.cloudfront.net/logo_url/deks-industries-australasia-405aec84", width=80)  # Placeholder logo URL
with col2:
    st.title("📄 Picking Ticket Sorter")

uploaded_file = st.file_uploader("Upload your PICKING TICKET PDF", type="pdf")

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        lines += page.get_text().splitlines()

    entries = []
    part_number_pattern = re.compile(r'^[A-Z0-9\-/]+$')

    for i in range(6, len(lines)):
        if lines[i].strip() == "EA":
            committed_qty = lines[i + 2].strip() if i + 2 < len(lines) else ""

            part_number = ""
            part_candidate_1 = lines[i - 2].strip()
            part_candidate_2 = lines[i - 3].strip()

            if part_number_pattern.match(part_candidate_1):
                part_number = part_candidate_1
            elif part_number_pattern.match(part_candidate_2):
                part_number = part_candidate_2

            bin_value = ""
            for j in range(i - 1, i - 10, -1):
                if "PICK" in lines[j]:
                    pick_line = lines[j].strip()

                    if pick_line.startswith("PICK ") and len(pick_line.split()) > 1:
                        bin_text = pick_line.split(" ", 1)[1]
                        bin_value = bin_text.split(',')[0].split()[0]

                    elif pick_line.strip() == "PICK" and j + 1 < len(lines):
                        bin_line = lines[j + 1].strip()
                        bin_value = bin_line.split(',')[0].split()[0]

                    elif pick_line.startswith("PICK") and len(pick_line) > 4 and j + 1 < len(lines):
                        pick_suffix = pick_line[4:].strip()
                        next_line = lines[j + 1].strip()
                        bin_value = (pick_suffix + next_line).split(',')[0].split()[0]
                    break

            if bin_value and part_number:
                entries.append({
                    "PICK": bin_value,
                    "Part #": part_number,
                    "Qty Committed": committed_qty
                })

    def sort_key(entry):
        try:
            return int(entry["PICK"])
        except:
            return entry["PICK"]

    sorted_entries = sorted(entries, key=sort_key)

    if sorted_entries:
        df = pd.DataFrame(sorted_entries)
        st.success("Extracted and sorted successfully!")
        st.dataframe(df, use_container_width=True)

        class PDFTable(FPDF):
            def header(self):
                self.set_font("Arial", "B", 12)
                self.cell(0, 10, "Pick Ticket Summary", 0, 1, "C")

            def table(self, data):
                self.set_font("Arial", "B", 10)
                col_widths = [30, 80, 40]
                headers = ["PICK", "Part #", "Qty Committed"]

                for i, header in enumerate(headers):
                    self.cell(col_widths[i], 10, header, border=1)
                self.ln()

                self.set_font("Arial", "", 10)
                for _, row in data.iterrows():
                    self.cell(col_widths[0], 10, str(row["PICK"]), border=1)
                    self.cell(col_widths[1], 10, str(row["Part #"]), border=1)
                    self.cell(col_widths[2], 10, str(row["Qty Committed"]), border=1)
                    self.ln()

        pdf = PDFTable()
        pdf.add_page()
        pdf.table(df)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            pdf.output(tmpfile.name)
            with open(tmpfile.name, "rb") as f:
                st.download_button("📥 Download Results as PDF", f.read(), file_name="pick_ticket_summary.pdf", mime="application/pdf")

    else:
        st.warning("No valid entries found in the PDF.")
