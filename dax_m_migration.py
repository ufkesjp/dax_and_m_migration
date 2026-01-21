"""
DAX & M MIGRATION TOOL
Version: 2.2.0
Description: Unified Tab-based app. 
Added optional mapping toggle for the DAX Measure Definer.
"""

import streamlit as st
import pandas as pd
from io import StringIO
import re

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Migration Pro v2.2.0", layout="wide")

st.title("🔄 Power BI Migration Toolkit")
st.caption("Version 2.2.0 | Optional Mapping Logic")

# --- SIDEBAR: GLOBAL MAPPING UPLOAD ---
st.sidebar.header("1. Global Mapping Upload")
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
    elif source_text:
        st.warning("Upload mapping in sidebar to perform conversion.")

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
    
    col1, col2 = st.columns([2, 1])
    with col1:
        target_table = st.text_input("Assign to Table in New Model", value="Measures_Table")
    with col2:
        st.write("##") # Spacer
        use_mapping = st.checkbox("Apply Global Mapping", value=True, help="If unchecked, measures will be defined exactly as they appear in the CSV.")
    
    info_file = st.file_uploader("Upload INFO.MEASURES CSV", type="csv", key="info_measures_upload")
    
    if info_file:
        try:
            info_df = pd.read_csv(info_file).fillna('')
            info_df.columns = [c.replace('[', '').replace(']', '').strip() for c in info_df.columns]
            
            name_col = next((c for c in info_df.columns if 'name' in c.lower()), None)
            expr_col = next((c for c in info_df.columns if 'expression' in c.lower() or 'formula' in c.lower()), None)
            
            if name_col and expr_col:
                define_lines = ["DEFINE"]
                
                # Check if mapping is requested but file is missing
                if use_mapping and df_map is None:
                    st.error("Mapping is enabled, but no Global Mapping CSV was uploaded in the sidebar.")
                else:
                    for _, row in info_df.iterrows():
                        m_name = str(row[name_col]).strip()
                        m_expr = str(row[expr_col]).strip()
                        
                        if not m_expr or m_expr.lower() in ['nan', 'null', '']:
                            continue
                        
                        # Apply mapping only if the toggle is ON
                        final_expr = apply_dax_mapping(m_expr, df_map) if use_mapping else m_expr
                        
                        define_lines.append(f"MEASURE '{target_table}'[{m_name}] = \n    {final_expr}\n")
                    
                    define_lines.append("EVALUATE")
                    define_lines.append(f"ROW(\"Status\", \"{len(define_lines)-3} Measures Defined\")")
                    
                    final_script = "\n".join(define_lines)
                    st.success(f"✅ Generated {len(define_lines)-3} measure definitions (Mapping: {'ON' if use_mapping else 'OFF'}).")
                    st.code(final_script, language='sql')
                    st.download_button("Download DEFINE Script", final_script, "bulk_define.dax")
            else:
                st.error(f"Required columns not found. Detected: {list(info_df.columns)}")
        except Exception as e:
            st.error(f"Error processing INFO.MEASURES file: {e}")

# --- TAB 4: MAPPING PREVIEWER ---
with tabs[3]:
    st.subheader("Current Global Mapping")
    if df_map is not None:
        st.dataframe(df_map, use_container_width=True)
    else:
        st.info("Upload a mapping file in the sidebar to see it here.")