"""
DAX & M MIGRATION TOOL
Version: 1.8.0
Description: Unified Tab-based app with shared sidebar uploader and Mapping Previewer.
"""

import streamlit as st
import pandas as pd
import re

# v1.8.0: Layout Setup
st.set_page_config(page_title="Migration Pro v1.8", layout="wide")

st.title("🔄 Power BI Migration Toolkit")
st.caption("Version 1.8.0 | Shared Mapping System")

# --- SIDEBAR: GLOBAL UPLOAD ---
st.sidebar.header("1. Global Mapping Upload")
mapping_file = st.sidebar.file_uploader("Upload Mapping CSV", type="csv")

# Helper to load mapping once per rerun
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
    "🚀 Full Script Converter", 
    "🛠️ M-Script Step Injector", 
    "🔍 Mapping Previewer"
])

# --- TAB 1: FULL SCRIPT CONVERTER ---
with tab1:
    st.subheader("Global Find-and-Replace")
    st.caption("v1.5.0 Logic: Replaces every instance of a reference throughout the script.")

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
                    old = f"'{ot}'[{of}]" if script_type == "DAX" else f'#"{ot}"["{of}"]'
                    new = f"'{nt}'[{nf}]" if script_type == "DAX" else f'#"{nt}"["{nf}"]'
                    all_mappings.append({'old': old, 'new': new, 'len': len(old)})
                elif ot and nt and not of:
                    old = f"'{ot}'" if script_type == "DAX" else f'#"{ot}"'
                    new = f"'{nt}'" if script_type == "DAX" else f'#"{nt}"'
                    all_mappings.append({'old': old, 'new': new, 'len': len(old)})
                elif of and nf and not ot:
                    all_mappings.append({'old': f"[{of}]", 'new': f"[{nf}]", 'len': len(f"[{of}]")})

            sorted_map = sorted(all_mappings, key=lambda x: x['len'], reverse=True)
            converted_script = source_text
            for item in sorted_map:
                converted_script = converted_script.replace(item['old'], item['new'])
            
            st.code(converted_script, language='sql' if script_type == "DAX" else 'powerquery')
            st.download_button("Download Script", converted_script, "converted_full.txt")
        else:
            st.warning("Upload CSV in sidebar and paste script to start.")

# --- TAB 2: M-SCRIPT STEP INJECTOR ---
with tab2:
    st.subheader("M-Script Source Step Injector")
    st.caption("v1.5.0 Logic: Injects Table.RenameColumns after the first detected step.")

    col1, col2 = st.columns(2)
    with col1:
        m_script = st.text_area("Paste M Script from Advanced Editor", height=400, key="m_inj_input")

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

                final_m = "\n".join(new_lines)
                st.success(f"Injected after step: `{first_step_name}`")
                st.code(final_m, language='powerquery')
                st.download_button("Download Injected M", final_m, "injected_m.txt")
            else:
                st.error("No valid Field renames found in mapping.")
        else:
            st.warning("Upload CSV in sidebar and paste M script.")

# --- TAB 3: MAPPING PREVIEWER ---
with tab3:
    st.subheader("Mapping Logic Preview")
    st.markdown("See how your CSV rows are translated into specific code syntax.")

    if df_map is not None:
        # Generate a quick preview of both syntaxes simultaneously for the user
        preview_data = []
        for _, row in df_map.iterrows():
            ot, of = str(row.get('OldTable', '')), str(row.get('OldField', ''))
            nt, nf = str(row.get('NewTable', '')), str(row.get('NewField', ''))
            
            if ot and of:
                dax_old = f"'{ot}'[{of}]"
                m_old = f'#"{ot}"["{of}"]'
            elif ot:
                dax_old = f"'{ot}'"
                m_old = f'#"{ot}"'
            else:
                dax_old = f"[{of}]"
                m_old = f"[{of}]"

            preview_data.append({
                "Source Table": ot,
                "Source Field": of,
                "DAX Syntax (Old)": dax_old,
                "M Syntax (Old)": m_old,
                "Target Table": nt,
                "Target Field": nf
            })

        st.dataframe(pd.DataFrame(preview_data), use_container_width=True)
    else:
        st.info("Upload a CSV in the sidebar to see the logic preview.")