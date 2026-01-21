"""
DAX & M MIGRATION TOOL
Version: 2.1.4
Description: Unified Tab-based app. 
Optimized for DAX Studio clipboard pastes and Power Query source injections.
"""

import streamlit as st
import pandas as pd
from io import StringIO
import re

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Migration Pro v2.1.4", layout="wide")

st.title("🔄 Power BI Migration Toolkit")
st.caption("Version 2.1.4 | Optimized for DAX Studio Clipboard & M-Injections")

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

if df_map is not None:
    st.sidebar.success(f"✅ Mapping Active ({len(df_map)} rows)")
else:
    st.sidebar.info("Awaiting CSV upload...")

# --- SHARED DAX REPLACER ENGINE (v1.9.1 Logic) ---
def apply_dax_mapping(text, mapping_df):
    if not text or mapping_df is None: 
        return text
    
    all_mappings = []
    for _, row in mapping_df.iterrows():
        ot, of = str(row.get('OldTable','')), str(row.get('OldField',''))
        nt, nf = str(row.get('NewTable','')), str(row.get('NewField',''))
        
        # Standardized New Reference
        new = f"'{nt}'[{nf}]" if nt and nf else f"'{nt}'" if nt else f"[{nf}]"
        
        if ot and of:
            # Match both 'Table'[Field] and Table[Field]
            all_mappings.append({'old': f"'{ot}'[{of}]", 'new': new, 'len': len(f"'{ot}'[{of}]")})
            all_mappings.append({'old': f"{ot}[{of}]", 'new': new, 'len': len(f"{ot}[{of}]")})
        elif ot:
            all_mappings.append({'old': f"'{ot}'", 'new': f"'{nt}'", 'len': len(f"'{ot}'")})
            all_mappings.append({'old': ot, 'new': f"'{nt}'", 'len': len(ot)})
        elif of:
            all_mappings.append({'old': f"[{of}]", 'new': f"[{nf}]", 'len': len(f"[{of}]")})
    
    # Process longest strings first to prevent partial replacement errors
    for item in sorted(all_mappings, key=lambda x: x['len'], reverse=True):
        text = text.replace(item['old'], item['new'])
    return text

# --- TABS SETUP ---
tabs = st.tabs(["🚀 Dax Measure Converter", "🛠️ M-Script Step Injector", "📋 DAX Measure Definer", "🔍 Mapping Previewer"])

# --- TAB 1: DAX MEASURE CONVERTER ---
with tabs[0]:
    st.subheader("Global DAX Find-and-Replace")
    st.caption("Replaces table/field references throughout any pasted DAX block.")
    source_text = st.text_area("Paste DAX Script", height=350, key="dax_conv")
    if source_text and df_map is not None:
        converted = apply_dax_mapping(source_text, df_map)
        st.code(converted, language='sql')
        st.download_button("Download DAX", converted, "converted_dax.txt")

# --- TAB 2: M-SCRIPT STEP INJECTOR ---
with tabs[1]:
    st.subheader("M-Script Source Step Injector")
    st.caption("Injects Table.RenameColumns after the first step (Source/Navigation).")
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
    st.subheader("Bulk Measure Definer (INFO.MEASURES)")
    st.markdown("Optimized for **DAX Studio** (Copy with Headers).")
    
    target_table = st.text_input("New Table Assignment", value="Measures_Table")
    measures_input = st.text_area("Paste FULL INFO.MEASURES() results here", height=300)
    
    if measures_input and df_map is not None:
        try:
            # Cleanup common clipboard artifacts
            cleaned_input = measures_input.replace('\r\n', '\n').strip()
            
            # Use Tab as primary separator (Standard for DAX Studio)
            m_df = pd.read_csv(StringIO(cleaned_input), sep='\t', engine='python')
            
            # Fallback for CSV format if Tab fails
            if len(m_df.columns) <= 1:
                m_df = pd.read_csv(StringIO(cleaned_input), sep=None, engine='python')

            # Clean headers: remove [ ] and whitespace
            m_df.columns = [c.replace('[', '').replace(']', '').strip() for c in m_df.columns]
            
            # Flexible keyword detection
            name_col = next((c for c in m_df.columns if 'name' in c.lower()), None)
            expr_col = next((c for c in m_df.columns if 'expression' in c.lower() or 'formula' in c.lower()), None)
            
            if name_col and expr_col:
                define_lines = ["DEFINE"]
                count = 0
                
                for _, row in m_df.iterrows():
                    m_name = str(row[name_col]).strip()
                    m_expr = str(row[expr_col]).strip()
                    
                    # Unwrap expressions often quoted by export tools
                    if m_expr.startswith('"') and m_expr.endswith('"'):
                        m_expr = m_expr[1:-1].replace('""', '"')
                    
                    if not m_expr or m_expr.lower() in ['nan', 'null'] or m_expr == "":
                        continue
                        
                    mapped_expr = apply_dax_mapping(m_expr, df_map)
                    define_lines.append(f"MEASURE '{target_table}'[{m_name}] = \n    {mapped_expr}\n")
                    count += 1
                
                define_lines.append("EVALUATE")
                define_lines.append(f"ROW(\"Status\", \"{count} Measures Generated\")")
                
                if count > 0:
                    final_script = "\n".join(define_lines)
                    st.success(f"✅ Generated {count} measure definitions.")
                    st.code(final_script, language='sql')
                    st.download_button("Download DEFINE Script", final_script, "bulk_define.dax")
                else:
                    st.warning("Found columns, but no valid measure formulas were found in the data rows.")
            else:
                st.error(f"Missing columns. Found: {list(m_df.columns)}")
                st.info("Tip: In DAX Studio, use 'Copy with Headers' (Ctrl+Shift+C).")

        except Exception as e:
            st.error(f"Clipboard Parsing Error: {e}")

# --- TAB 4: MAPPING PREVIEWER ---
with tabs[3]:
    st.subheader("Current Mapping File Preview")
    if df_map is not None:
        st.dataframe(df_map, use_container_width=True)
    else:
        st.info("Upload a CSV in the sidebar to see the preview.")