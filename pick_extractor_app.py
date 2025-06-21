import streamlit as st
import fitz  # PyMuPDF
import re
from fpdf import FPDF
import tempfile
import os

# === Parse Compact Line ===
def parse_single_line(line):
    parts = line.strip().split()
    if 'EA' not in parts or len(parts) < 7:
        return None
    try:
        ea_idx = parts.index('EA')
        part_no = parts[0]
        description = " ".join(parts[1:ea_idx])
        qty_ordered = int(parts[ea_idx + 1])
        qty_committed = int(parts[ea_idx + 2])
        qty_bo = int(parts[ea_idx + 3])
        return {
            "pick_display": "",  # will fill later
            "part_no": part_no,
            "description": description.strip(),
            "qty_ordered": qty_ordered,
            "qty_committed": qty_committed,
            "qty_bo": qty_bo
        }
    except:
        return None

# === Parse Multi-Line Block ===
def parse_multi_line(lines, i):
    try:
        pick_raw = lines[i + 1].strip()
        pick_display = re.match(r'(\d+)', pick_raw).group()

        part_line = lines[i + 2].strip()
        desc_line = lines[i + 3].strip()

        next_line = lines[i + 4].strip()
        if next_line == "EA":
            description = desc_line
            ea_index = i + 4
        else:
            description = f"{desc_line} {next_line}"
            ea_index = i + 5

        qty_line = lines[ea_index + 1:ea_index + 4]
        qtys = list(map(int, qty_line))

        return {
            "pick_display": pick_display,
            "part_no": part_line,
            "description": description.strip(),
            "qty_ordered": qtys[0],
            "qty_committed": qtys[1],
            "qty_bo": qtys[2]
        }, ea_index + 4
    except:
        return None, i + 1

# === PDF Generator ===
def generate_pdf(sorted_entries):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Sorted PICK Report", ln=True, align='C')
    pdf.ln(5)

    for entry in sorted_entries:
        pdf.cell(0, 10, f"PICK {entry['pick_display']}", ln=True)
        pdf.cell(0, 10, f"  Part #: {entry['part_no']}", ln=True)
        pdf.cell(0, 10, f"  Description: {entry['description']}", ln=True)
        pdf.cell(0, 10, f"  Qty Ordered: {entry['qty_ordered']}, Committed: {entry['qty_committed']}, B/O: {entry['qty_bo']}", ln=True)
        pdf.ln(2)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        pdf.output(tmpfile.name)
        return tmpfile.name

# === Streamlit App ===
st.set_page_config(page_title="PICK Ticket Extractor", layout="centered")
st.title("📦 PICK Ticket Extractor")

uploaded_file = st.file_uploader("Upload your Picking Ticket PDF", type=["pdf"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name

    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        lines += page.get_text().splitlines()

    entries = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == "PICK":
            block, new_i = parse_multi_line(lines, i)
            if block:
                entries.append(block)
            i = new_i
        else:
            single = parse_single_line(line)
            if single:
                match = re.search(r"PICK\s+(\d+)", "\n".join(lines[max(i - 3, 0):i + 1]))
                if match:
                    single["pick_display"] = match.group(1)
                entries.append(single)
            i += 1

    if entries:
        sorted_entries = sorted(entries, key=lambda x: int(re.match(r'\d+', x["pick_display"]).group()))
        st.success("✅ Entries successfully parsed and sorted!")

        for entry in sorted_entries:
            st.markdown(f"**PICK {entry['pick_display']}**")
            st.markdown(f"- Part #: `{entry['part_no']}`")
            st.markdown(f"- Description: {entry['description']}")
            st.markdown(f"- Qty Ordered: {entry['qty_ordered']}, Committed: {entry['qty_committed']}, B/O: {entry['qty_bo']}")
            st.markdown("---")

        pdf_file = generate_pdf(sorted_entries)
        with open(pdf_file, "rb") as f:
            st.download_button("📥 Download PDF", f, file_name="pick_summary.pdf", mime="application/pdf")
    else:
        st.error("🚫 No valid PICK entries found.")

