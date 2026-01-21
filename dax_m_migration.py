"""
DAX & M MIGRATION TOOL
Version: 2.1.5
Description: Unified Tab-based app. 
DAX Measure Definer now uses a dedicated CSV upload for stability.
"""

import streamlit as st
import pandas as pd
from io import StringIO
import re

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Migration Pro v2.1.5", layout="wide")

st.title("🔄 Power BI Migration Toolkit")
st.caption("Version 2.1.5 | CSV-Based Measure Definition")

# --- SIDEBAR: GLOBAL MAPPING UPLOAD ---
st.sidebar.header("1. Global Mapping Upload")
st.sidebar.markdown("Upload the file that defines your Table/Field renames.")
mapping_file = st.sidebar.file_uploader("Upload Mapping CSV", type="csv", key="global_map")

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

# --- SHARED DAX REPLACER ENGINE ---
def apply_dax_mapping(text, mapping_df):
    if not text or mapping_df is None: 
        return text
    
    all_mappings = []
    for _, row in mapping_df.iterrows():
        ot, of = str(row.get('OldTable','')), str(row.get('OldField',''))
        nt, nf = str(row.get('NewTable','')), str(row.get('NewField',''))
        
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

# --- TABS SETUP ---
tabs = st.tabs(["🚀 Dax Measure Converter", "🛠️ M-Script Step Injector", "📋 DAX Measure Definer", "🔍 Mapping Previewer"])

# --- TAB 1: DAX MEASURE CONVERTER ---
with tabs[0]:
    st.subheader("Global DAX Find-and-Replace")
    source_text = st.text_area("Paste DAX Script", height=350, key="dax_conv")
    if source_text and df_map is not None:
        converted = apply_dax_mapping(source_text, df_map)
        st.code(converted, language='sql')

# --- TAB 2: M-SCRIPT STEP INJECTOR ---
with tabs[1]:
    st.subheader("M-Script Source Step Injector")
    m_script = st.text_area("Paste M Script", height=350, key="m_inj")
    if m_script and df_map is not None:
        rename_list = [f'{{"{r.OldField}", "{r.NewField}"}}' for r in df_map.itertuples() if r.OldField and r.NewField]
        if rename_list:
            lines = m_script.split('\n')
            new_lines, first_step_name, injected = [], None, False
            step_pattern = r'^\s*(#"[^"]+"|\w+)\s*='
            for line in lines:
                new_lines.append(line)
                if not first_step_name:
                    match = re.search(step_pattern, line)
                    if match:
                        first_step_name = match.group(1)
                        new_lines.append(f'    RenamedColumns = Table.RenameColumns({first_step_name}, {{{", ".join(rename_list)}}}),')
                        injected = True
                        continue 
                if injected and first_step_name in line:
                    line = line.replace(f"({first_step_name})", "(RenamedColumns)").replace(f"{first_step_name},", "RenamedColumns,")
                    new_lines[-1] = line
            st.code("\n".join(new_lines), language='powerquery')

# --- TAB 3: DAX MEASURE DEFINER ---
with tabs[2]:
    st.subheader("Bulk Measure Definer (INFO.MEASURES CSV)")
    st.markdown("""
    **Instructions:**
    1. Export your `EVALUATE INFO.MEASURES()` results as a **CSV** from DAX Studio.
    2. Upload that CSV below.
    3. Ensure the CSV contains columns named **Name** and **Expression**.
    """)
    
    target_table = st.text_input("Assign to Table", value="Measures_Table")
    info_file = st.file_uploader("Upload INFO.MEASURES CSV", type="csv", key="info_measures_upload")
    
    if info_file and df_map is not None:
        try:
            # Read the uploaded INFO.MEASURES file
            info_df = pd.read_csv(info_file).fillna('')
            
            # Clean headers (strip brackets and spaces)
            info_df.columns = [c.replace('[', '').replace(']', '').strip() for c in info_df.columns]
            
            # Identify columns
            name_col = next((c for c in info_df.columns if 'name' in c.lower()), None)
            expr_col = next((c for c in info_df.columns if 'expression' in c.lower() or 'formula' in c.lower()), None)
            
            if name_col and expr_col:
                define_lines = ["DEFINE"]
                
                for _, row in info_df.iterrows():
                    m_name = str(row[name_col]).strip()
                    m_expr = str(row[expr_col]).strip()
                    
                    if not m_expr or m_expr.lower() in ['nan', 'null', '']:
                        continue
                        
                    mapped_expr = apply_dax_mapping(m_expr, df_map)
                    define_lines.append(f"MEASURE '{target_table}'[{m_name}] = \n    {mapped_expr}\n")
                
                define_lines.append("EVALUATE")
                define_lines.append(f"ROW(\"Status\", \"{len(define_lines)-3} Measures Defined\")")
                
                final_script = "\n".join(define_lines)
                st.success(f"✅ Generated {len(define_lines)-3} measure definitions.")
                st.code(final_script, language='sql')
                st.download_button("Download DEFINE Script", final_script, "bulk_define.dax")
            else:
                st.error(f"Required columns not found. Detected: {list(info_df.columns)}")
        except Exception as e:
            st.error(f"Error processing INFO.MEASURES file: {e}")
    elif info_file and df_map is None:
        st.warning("Please upload your Global Mapping CSV in the sidebar first.")

# --- TAB 4: MAPPING PREVIEWER ---
with tabs[3]:
    st.subheader("Current Global Mapping")
    if df_map is not None:
        st.dataframe(df_map, use_container_width=True)
    else:
        st.info("Upload a mapping file in the sidebar to see it here.")