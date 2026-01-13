"""
DAX & M MIGRATION TOOL
Version: 1.9.1
Description: Global converter now detects M and DAX patterns simultaneously when in M mode.
"""

import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Migration Tool v1.9.1", layout="wide")

st.title("🔄 Power BI Migration Toolkit")
st.caption("Version 1.9.1 | M & Embedded DAX Support")

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

# --- TABS SETUP ---
tab1, tab2, tab3 = st.tabs(["🚀 DAX and M Converter", "🛠️ Add Rename Step to M", "🔍 Mapping Previewer"])

# --- TAB 1: FULL SCRIPT CONVERTER ---
with tab1:
    st.subheader("Global Find-and-Replace")
    script_type = st.radio("Target Syntax Mode:", ["DAX", "M (Power Query)"], horizontal=True, key="full_mode")
    
    col1, col2 = st.columns(2)
    with col1:
        source_text = st.text_area("Paste Old Script", height=400, key="full_conv_input")
    
    with col2:
        if df_map is not None and source_text:
            all_mappings = []
            for _, row in df_map.iterrows():
                ot, of = str(row.get('OldTable', '')), str(row.get('OldField', ''))
                nt, nf = str(row.get('NewTable', '')), str(row.get('NewField', ''))
                
                if ot and of and nt and nf:
                    # Define what the NEW reference should look like based on mode
                    new_m = f'#"{nt}"["{nf}"]'
                    new_dax = f"'{nt}'[{nf}]"
                    
                    # Logic: If in M Mode, we must search for BOTH M and DAX patterns
                    # If in DAX Mode, we only search for DAX patterns
                    
                    # 1. M Patterns
                    if script_type == "M (Power Query)":
                        m_old = f'#"{ot}"["{of}"]'
                        all_mappings.append({'old': m_old, 'new': new_m, 'len': len(m_old)})
                    
                    # 2. DAX Patterns (Quoted)
                    dax_quoted_old = f"'{ot}'[{of}]"
                    target_dax = new_dax if script_type == "DAX" else new_m # Ensure we don't mix syntaxes in output
                    all_mappings.append({'old': dax_quoted_old, 'new': target_dax, 'len': len(dax_quoted_old)})
                    
                    # 3. DAX Patterns (Unquoted)
                    dax_unquoted_old = f"{ot}[{of}]"
                    all_mappings.append({'old': dax_unquoted_old, 'new': target_dax, 'len': len(dax_unquoted_old)})
                
                # Table-Only Logic
                elif ot and nt and not of:
                    if script_type == "M (Power Query)":
                        all_mappings.append({'old': f'#"{ot}"', 'new': f'#"{nt}"', 'len': len(f'#"{ot}"')})
                    
                    all_mappings.append({'old': f"'{ot}'", 'new': f"'{nt}'", 'len': len(f"'{ot}'")})
                    all_mappings.append({'old': ot, 'new': nt, 'len': len(ot)})

            # Sort by length descending to ensure specific matches happen before broad ones
            sorted_map = sorted(all_mappings, key=lambda x: x['len'], reverse=True)
            
            converted_script = source_text
            for item in sorted_map:
                converted_script = converted_script.replace(item['old'], item['new'])
            
            st.code(converted_script, language='sql' if script_type == "DAX" else 'powerquery')
            st.download_button("Download Script", converted_script, "converted_full.txt")
        else:
            st.info("Upload CSV in sidebar and paste script to begin.")

# --- TAB 2: M-SCRIPT STEP INJECTOR ---
with tab2:
    st.subheader("M-Script Source Step Injector")
    col1, col2 = st.columns(2)
    with col1:
        m_script = st.text_area("Paste M Script", height=400, key="m_inj_input")
    with col2:
        if df_map is not None and m_script:
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

# --- TAB 3: MAPPING PREVIEWER ---
with tab3:
    st.subheader("Mapping Logic Preview")
    if df_map is not None:
        preview_data = []
        for _, row in df_map.iterrows():
            preview_data.append({
                "Old Table": row.get('OldTable'),
                "Old Field": row.get('OldField'),
                "M Syntax": f'#"{row.get("OldTable")}"["{row.get("OldField")}"]' if row.get("OldTable") else "",
                "DAX (Quoted)": f"'{row.get('OldTable')}'[{row.get('OldField')}]" if row.get('OldTable') and row.get('OldField') else "",
                "DAX (Unquoted)": f"{row.get('OldTable')}[{row.get('OldField')}]" if row.get('OldTable') and row.get('OldField') else "",
                "New Table": row.get('NewTable'),
                "New Field": row.get('NewField')
            })
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True)