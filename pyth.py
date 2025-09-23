# app.py
import streamlit as st
import pandas as pd
import pdfplumber
import openpyxl
import re
import os
from io import BytesIO

# To parse .docx files, you need to install python-docx
try:
    import docx
except ImportError:
    st.error("The 'python-docx' library is not installed. Please install it by running: pip install python-docx")
    st.stop()

# === Branding & Page Config ===
st.set_page_config(page_title="Regulatory Compliance & Safety Tool", layout="wide")

# --- FINAL, CORRECTED LOGO AND TITLE LAYOUT ---
col1, col2 = st.columns([1, 4])

with col1:
    def find_logo_path(possible_names=["logo.jpg", "logo.png"]):
        """Tries to find the logo file in the current directory."""
        for name in possible_names:
            if os.path.exists(name):
                return name
        return None

    logo_path = find_logo_path()
    if logo_path:
        try:
            st.image(logo_path, width=150)
        except Exception as e:
            st.error(f"Error loading logo: {e}")
    else:
        st.warning("Logo not found. Place a file named 'logo.png' or 'logo.jpg' in the same directory.")

with col2:
    st.title("Regulatory Compliance & Safety Verification Tool")

# === Advanced CSS for Styling ===
st.markdown("""
<style>
.card{background:#f9f9f9; border-radius:10px; padding:15px; margin-bottom:10px; border-left: 5px solid #0056b3;}
.small-muted{color:#777; font-size:0.95em;}
.result-pass{color:#1e9f50; font-weight:700;}
.result-fail{color:#c43a31; font-weight:700;}
.main .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# === Session State Initialization ===
def init_session_state():
    state_defaults = {
        "reports_verified": 0,
        "requirements_generated": 0,
        "found_component": None,
        "component_db": pd.DataFrame(columns=['Part Number', 'Product Category', 'Manufacturer', 'Qualification', 'Voltage Rating DC', 'Dielectric', 'Capacitance', 'Tolerance'])
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()

# --- UNIFIED HELPER FUNCTIONS (for data parsing and display) ---
def parse_uploaded_file(uploaded_file):
    """Parses various file types to extract text and data."""
    file_type = uploaded_file.type
    content = None
    file_bytes = BytesIO(uploaded_file.getvalue())

    if file_type == "application/pdf":
        with pdfplumber.open(file_bytes) as pdf:
            content = " ".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file_type == "text/plain":
        content = file_bytes.getvalue().decode("utf-8")
    elif file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        content = parse_xlsx(file_bytes)
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        content = parse_docx(file_bytes)
    else:
        st.error(f"Unsupported file type: {file_type}")
        return None
    return content

def parse_docx(file_bytes):
    """Parses a .docx file and returns its text content."""
    try:
        doc = docx.Document(file_bytes)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        st.error(f"An error occurred while parsing the DOCX file: {e}")
        return None

def parse_xlsx(file_bytes):
    """Parses a .xlsx file and returns its text content."""
    try:
        workbook = openpyxl.load_workbook(file_bytes)
        full_text = []
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            full_text.append(f"--- Sheet: {sheet_name} ---")
            for row in sheet.iter_rows():
                row_text = [str(cell.value) if cell.value is not None else "" for cell in row]
                full_text.append("\t".join(row_text))
        return "\n".join(full_text)
    except Exception as e:
        st.error(f"An error occurred while parsing the XLSX file: {e}")
        return None

def extract_test_data(text_content):
    """
    Extracts individual test cases and their results from a continuous text block.
    """
    extracted_data = []
    
    # This regex handles the formats from the images: `[number]: [Test Description] -> [Result]` or `[number]: [Test Description] "FAIL"`
    # It is designed to be flexible.
    test_pattern = re.compile(
        r"(\d+): (.*?)(?:->| |)(PASS|FAIL|N/A|COMPLETE|SUCCESS|FAILURE)",
        re.IGNORECASE
    )

    matches = test_pattern.findall(text_content)

    if not matches:
        # Fallback to a simpler line-by-line search for results if the primary regex fails.
        lines = text_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            result = None
            test_description = line
            if "FAIL" in line.upper() or "FAILURE" in line.upper():
                result = "FAIL"
            elif "PASS" in line.upper() or "SUCCESS" in line.upper():
                result = "PASS"
            elif "N/A" in line.upper() or "NA" in line.upper():
                result = "N/A"

            if result:
                test_description = re.sub(r'(PASS|FAIL|N/A|COMPLETE|SUCCESS|FAILURE)', '', test_description, flags=re.IGNORECASE).strip()
                extracted_data.append({
                    "Test Description": test_description,
                    "Result": result
                })
    else:
        for match in matches:
            test_id, description, result = match
            extracted_data.append({
                "Test Description": f"{test_id}: {description.strip()}",
                "Result": result.upper()
            })

    return extracted_data


def display_test_card(test_data, color):
    """Displays a single test case in a stylish card format."""
    st.markdown(f"""
    <div class="card" style="border-left: 5px solid {color};">
        <p><strong>Test:</strong> {test_data.get('Test Description', 'N/A')}</p>
        <p><strong>Result:</strong> <span style="color:{color}; font-weight: bold;">{test_data.get('Result', 'N/A')}</span></p>
    </div>
    """, unsafe_allow_html=True)


# --- MAIN APPLICATION LOGIC ---
st.sidebar.header("Navigation", anchor=False)
option = st.sidebar.radio("Select a Module", ("Report Verification", "Regulatory Requirements", "Component Information", "Dashboard & Analytics"))


# --- Report Verification Module ---
if option == "Report Verification":
    st.subheader("Automated Report Verification", anchor=False)
    st.caption("Upload a test report to automatically identify PASS/FAIL results.")
    uploaded_file = st.file_uploader("Choose a file (PDF, TXT, DOCX, XLSX)", type=["pdf", "txt", "docx", "xlsx"])

    if uploaded_file:
        st.session_state.reports_verified += 1
        with st.spinner("Parsing and analyzing the report..."):
            text_content = parse_uploaded_file(uploaded_file)

        if text_content:
            parsed_data = extract_test_data(text_content)

            if parsed_data:
                passed = [t for t in parsed_data if "PASS" in str(t.get("Result", "")).upper()]
                failed = [t for t in parsed_data if "FAIL" in str(t.get("Result", "")).upper()]
                others = [t for t in parsed_data if not ("PASS" in str(t.get("Result", "")).upper() or "FAIL" in str(t.get("Result", "")).upper())]

                st.markdown(f"### Found {len(passed)} Passed, {len(failed)} Failed, and {len(others)} Other items.")

                if failed:
                    st.error(f"Report analysis complete. {len(failed)} FAILED test cases found.")
                    with st.expander("🔴 Failed Cases", expanded=True):
                        for t in failed: display_test_card(t, '#c43a31')
                else:
                    st.success("Report analysis complete. No FAILED test cases found.")

                if passed:
                    with st.expander("✅ Passed Cases", expanded=False):
                        for t in passed: display_test_card(t, '#1e9f50')

                if others:
                    with st.expander("ℹ️ Other/Informational Items", expanded=False):
                        for t in others: display_test_card(t, '#808080')
            else:
                st.warning("No recognizable test data was extracted. Please ensure the report contains clear PASS/FAIL keywords or numbered lists.")
        else:
            st.error("Failed to extract content from the uploaded file.")