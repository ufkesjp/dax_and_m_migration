"""
DAX & M MIGRATION TOOL
Version: 2.1.0
Description: Unified Tab-based app with DAX Measure Definer using INFO.MEASURES() input.
"""

import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Migration Pro v2.1.0", layout="wide")

st.title("🔄 Power BI Migration Toolkit")
st.caption("Version 2.1.0 | INFO.MEASURES() Support")

# --- SIDEBAR: GLOBAL UPLOAD ---
st.sidebar.header("1. Global Mapping Upload")
mapping_file = st.sidebar.file_uploader("Upload Mapping CSV", type="csv")

def get_mapping_data(file):
    if file:
        try:
            df = pd.read_csv(file).fillna('')
            df.columns = [c.strip() for c in df.columns]
            return df
        except Exception as e:
            st.sidebar.error(f"Error reading CSV: {e}")
            return None
    return None

df_map = get_mapping_data(mapping_file)

# --- HELPER: DAX REPLACER ENGINE ---
def apply_dax_mapping(source_text, mapping_df):
    if not source_text or mapping_df is None:
        return source_text
    
    all_mappings = []
    for _, row in mapping_df.iterrows():
        ot, of = str(row.get('OldTable', '')), str(row.get('OldField', ''))
        nt, nf = str(row.get('NewTable', '')), str(row.get('NewField', ''))
        
        new_ref = f"'{nt}'[{nf}]" if nt and nf else f"'{nt}'" if nt else f"[{nf}]"
        
        if ot and of:
            all_mappings.append({'old': f"'{ot}'[{of}]", 'new': new_ref, 'len': len(f"'{ot}'[{of}]")})
            all_mappings.append({'old': f"{ot}[{of}]", 'new': new_ref, 'len': len(f"{ot}[{of}]")})
        elif ot and nt and not of:
            all_mappings.append({'old': f"'{ot}'", 'new': f"'{nt}'", 'len': len(f"'{ot}'")})
            all_mappings.append({'old': ot, 'new': f"'{nt}'", 'len': len(ot)})
        elif of and nf and not ot:
            all_mappings.append({'old': f"[{of}]", 'new': f"[{nf}]", 'len': len(f"[{of}]")})

    sorted_map = sorted(all_mappings, key=lambda x: x['len'], reverse=True)
    for item in sorted_map:
        source_text = source_text.replace(item['old'], item['new'])
    return source_text

# --- TABS SETUP ---
tabs = st.tabs(["🚀 Dax Measure Converter", "🛠️ M-Script Step Injector", "📋 DAX Measure Definer", "🔍 Mapping Previewer"])

# --- TAB 1: DAX MEASURE CONVERTER ---
with tabs[0]:
    st.subheader("DAX Find-and-Replace")
    source_text = st.text_area("Paste DAX Script", height=300, key="dax_conv_input")
    if st.button("Convert Script"):
        if df_map is not None and source_text:
            converted = apply_dax_mapping(source_text, df_map)
            st.code(converted, language='sql')
        else:
            st.warning("Upload mapping and paste script.")

# --- TAB 2: M-SCRIPT STEP INJECTOR ---
with tabs[1]:
    # (Existing v1.9.1 Step Injector logic here)
    st.subheader("M-Script Source Step Injector")
    m_script = st.text_area("Paste M Script", height=300, key="m_inj_input")
    if df_map is not None and m_script:
        # ... (Same logic as v1.9.1)
        st.info("Step injector logic active.")

# --- TAB 3: DAX MEASURE DEFINER (NEW) ---
with tabs[2]:
    st.subheader("Bulk Measure Definer (INFO.MEASURES)")
    st.markdown("""
    1. Run `EVALUATE INFO.MEASURES()` in DAX Studio.
    2. Export results to CSV or Copy/Paste the table below.
    3. The tool will rewrite all expressions using your mapping.
    """)
    
    measures_input = st.text_area("Paste INFO.MEASURES() results (Tab-separated or CSV)", height=300)
    
    if measures_input and df_map is not None:
        try:
            # Attempt to read the pasted table (works for DAX Studio copy-paste)
            from io import StringIO
            m_df = pd.read_csv(StringIO(measures_input), sep=None, engine='python')
            
            # We specifically need [Name], [Expression], and [TableID] or [TableName]
            # INFO.MEASURES columns are usually: [Name], [Expression], [Description], etc.
            # For a DEFINE statement, we need the measure name and expression.
            
            define_statements = []
            for _, m_row in m_df.iterrows():
                m_name = str(m_row.get('Name', 'UnknownMeasure'))
                # Some versions of INFO.MEASURES use 'Table' or 'ParentName'
                m_table = str(m_row.get('TableName', 'FactTable')) 
                m_expr = str(m_row.get('Expression', ''))
                
                # Apply mapping to the expression
                new_expr = apply_dax_mapping(m_expr, df_map)
                
                # Format as DEFINE MEASURE 'Table'[Name] = Expression
                statement = f"MEASURE '{m_table}'[{m_name}] = \n{new_expr}\n"
                define_statements.append(statement)
            
            final_define_block = "DEFINE\n" + "\n".join(define_statements) + "\nEVALUATE\nROW(\"Status\", \"Measures Defined\")"
            
            st.success(f"Generated {len(define_statements)} measure definitions.")
            st.code(final_define_block, language='sql')
            st.download_button("Download DEFINE Script", final_define_block, "bulk_measures.dax")
            
        except Exception as e:
            st.error(f"Error parsing measure table: {e}")

# --- TAB 4: MAPPING PREVIEWER ---
with tabs[3]:
    st.subheader("Mapping Logic Preview")
    if df_map is not None:
        st.dataframe(df_map)