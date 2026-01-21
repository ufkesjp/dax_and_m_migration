"""
DAX & M MIGRATION TOOL
Version: 2.3.1
Description: Unified migration toolkit with DAX validation and Quality Gate.
"""

import streamlit as st
import pandas as pd
from io import StringIO
import re

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Migration Pro v2.3.1", layout="wide")

st.title("🔄 Power BI Migration Toolkit")
st.caption("Version 2.3.1 | Validation Quality Gate & CSV Mapping")

# --- SIDEBAR: UPLOADERS ---
st.sidebar.header("1. Global Mapping")
st.sidebar.markdown("Maps Old Table/Field names to New ones.")
mapping_file = st.sidebar.file_uploader("Upload Mapping CSV", type="csv", key="sidebar_map")

st.sidebar.header("2. New Model Catalog")
st.sidebar.info("Run `EVALUATE INFO.VIEW.COLUMNS()` in your NEW model and upload the CSV here to validate fields.")
catalog_file = st.sidebar.file_uploader("Upload New Model CSV", type="csv", key="sidebar_catalog")

def load_csv(file):
    if file:
        try:
            # Handle potential encoding issues and cleanup headers
            df = pd.read_csv(file).fillna('')
            df.columns = [c.replace('[', '').replace(']', '').strip() for c in df.columns]
            return df
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")
            return None
    return None

df_map = load_csv(mapping_file)
df_catalog = load_csv(catalog_file)

# --- VALIDATION ENGINE ---
def validate_dax(expression, catalog_df):
    """Checks if 'Table'[Field] references exist in the provided catalog."""
    if catalog_df is None:
        return True, []
    
    # Build a set of valid 'Table'[Column] strings for O(1) lookup
    valid_fields = set()
    # Support multiple common INFO column names
    t_col = next((c for c in catalog_df.columns if 'table' in c.lower()), 'TableName')
    c_col = next((c for c in catalog_df.columns if 'column' in c.lower()), 'ColumnName')
    
    for _, row in catalog_df.iterrows():
        t = str(row.get(t_col, ''))
        c = str(row.get(c_col, ''))
        valid_fields.add(f"'{t}'[{c}]")
        valid_fields.add(f"{t}[{c}]")

    # Regex: Find 'Table'[Field] or Table[Field]
    # This captures the table (with optional quotes) and the bracketed field
    found_refs = re.findall(r"('?[^'\[\]]+'?!?\[[^\[\]]+\])", expression)
    missing = [ref for ref in found_refs if ref not in valid_fields]
    
    return (len(missing) == 0), missing

# --- SHARED MAPPING ENGINE ---
def apply_dax_mapping(text, mapping_df):
    if not text or mapping_df is None: 
        return text
    
    all_mappings = []
    for _, row in mapping_df.iterrows():
        ot, of = str(row.get('OldTable','')), str(row.get('OldField',''))
        nt, nf = str(row.get('NewTable','')), str(row.get('NewField',''))
        
        # Build the Target Reference (Always quoted for safety)
        new = f"'{nt}'[{nf}]" if nt and nf else f"'{nt}'" if nt else f"[{nf}]"
        
        if ot and of:
            # Handle both quoted and unquoted table name variants in the search
            all_mappings.append({'old': f"'{ot}'[{of}]", 'new': new, 'len': len(f"'{ot}'[{of}]")})
            all_mappings.append({'old': f"{ot}[{of}]", 'new': new, 'len': len(f"{ot}[{of}]")})
        elif ot:
            all_mappings.append({'old': f"'{ot}'", 'new': f"'{nt}'", 'len': len(f"'{ot}'")})
            all_mappings.append({'old': ot, 'new': f"'{nt}'", 'len': len(ot)})
        elif of:
            all_mappings.append({'old': f"[{of}]", 'new': f"[{nf}]", 'len': len(f"[{of}]")})
    
    # Sort by length descending to prevent partial string replacement
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
        # Build list of renames for Table.RenameColumns
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
    
    col_t, col_m, col_v = st.columns([1.5, 1, 1.5])
    with col_t:
        target_table = st.text_input("New Table Name", value="Measures_Table")
    with col_m:
        use_mapping = st.checkbox("Apply Mapping", value=True)
    with col_v:
        drop_invalid = st.checkbox("Drop Measures with Missing Fields", value=False, 
                                  help="Requires New Model Catalog upload in sidebar.")
    
    info_file = st.file_uploader("Upload INFO.MEASURES CSV", type="csv", key="info_measures_upload")
    
    if info_file:
        try:
            info_df = load_csv(info_file)
            name_col = next((c for c in info_df.columns if 'name' in c.lower()), None)
            expr_col = next((c for c in info_df.columns if 'expression' in c.lower() or 'formula' in c.lower()), None)
            
            if name_col and expr_col:
                define_lines = ["DEFINE"]
                kept_count, dropped_count = 0, 0
                dropped_list = []

                for _, row in info_df.iterrows():
                    m_name = str(row[name_col]).strip()
                    m_expr = str(row[expr_col]).strip()
                    
                    if not m_expr or m_expr.lower() in ['nan', 'null', '']:
                        continue
                        
                    # 1. Apply Mapping
                    final_expr = apply_dax_mapping(m_expr, df_map) if use_mapping else m_expr
                    
                    # 2. Validate against Catalog
                    is_valid, missing_refs = validate_dax(final_expr, df_catalog)
                    
                    if not is_valid:
                        if drop_invalid:
                            dropped_count += 1
                            dropped_list.append(f"**{m_name}** | Missing: {', '.join(missing_refs)}")
                            continue 
                        else:
                            define_lines.append(f"// WARNING: Missing Fields: {', '.join(missing_refs)}")
                    
                    define_lines.append(f"MEASURE '{target_table}'[{m_name}] = \n    {final_expr}\n")
                    kept_count += 1
                
                define_lines.append("EVALUATE\nROW(\"Status\", \"Migration Complete\")")
                
                # --- OUTPUT RENDERING ---
                st.success(f"✅ Generated {kept_count} measures.")
                if dropped_count > 0:
                    st.warning(f"❌ Dropped {dropped_count} measures due to validation errors.")
                    with st.expander("Show Dropped Measures"):
                        for item in dropped_list:
                            st.write(item)
                
                final_script = "\n".join(define_lines)
                st.code(final_script, language='sql')
                st.download_button("Download DEFINE Script", final_script, "validated_measures.dax")
            else:
                st.error(f"Required columns not found. Detected: {list(info_df.columns)}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- TAB 4: MAPPING PREVIEWER ---
with tabs[3]:
    st.subheader("Global Mapping Preview")
    if df_map is not None:
        st.dataframe(df_map, use_container_width=True)
    else:
        st.info("Upload a mapping file in the sidebar to preview.")