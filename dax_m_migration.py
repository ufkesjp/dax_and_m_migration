"""
DAX & M MIGRATION TOOL
Version: 1.3.0
Description: Converts DAX/M scripts using a CSV mapping file.
Schema: OldTable, OldField, NewTable, NewField
"""

import streamlit as st
import pandas as pd

# v1.3.0: Page config and versioning
st.set_page_config(page_title="DAX & M Migration v1.3", layout="wide")
st.title("🔄 DAX & M Migration")
st.caption("Version 1.3.0 | Stable")

# Initialize variables to prevent "unbound" errors
all_mappings = []

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("1. Configuration")
mapping_file = st.sidebar.file_uploader("Upload Mapping CSV", type="csv")
script_type = st.sidebar.selectbox("Script Type", ["DAX", "M (Power Query)"])

# --- CORE ENGINE: SYNTAX GENERATOR ---
def get_replacement_pairs(df, mode):
    """
    v1.1.0: Logic to generate correct syntax strings based on language mode.
    Handles Table+Field, Table-only, and Field-only scenarios.
    """
    pairs = []
    for _, row in df.iterrows():
        # Using .get() and stripping to handle whitespace/missing headers
        ot = str(row.get('OldTable', '')).strip()
        of = str(row.get('OldField', '')).strip()
        nt = str(row.get('NewTable', '')).strip()
        nf = str(row.get('NewField', '')).strip()

        # Handle 'nan' strings that result from empty pandas cells
        ot = "" if ot.lower() == 'nan' else ot
        of = "" if of.lower() == 'nan' else of
        nt = "" if nt.lower() == 'nan' else nt
        nf = "" if nf.lower() == 'nan' else nf

        # Scenario A: Table and Field both change
        if ot and of and nt and nf:
            old = f"'{ot}'[{of}]" if mode == "DAX" else f'#"{ot}"["{of}"]'
            new = f"'{nt}'[{nf}]" if mode == "DAX" else f'#"{nt}"["{nf}"]'
        
        # Scenario B: Table-wide rename
        elif ot and nt and not of and not nf:
            old = f"'{ot}'" if mode == "DAX" else f'#"{ot}"'
            new = f"'{nt}'" if mode == "DAX" else f'#"{nt}"'
            
        # Scenario C: Field-wide rename
        elif of and nf and not ot and not nt:
            old = f"[{of}]"
            new = f"[{nf}]"
        else:
            continue
            
        pairs.append({'Old Syntax': old, 'New Syntax': new, 'len': len(old)})
    return pairs

# --- PREVIEW SECTION ---
if mapping_file:
    try:
        # Load mapping and fill empty cells to avoid processing issues
        df_raw = pd.read_csv(mapping_file).fillna('')
        all_mappings = get_replacement_pairs(df_raw, script_type)
        
        if all_mappings:
            preview_df = pd.DataFrame(all_mappings).drop(columns=['len'])
            with st.expander("🔍 Mapping Preview & Search"):
                search_term = st.text_input("Filter mappings...", "")
                if search_term:
                    preview_df = preview_df[preview_df['Old Syntax'].str.contains(search_term, case=False)]
                st.dataframe(preview_df, use_container_width=True)
        else:
            st.warning("No valid mappings found. Please check your CSV headers.")
            
    except Exception as e:
        st.error(f"CSV Error: Ensure headers are OldTable, OldField, NewTable, NewField.")

# --- MAIN UI: SCRIPT CONVERSION ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Source Script")
    source_script = st.text_area("Paste Old Script", height=500, placeholder="Paste your DAX or M code here...")

with col2:
    st.subheader("Converted Output")
    # Only run if mapping file is uploaded, mappings generated, and script exists
    if mapping_file and all_mappings and source_script:
        # v1.0.0: Sort by length descending to prevent sub-string collision errors
        sorted_map = sorted(all_mappings, key=lambda x: x['len'], reverse=True)
        converted_script = source_script
        
        replace_count = 0
        for item in sorted_map:
            if item['Old Syntax'] in converted_script:
                count = converted_script.count(item['Old Syntax'])
                converted_script = converted_script.replace(item['Old Syntax'], item['New Syntax'])
                replace_count += count
        
        st.success(f"Conversion complete! Found and replaced {replace_count} references.")
        st.code(converted_script, language='sql' if script_type == "DAX" else 'powerquery')
        
        st.download_button(
            label="Download Script", 
            data=converted_script, 
            file_name=f"converted_{script_type.lower().replace(' ', '_')}.txt"
        )
    else:
        st.info("Upload CSV and paste script to begin.")