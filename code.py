# app.py
import streamlit as st
import pandas as pd
import pdfplumber
import openpyxl
import re
import os

# To parse .docx files, you need to install python-docx
try:
    import docx
except ImportError:
    st.error("The 'python-docx' library is not installed. Please install it by running: pip install python-docx")
    st.stop()

# === Branding & Page Config ===
st.set_page_config(page_title="Regulatory Compliance & Safety Tool", layout="wide")

# --- FINAL, CORRECTED LOGO AND TITLE LAYOUT ---
col1, col2 = st.columns([1, 4])  # Create two columns, the second being wider

with col1:
    # This code finds and displays the logo in the first (left) column.
    def find_logo_path(possible_names=["logo.jpg", "logo.png", "logo.png.jpg"]):
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
        st.warning("Logo not found.")

with col2:
    # This code displays the title in the second (right) column.
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
        "reports_verified": 0, "requirements_generated": 0, "found_component": None,
        "component_db": pd.DataFrame()
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()


# === UPGRADED KNOWLEDGE BASE with Detailed Procedures ===
TEST_CASE_KNOWLEDGE_BASE = {
    "water ingress": {
        "name": "Water Ingress Protection Test (IPX7)",
        "standard": "Based on ISO 20653 / IEC 60529",
        "description": "This test simulates the temporary immersion of the device in water to ensure no harmful quantity of water can enter the enclosure.",
        "procedure": [
            "Ensure the Device Under Test (DUT) is in a non-operational state and at ambient temperature.",
            "Submerge the DUT completely in a water tank.",
            "The lowest point of the DUT should be 1 meter below the surface of the water.",
            "The highest point of the DUT should be at least 0.15 meters below the surface.",
            "Maintain the immersion for the specified duration.",
            "After the test, remove the DUT, dry the exterior, and inspect the interior for any signs of water ingress.",
            "Conduct a functional check to ensure the device operates as expected."
        ],
        "parameters": {
            "Immersion Depth": "1 meter",
            "Test Duration": "30 minutes",
            "Water Temperature": "Ambient (within 5°C of DUT temperature)"
        },
        "equipment": ["Water Immersion Tank", "Depth Measurement Tool", "Stopwatch"]
    },
    "thermal shock": {
        "name": "Thermal Shock Test",
        "standard": "Based on ISO 16750-4",
        "description": "This test simulates the stress placed on electronic components when moving between extreme temperatures, such as a car being washed in winter.",
        "procedure": [
            "Set up a dual-chamber thermal shock system (hot and cold chambers).",
            "Place the DUT in the cold chamber and allow it to stabilize at the minimum temperature.",
            "Rapidly transfer the DUT to the hot chamber (transfer time should be less than 1 minute).",
            "Allow the DUT to stabilize at the maximum temperature.",
            "This completes one cycle. Repeat for the specified number of cycles.",
            "After the final cycle, allow the DUT to return to room temperature and perform a full functional and visual inspection."
        ],
        "parameters": {
            "Minimum Temperature": "-40°C",
            "Maximum Temperature": "+85°C",
            "Soak Time per Chamber": "1 hour",
            "Number of Cycles": "100 cycles"
        },
        "equipment": ["Dual-Chamber Thermal Shock System"]
    },
     "humidity": {
        "name": "Steady-State Damp Heat Test 🌡️",
        "standard": "Based on IEC 60068-2-78",
        "description": "Evaluates the reliability of components in high humidity, high-temperature environments. It's used to detect failures caused by moisture absorption and corrosion.",
        "procedure": [
            "Place the unpowered DUT inside the climatic chamber.",
            "Ramp up the temperature and humidity to the specified levels.",
            "Maintain these conditions for the specified duration (dwell time).",
            "During the test, the DUT may be powered or unpowered as per the test plan.",
            "After the dwell time, ramp down to ambient conditions.",
            "Perform a full functional and visual inspection for corrosion or performance degradation."
        ],
        "parameters": {
            "Temperature": "+40°C",
            "Relative Humidity": "93% RH",
            "Test Duration": "96 hours (4 days)"
        },
        "equipment": ["Climatic Chamber", "Humidity Sensor"]
    },
    "vibration": {
        "name": "Sinusoidal Vibration Test",
        "standard": "Based on IEC 60068-2-6",
        "description": "This test simulates the vibrations that a component might experience during its operational life due to engine harmonics or rough road conditions.",
        "procedure": [
            "Securely mount the DUT onto the vibration shaker table in its intended orientation.",
            "Sweep the frequency range from the minimum to the maximum value and back down.",
            "Perform the sweep on all three axes (X, Y, and Z).",
            "Maintain the specified G-force (acceleration) throughout the test.",
            "During the test, monitor the DUT for any intermittent failures or resonant frequencies.",
            "After the test, perform a full functional and visual inspection for any damage."
        ],
        "parameters": {
            "Frequency Range": "10 Hz to 500 Hz",
            "Acceleration": "5g (49 m/s²)",
            "Sweep Rate": "1 octave/minute",
            "Duration per Axis": "2 hours"
        },
        "equipment": ["Electrodynamic Shaker Table", "Vibration Controller", "Accelerometers"]
    },
    "mechanical shock": {
        "name": "Mechanical Shock Test 🔧",
        "standard": "Based on IEC 60068-2-27",
        "description": "Tests the product's ability to withstand sudden, abrupt accelerations or decelerations, simulating events like being dropped or impacts during transit.",
        "procedure": [
            "Securely mount the DUT to the shock test machine.",
            "Apply a specified number of shocks along one axis.",
            "The shock should follow a specific waveform (e.g., half-sine).",
            "Repeat the process for both positive and negative directions on all three axes (X, Y, Z).",
            "After all shocks are applied, perform a full functional and visual inspection for physical damage or loss of function."
        ],
        "parameters": {
            "Peak Acceleration": "50g",
            "Pulse Duration": "11 ms",
            "Waveform": "Half-sine",
            "Number of Shocks per Axis/Direction": "3"
        },
        "equipment": ["Mechanical Shock Test Machine", "Accelerometers", "Data Acquisition System"]
    },
    "short circuit": {
        "name": "External Short Circuit Protection",
        "standard": "Based on AIS-156 / IEC 62133-2",
        "description": "Verifies the safety performance of the battery or system when an external short circuit is applied.",
        "procedure": [
            "Ensure the DUT is fully charged.",
            "Connect the positive and negative terminals of the DUT with a copper wire or load with a resistance of less than 100 mΩ.",
            "Maintain the short circuit condition for the specified duration or until the protection circuit interrupts the current.",
            "Monitor the DUT for any hazardous events like fire, explosion, or casing rupture.",
            "Measure the case temperature during the test; it should not exceed the specified limit.",
            "After the test, the DUT should not show signs of fire or explosion."
        ],
        "parameters": {
            "Short Circuit Resistance": "< 100 mΩ",
            "Test Temperature": "55°C ± 5°C",
            "Observation Period": "1 hour after the event"
        },
        "equipment": ["High-Current Contactor", "Low-Resistance Load", "Thermocouples", "Safety Enclosure"]
    },
    "esd": {
        "name": "Electrostatic Discharge (ESD) Immunity Test ⚡",
        "standard": "Based on IEC 61000-4-2",
        "description": "Verifies the device's immunity to electrostatic discharges from a human operator, which can cause damage to electronic components.",
        "procedure": [
            "Place the DUT on a non-conductive table over a ground reference plane.",
            "Apply discharges to points and surfaces that are normally accessible during operation.",
            "Perform Contact Discharges: Apply the ESD generator tip directly to conductive surfaces.",
            "Perform Air Discharges: Bring the charged tip close to insulating surfaces until a spark occurs.",
            "Apply discharges to both positive and negative polarities at increasing voltage levels.",
            "Monitor the DUT for any operational upset, degradation, or damage."
        ],
        "parameters": {
            "Contact Discharge Levels": "±2kV, ±4kV",
            "Air Discharge Levels": "±2kV, ±4kV, ±8kV",
            "Number of Discharges per Point": "10"
        },
        "equipment": ["ESD Generator (ESD Gun)", "Ground Reference Plane", "Test Setup Table"]
    }
}

# --- COMPLETE, UNIFIED, and FULLY POPULATED Component Database ---
UNIFIED_COMPONENT_DB = {
    "cga3e1x7r1e105k080ac": {"Manufacturer":"TDK", "Product Category":"Multilayer Ceramic Capacitors MLCC - SMD/SMT", "RoHS":"Yes", "Capacitance":"1 uF", "Voltage Rating DC":"25 VDC", "Dielectric":"X7R", "Tolerance":"10 %", "Case Code - in":"0603", "Case Code - mm":"1608", "Termination Style":"SMD/SMT", "Termination":"Standard", "Minimum Operating Temperature":"-55 C", "Maximum Operating Temperature":"+125 C", "Length":"1.6 mm", "Width":"0.8 mm", "Height":"0.8 mm", "Product":"Automotive MLCCs", "Qualification":"AEC-Q200"},
    "spc560p50l3": {"Manufacturer": "STMicroelectronics", "Product Category": "MCU", "RoHS": "Yes", "CPU Core": "PowerPC e200z0h", "Frequency": "64 MHz", "RAM Size": "48KB", "Flash Size": "512KB", "Package": "LQFP-100", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q100"},
    "tja1051t": {"Manufacturer": "NXP", "Product Category": "CAN Transceiver", "RoHS": "Yes", "Data Rate": "1 Mbps", "Voltage Rating DC": "5V", "Package": "SO-8", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q100"},
    "tle4275g": {"Manufacturer": "Infineon", "Product Category": "LDO Regulator", "RoHS": "Yes", "Output Voltage": "5V", "Output Current": "450mA", "Package": "TO-252-3", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "150 C", "Qualification": "AEC-Q100"},
    "fsbb30ch60f": {"Manufacturer": "onsemi", "Product Category": "IGBT Module", "RoHS": "Yes", "Voltage Rating DC": "600V", "Current": "30A", "Package": "SPM27-CC", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "150 C", "Product": "Smart Power Module"},
    "wslp2512r0100fe": {"Manufacturer": "Vishay", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "10 mOhm", "Power": "1W", "Tolerance": "1%", "Case Code - in": "2512", "Minimum Operating Temperature": "-65 C", "Maximum Operating Temperature": "170 C", "Qualification": "AEC-Q200"},
    "bq76952": {"Manufacturer": "Texas Instruments", "Product Category": "Battery Monitor", "RoHS": "Yes", "Cell Count": "3-16", "Interface": "I2C, SPI", "Package": "TQFP-48", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "85 C", "Qualification": "AEC-Q100"},
    "irfz44n": {"Manufacturer": "Infineon", "Product Category": "MOSFET", "RoHS": "Yes", "Vds": "55V", "Id": "49A", "Rds(on)": "17.5 mOhm", "Package": "TO-220AB", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "175 C"},
    "1n4007": {"Manufacturer": "Multiple", "Product Category": "Diode", "RoHS": "Yes", "VRRM": "1000V", "If(AV)": "1A", "Package": "DO-41", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "150 C"},
    # ... (the rest of your extensive component database is assumed to be here) ...
}


# ==============================================================================
# === NEW SECTION: Core Application Logic and Functions ===
# ==============================================================================

# --- Function to Parse Uploaded Bill of Materials (BOM) ---
def parse_bom(uploaded_file):
    """Reads an Excel or CSV file and extracts a list of component part numbers."""
    if uploaded_file is None:
        return None, "Please upload a BOM file."

    try:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            return None, "Unsupported file format. Please upload .xlsx or .csv"

        # Find the column that most likely contains the part numbers.
        # This makes the tool flexible to different BOM formats.
        part_number_col = None
        for col in df.columns:
            if 'part number' in col.lower() or 'mpn' in col.lower() or 'p/n' in col.lower():
                part_number_col = col
                break
        
        if not part_number_col:
             return None, "Could not automatically find a 'Part Number' or 'MPN' column in the file."
        
        # Clean up part numbers: convert to string, strip whitespace, and convert to lowercase
        part_numbers = df[part_number_col].dropna().astype(str).str.strip().str.lower().tolist()
        return part_numbers, f"Successfully parsed {len(part_numbers)} components from '{uploaded_file.name}'."
    
    except Exception as e:
        return None, f"An error occurred while parsing the file: {e}"

# --- Function to Verify Components Against the Database ---
def verify_components(part_numbers):
    """Checks a list of part numbers against the unified component database."""
    results = []
    if not part_numbers:
        return []

    for pn in part_numbers:
        component_data = UNIFIED_COMPONENT_DB.get(pn)
        if component_data:
            # Component found in our DB
            result = {
                "Part Number": pn,
                "Status": "Found",
                "Manufacturer": component_data.get("Manufacturer", "N/A"),
                "Category": component_data.get("Product Category", "N/A"),
                "AEC-Q Qualified": component_data.get("Qualification", "No")
            }
        else:
            # Component not in our DB
            result = {
                "Part Number": pn,
                "Status": "Not Found",
                "Manufacturer": "N/A",
                "Category": "N/A",
                "AEC-Q Qualified": "Unknown"
            }
        results.append(result)
    return results


# ==============================================================================
# === NEW SECTION: Streamlit User Interface Elements ===
# ==============================================================================

st.markdown("---")

# --- Create Tabs for Different Tool Functions ---
tab1, tab2 = st.tabs(["⚙️ BOM Component Verification", "📝 Test Requirement Generator"])

# --- Tab 1: BOM Component Verification ---
with tab1:
    st.header("Upload Bill of Materials (BOM)")
    st.markdown("Upload your BOM file (`.xlsx` or `.csv`) to check component compliance and qualification status against our database.")
    
    uploaded_bom_file = st.file_uploader("Choose a BOM file", type=["xlsx", "csv"], key="bom_uploader")

    if uploaded_bom_file:
        part_numbers, message = parse_bom(uploaded_bom_file)
        st.info(message)

        if part_numbers:
            with st.spinner("Verifying components..."):
                verification_results = verify_components(part_numbers)
                results_df = pd.DataFrame(verification_results)

                st.subheader("Verification Results")

                # --- Style the DataFrame for better readability ---
                def style_status(val):
                    if val == "Found":
                        color = 'green'
                    elif val == "Not Found":
                        color = 'red'
                    else:
                        color = 'black'
                    return f'color: {color}; font-weight: bold;'
                
                st.dataframe(results_df.style.applymap(style_status, subset=['Status']), use_container_width=True)

                # --- Summary Metrics ---
                found_count = len(results_df[results_df['Status'] == 'Found'])
                not_found_count = len(results_df[results_df['Status'] == 'Not Found'])
                aec_q_count = len(results_df[results_df['AEC-Q Qualified'].str.contains('AEC', na=False)])

                st.subheader("Summary")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Components", len(results_df))
                col2.metric("Components Found", f"{found_count}")
                col3.metric("AEC-Q Qualified", f"{aec_q_count}")


# --- Tab 2: Test Requirement Generator ---
with tab2:
    st.header("Generate Test Requirements")
    st.markdown("Select one or more tests from the list below to generate detailed procedures, parameters, and equipment lists.")

    # Create a list of test names for the multiselect widget
    test_options = list(TEST_CASE_KNOWLEDGE_BASE.keys())
    
    selected_tests = st.multiselect(
        "Choose tests to generate requirements for:",
        options=test_options,
        format_func=lambda x: TEST_CASE_KNOWLEDGE_BASE[x]['name'] # Show the full name in the dropdown
    )

    if st.button("Generate Requirements", type="primary"):
        if not selected_tests:
            st.warning("Please select at least one test.")
        else:
            st.subheader("Generated Test Requirement Documents")
            for test_key in selected_tests:
                test_data = TEST_CASE_KNOWLEDGE_BASE[test_key]
                
                st.markdown(f"""
                <div class="card">
                    <h4>{test_data['name']}</h4>
                    <p class="small-muted"><strong>Standard:</strong> {test_data['standard']}</p>
                    <p>{test_data['description']}</p>
                    
                    <h5>Procedure:</h5>
                    <ol>
                        {''.join([f'<li>{step}</li>' for step in test_data['procedure']])}
                    </ol>

                    <h5>Key Parameters:</h5>
                    <ul>
                         {''.join([f'<li><strong>{key}:</strong> {value}</li>' for key, value in test_data['parameters'].items()])}
                    </ul>

                     <h5>Required Equipment:</h5>
                    <p>{', '.join(test_data['equipment'])}</p>
                </div>
                """, unsafe_allow_html=True)