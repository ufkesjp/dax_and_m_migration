"""
DAX & M MIGRATION TOOL
Version: 2.1.1
Description: Unified Tab-based app with optimized DAX DEFINE block generation.
"""

import streamlit as st
import pandas as pd
from io import StringIO
import re

st.set_page_config(page_title="DAX Definer v2.1.1", layout="wide")

st.title("🔄 Power BI Migration Toolkit")

# --- SIDEBAR: GLOBAL UPLOAD ---
st.sidebar.header("1. Global Mapping Upload")
mapping_file = st.sidebar.file_uploader("Upload Mapping CSV", type="csv")

def get_mapping_data(file):
    if file:
        df = pd.read_csv(file).fillna('')
        df.columns = [c.strip() for c in df.columns]
        return df
    return None

df_map = get_mapping_data(mapping_file)

# --- SHARED DAX REPLACER ---
def apply_dax_mapping(text, mapping_df):
    if not text or mapping_df is None: return text
    all_mappings = []
    for _, row in mapping_df.iterrows():
        ot, of, nt, nf = str(row.get('OldTable','')), str(row.get('OldField','')), str(row.get('NewTable','')), str(row.get('NewField',''))
        new = f"'{nt}'[{nf}]" if nt and nf else f"'{nt}'" if nt else f"[{nf}]"
        if ot and of:
            all_mappings.append({'old': f"'{ot}'[{of}]", 'new': new, 'len': len(f"'{ot}'[{of}]")})
            all_mappings.append({'old': f"{ot}[{of}]", 'new': new, 'len': len(f"{ot}[{of}]")})
        elif ot:
            all_mappings.append({'old': f"'{ot}'", 'new': f"'{nt}'", 'len': len(f"'{ot}'")})
            all_mappings.append({'old': ot, 'new': f"'{nt}'", 'len': len(ot)})
        elif of:
            all_mappings.append({'old': f"[{of}]", 'new': f"[{nf}]", 'len': len(f"[{of}]")})
    
    for item in sorted(all_mappings, key=lambda x: x['len'], reverse=True):
        text = text.replace(item['old'], item['new'])
    return text

tabs = st.tabs(["🚀 Dax Measure Converter", "🛠️ M-Script Step Injector", "📋 DAX Measure Definer", "🔍 Mapping Previewer"])

# --- TAB 3: DAX MEASURE DEFINER ---
with tabs[2]:
    st.subheader("Bulk Measure Definer (INFO.MEASURES)")
    
    col_set, col_btn = st.columns([3, 1])
    with col_set:
        target_table = st.text_input("New Table Name", value="Fact_Sales", help="The table where these measures will be defined in the new model.")
    
    measures_input = st.text_area("Paste INFO.MEASURES() results here", height=300, placeholder="Name, Expression, TableID...")
    
    if measures_input and df_map is not None:
        try:
            # Use sep=None to auto-detect Tab vs CSV (DAX Studio usually provides Tabs)
            m_df = pd.read_csv(StringIO(measures_input), sep=None, engine='python')
            
            if 'Name' in m_df.columns and 'Expression' in m_df.columns:
                define_lines = ["DEFINE"]
                
                for _, m_row in m_df.iterrows():
                    m_name = str(m_row['Name'])
                    m_expr = str(m_row['Expression'])
                    
                    # Apply mapping to the formula
                    mapped_expr = apply_dax_mapping(m_expr, df_map)
                    
                    # Build the DEFINE MEASURE statement
                    define_lines.append(f"MEASURE '{target_table}'[{m_name}] = {mapped_expr}")
                
                define_lines.append("\nEVALUATE\nROW(\"Status\", \"Migration Complete\")")
                final_script = "\n".join(define_lines)
                
                st.success(f"Successfully generated DEFINE block for {len(m_df)} measures.")
                st.code(final_script, language='sql')
                st.download_button("Download .dax Script", final_script, "bulk_define_measures.dax")
            else:
                st.error("Input table must contain 'Name' and 'Expression' columns.")
        except Exception as e:
            st.error(f"Error parsing table: {e}")