# --- TAB 3: DAX MEASURE DEFINER (v2.1.4 - Clipboard Optimized) ---
with tabs[2]:
    st.subheader("Bulk Measure Definer (INFO.MEASURES)")
    target_table = st.text_input("Target Table Name", value="Measures_Table")
    
    measures_input = st.text_area("Paste FULL DAX Studio Results here", height=300)
    
    if measures_input and df_map is not None:
        try:
            # Step 1: Clean the raw string (DAX Studio often adds " to multiline expressions)
            # We preserve the structure but help the parser see the tabs
            cleaned_input = measures_input.replace('\r\n', '\n')
            
            # Step 2: Parse using Tab as primary separator (Standard for DAX Studio Copy)
            m_df = pd.read_csv(StringIO(cleaned_input), sep='\t', engine='python')
            
            # Fallback: if tabs didn't work, try auto-detect
            if len(m_df.columns) <= 1:
                m_df = pd.read_csv(StringIO(cleaned_input), sep=None, engine='python')

            # Step 3: Clean column names (Remove brackets or extra spaces)
            m_df.columns = [c.replace('[', '').replace(']', '').strip() for c in m_df.columns]
            
            # Step 4: Flexible column detection
            name_col = next((c for c in m_df.columns if 'name' in c.lower()), None)
            expr_col = next((c for c in m_df.columns if 'expression' in c.lower() or 'formula' in c.lower()), None)
            
            if name_col and expr_col:
                define_lines = ["DEFINE"]
                count = 0
                
                for _, row in m_df.iterrows():
                    m_name = str(row[name_col]).strip()
                    m_expr = str(row[expr_col]).strip()
                    
                    # Handle DAX expressions that were wrapped in double quotes during export
                    if m_expr.startswith('"') and m_expr.endswith('"'):
                        m_expr = m_expr[1:-1].replace('""', '"')
                    
                    if not m_expr or m_expr.lower() == 'nan' or m_expr == "":
                        continue
                        
                    mapped_expr = apply_dax_mapping(m_expr, df_map)
                    define_lines.append(f"MEASURE '{target_table}'[{m_name}] = \n    {mapped_expr}\n")
                    count += 1
                
                define_lines.append("EVALUATE")
                define_lines.append(f"ROW(\"Status\", \"{count} Measures Generated\")")
                
                if count > 0:
                    final_script = "\n".join(define_lines)
                    st.success(f"✅ Processed {count} measures from your clipboard.")
                    st.code(final_script, language='sql')
                    st.download_button("Download .dax", final_script, "bulk_define.dax")
                else:
                    st.warning("Found the columns, but no valid expressions to convert.")
            else:
                st.error(f"Could not identify columns. Detected headers: {list(m_df.columns)}")
                st.info("Tip: Ensure you are copying the header row from DAX Studio results.")

        except Exception as e:
            st.error(f"Clipboard Parsing Error: {e}")