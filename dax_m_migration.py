"""
DAX & M MIGRATION TOOL
Version: 2.0.0
Description: Unified Tab-based app. 
- Dax Measure Converter: Handles quoted/unquoted DAX references.
- M-Script Step Injector: Handles Power Query source-level renames.
"""

import streamlit as st
import pandas as pd
import re

# v2.0.0: UI Layout Setup
st.set_page_config(page_title="DAX & M Migration v2.0", layout="wide")

st.title("🔄 Power BI Migration Toolkit")
st.caption("Version 2.0.0 | Focused Tools")

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

# --- TABS SETUP ---
tab1, tab2, tab3 = st.tabs([
    "🚀 Dax Measure Converter", 
    "🛠️ M-Script Step Injector", 
    "🔍 Mapping Previewer"
])

# --- TAB 1: DAX MEASURE CONVERTER ---
with tab1:
    st.subheader("DAX Find-and-Replace")
    st.caption("Replaces table/field references. Automatically detects 'Table'[Field] and Table[Field].")
    
    col1, col2 = st.columns(2)
    with col1:
        source_text = st.text_area("Paste DAX Script", height=450, key="dax_conv_input")
    
    with col2:
        if df_map is not None and source_text:
            all_mappings = []
            for _, row in df_map.iterrows():
                ot, of = str(row.get('OldTable', '')), str(row.get('OldField', ''))
                nt, nf = str(row.get('NewTable', '')), str(row.get('NewField', ''))
                
                # New Target Syntax (Standardized with quotes)
                new_ref = f"'{nt}'[{nf}]" if nt and nf else f"'{nt}'" if nt else f"[{nf}]"
                
                # Scenario: Table and Field
                if ot and of:
                    # Match both 'Table'[Field] and Table[Field]
                    all_mappings.append({'old': f"'{ot}'[{of}]", 'new': new_ref, 'len': len(f"'{ot}'[{of}]")})
                    all_mappings.append({'old': f"{ot}[{of}]", 'new': new_ref, 'len': len(f"{ot}[{of}]")})
                
                # Scenario: Table Only rename
                elif ot and nt and not of:
                    all_mappings.append({'old': f"'{ot}'", 'new': f"'{nt}'", 'len': len(f"'{ot}'")})
                    all_mappings.append({'old': ot, 'new': f"'{nt}'", 'len': len(ot)})
                
                # Scenario: Field Only rename
                elif of and nf and not ot:
                    all_mappings.append({'old': f"[{of}]", 'new': f"[{nf}]", 'len': len(f"[{of}]")})

            # Sort by length descending to ensure specific matches happen before broad ones
            sorted_map = sorted(all_mappings, key=lambda x: x['len'], reverse=True)
            
            converted_script = source_text
            for item in sorted_map:
                converted_script = converted_script.replace(item['old'], item['new'])
            
            st.code(converted_script, language='sql')
            st.download_button("Download DAX Script", converted_script, "converted_dax.txt")
        else:
            st.info("Upload CSV in sidebar and paste DAX to start.")

# --- TAB 2: M-SCRIPT STEP INJECTOR ---
with tab2:
    st.subheader("M-Script Source Step Injector")
    st.caption("Injects Table.RenameColumns after the first detected step in Power Query.")

    col1, col2 = st.columns(2)
    with col1:
        m_script = st.text_area("Paste M Script from Advanced Editor", height=450, key="m_inj_input")

    with col2:
        if df_map is not None and m_script:
            # Build the rename list from the shared mapping
            rename_list = [f'{{"{r.OldField}", "{r.NewField}"}}' for r in df_map.itertuples() if r.OldField and r.NewField]

            if rename_list:
                lines = m_script.split('\n')
                new_lines, first_step_name, injected = [], None, False
                # Captures step names like #"Source" or Source
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
                        # Re-link the subsequent step to point to RenamedColumns
                        line = line.replace(f"({first_step_name})", "(RenamedColumns)").replace(f"{first_step_name},", "RenamedColumns,")
                        new_lines[-1] = line

                final_m = "\n".join(new_lines)
                st.success(f"Injected after step: `{first_step_name}`")
                st.code(final_m, language='powerquery')
                st.download_button("Download M Script", final_m, "injected_m.txt")
            else:
                st.error("No valid Field renames (OldField -> NewField) found in mapping.")
        else:
            st.warning("Upload CSV in sidebar and paste an M script.")

# --- TAB 3: MAPPING PREVIEWER ---
with tab3:
    st.subheader("Mapping Logic Preview")
    if df_map is not None:
        preview_data = []
        for _, row in df_map.iterrows():
            ot, of = str(row.get('OldTable', '')), str(row.get('OldField', ''))
            nt, nf = str(row.get('NewTable', '')), str(row.get('NewField', ''))
            
            preview_data.append({
                "Old Table": ot,
                "Old Field": of,
                "Pattern (Quoted)": f"'{ot}'[{of}]" if ot and of else f"'{ot}'" if ot else f"[{of}]",
                "Pattern (Unquoted)": f"{ot}[{of}]" if ot and of else ot if ot else f"[{of}]",
                "New Reference": f"'{nt}'[{nf}]" if nt and nf else f"'{nt}'" if nt else f"[{nf}]"
            })

        st.dataframe(pd.DataFrame(preview_data), use_container_width=True)
    else:
        st.info("Upload a CSV in the sidebar to see the logic preview.")