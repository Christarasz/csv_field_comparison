"""CSV Field Comparison Tool - Main Streamlit Application."""

import io
import streamlit as st
import pandas as pd

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

import utils
import config


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="CSV Field Comparison Tool",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 CSV Field Comparison Tool")
    
    # Step 1: Upload datasets
    st.subheader("Step 1: Upload TEST and GOLD CSV datasets")
    
    uploaded_test = st.file_uploader(
        "Upload TEST (output) CSV file",
        type=["csv"],
        key="upload_test"
    )
    uploaded_gold = st.file_uploader(
        "Upload GOLD CSV file",
        type=["csv"],
        key="upload_gold"
    )
    
    if uploaded_test is None or uploaded_gold is None:
        st.info("📁 Please upload both TEST and GOLD CSV files to proceed.")
        st.stop()
    
    # Read uploaded files
    try:
        output_df = pd.read_csv(uploaded_test)
        st.success(f"✓ TEST file loaded: {len(output_df)} rows")
    except Exception as e:
        st.error(f"❌ Error reading TEST CSV: {e}")
        st.stop()
    
    try:
        gold_df = pd.read_csv(uploaded_gold)
        st.success(f"✓ GOLD file loaded: {len(gold_df)} rows")
    except Exception as e:
        st.error(f"❌ Error reading GOLD CSV: {e}")
        st.stop()
    
    feedback = st.empty()
    
    # Process dataframes
    output_df = utils.normalize_df(output_df)
    gold_df = utils.normalize_df(gold_df)
    
    output_df = utils.fill_empty_with_blank(output_df)
    gold_df = utils.fill_empty_with_blank(gold_df)
    
    output_df = utils.normalize_columns(output_df)
    gold_df = utils.normalize_columns(gold_df)
    
    output_df = utils.strip_values(output_df)
    gold_df = utils.strip_values(gold_df)
    
    # Validate job names
    job_names_test = output_df[config.JOB_NAME_COLUMN].unique()
    job_names_gold = gold_df[config.JOB_NAME_COLUMN].unique()
    
    if len(job_names_test) != len(job_names_gold):
        st.warning(
            f"⚠️ Job name count mismatch: TEST has {len(job_names_test)}, "
            f"GOLD has {len(job_names_gold)} job names."
        )
    else:
        mismatched = set(job_names_gold) - set(job_names_test)
        if mismatched:
            st.warning(
                f"⚠️ Job names in GOLD but not in TEST: {', '.join(mismatched)}"
            )
        else:
            st.success("✓ All job names match between datasets.")
    
    # Step 2: Field selection
    all_columns = [
        col for col in output_df.columns
        if col not in [config.ID_COLUMN, config.JOB_NAME_COLUMN]
    ]
    base_fields = sorted(set(utils.get_base_field(col) for col in all_columns))
    
    with st.expander("Step 2: Select fields to compare", expanded=True):
        filter_text = st.text_input("🔍 Filter fields:", value="")
        filtered_fields = [
            f for f in base_fields if filter_text.lower() in f.lower()
        ]
        
        if "prev_select_all" not in st.session_state:
            st.session_state.prev_select_all = False
        
        select_all = st.checkbox(
            "Select All Filtered Fields",
            value=st.session_state.prev_select_all,
            key="select_all"
        )
        
        if select_all != st.session_state.prev_select_all:
            for field in filtered_fields:
                st.session_state[f"field_{field}"] = select_all
            st.session_state.prev_select_all = select_all
        
        selected_fields = []
        for field in filtered_fields:
            key = f"field_{field}"
            if key not in st.session_state:
                st.session_state[key] = False
            if st.checkbox(field, key=key):
                selected_fields.append(field)
        
        st.caption(f"📋 {len(selected_fields)} field(s) selected.")
    
    if not selected_fields:
        st.info("👆 Please select at least one field to run the analysis.")
        return
    
    # Step 3: Run analysis
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            try:
                with st.spinner("🔄 Running analysis..."):
                    # Prepare data
                    id_vars = [config.ID_COLUMN, config.JOB_NAME_COLUMN]
                    output_melted = utils.melt_dataframe(output_df, id_vars)
                    gold_melted = utils.melt_dataframe(gold_df, id_vars)
                    
                    # Filter to selected fields
                    output_melted = output_melted[
                        output_melted['Attribute'].apply(
                            lambda x: utils.get_base_field(x) in selected_fields
                        )
                    ]
                    gold_melted = gold_melted[
                        gold_melted['Attribute'].apply(
                            lambda x: utils.get_base_field(x) in selected_fields
                        )
                    ]
                    
                    # Rename columns
                    gold_melted.rename(
                        columns={config.JOB_NAME_COLUMN: config.GOLD_JOB_NAME_COLUMN},
                        inplace=True
                    )
                    output_melted.rename(
                        columns={config.JOB_NAME_COLUMN: config.OUTPUT_JOB_NAME_COLUMN},
                        inplace=True
                    )
                    
                    # Create unique IDs
                    output_melted = utils.create_unique_id(
                        output_melted, config.OUTPUT_JOB_NAME_COLUMN
                    )
                    gold_melted = utils.create_unique_id(
                        gold_melted, config.GOLD_JOB_NAME_COLUMN
                    )
                    
                    # Merge
                    merged_df = utils.merge_dataframes(output_melted, gold_melted)
                    merged_df = utils.remove_empty_rows(merged_df)
                    
                    # Compute validity
                    merged_df['validity'] = merged_df.apply(
                        lambda row: utils.compute_validity(
                            row, merged_df, selected_fields, config.THRESHOLD
                        ),
                        axis=1
                    )
                    
                    # Add missing gold rows
                    merged_df = utils.add_missing_gold_array_rows(
                        merged_df, selected_fields, config.THRESHOLD
                    )
                    
                    # Clean up
                    merged_df = merged_df.dropna(subset=['Attribute_output'])
                    
                    condition = ~(
                        (merged_df['job_id_output'] == config.NO_ID_PLACEHOLDER) &
                        (merged_df['Value_gold'].isna())
                    )
                    merged_df = merged_df[condition]
                    
                    # Mark fields in TEST but not in GOLD
                    mask = (
                        (merged_df['validity'] == config.INVALID_STATUS) &
                        (merged_df['job_id_output'] != config.NO_ID_PLACEHOLDER)
                    )
                    merged_df.loc[mask, 'Value_gold'] = config.FIELD_IN_TEST_NOT_GOLD
                    
                    # Convert to string to prevent Arrow errors
                    for col in ["Value_output", "Value_gold"]:
                        if col in merged_df.columns:
                            merged_df[col] = merged_df[col].astype("string")
                    
                    # Calculate accuracy
                    accuracy_base_attribute = utils.aggregate_base_attributes(merged_df)
                    accuracy_df = pd.DataFrame({
                        'Attribute': list(accuracy_base_attribute.keys()),
                        'Valid Count': [
                            d['valid'] for d in accuracy_base_attribute.values()
                        ],
                        'Total Count': [
                            d['total'] for d in accuracy_base_attribute.values()
                        ],
                        'Accuracy (%)': [
                            d['accuracy'] for d in accuracy_base_attribute.values()
                        ]
                    })
                
                feedback.success("✅ Analysis completed!")
                
                # Display results
                st.divider()
                st.subheader("📈 Accuracy Metrics")
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                total_valid = accuracy_df['Valid Count'].sum()
                total_count = accuracy_df['Total Count'].sum()
                overall_accuracy = (
                    (total_valid / total_count * 100) if total_count > 0 else 0
                )
                
                with col1:
                    st.metric("Total Valid", f"{total_valid:,}")
                with col2:
                    st.metric("Total Comparisons", f"{total_count:,}")
                with col3:
                    st.metric("Overall Accuracy", f"{overall_accuracy:.2f}%")
                
                st.dataframe(accuracy_df, use_container_width=True, hide_index=True)
                
                # Create Excel download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    merged_df.to_excel(writer, sheet_name='Comparison Results', index=False)
                    accuracy_df.to_excel(writer, sheet_name='Accuracy Metrics', index=False)
                output.seek(0)
                
                st.divider()
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.download_button(
                        label="📥 Download Detailed Results (Excel)",
                        data=output.getvalue(),
                        file_name="comparison_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
            except Exception as e:
                feedback.error(f"❌ Error: {e}")
                st.exception(e)


if __name__ == "__main__":
    main()