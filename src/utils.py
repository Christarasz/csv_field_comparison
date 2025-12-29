"""Utility functions for CSV data processing and comparison."""

import re
import difflib
from typing import Dict, Any, Set
import pandas as pd
import numpy as np
import config


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert all string values to lowercase."""
    return df.applymap(lambda x: x.lower() if isinstance(x, str) else x)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from column names."""
    df.columns = df.columns.str.strip()
    return df


def fill_empty_with_blank(df: pd.DataFrame) -> pd.DataFrame:
    """Replace NaN values with placeholder."""
    return df.fillna(config.EMPTY_CELL_PLACEHOLDER)


def strip_values(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and handle empty strings."""
    def clean_cell(x: Any) -> Any:
        if pd.isna(x):
            return config.NO_VALUE_PLACEHOLDER
        if isinstance(x, str):
            stripped = x.strip()
            return stripped if stripped else config.NO_VALUE_PLACEHOLDER
        return x
    return df.applymap(clean_cell)


def melt_dataframe(df: pd.DataFrame, id_vars: list) -> pd.DataFrame:
    """Transform DataFrame from wide to long format."""
    return pd.melt(df, id_vars=id_vars, var_name='Attribute', value_name='Value')


def create_unique_id(df: pd.DataFrame, job_name_col: str) -> pd.DataFrame:
    """Create unique identifier by combining job name and attribute."""
    df['unique_id'] = df[job_name_col] + '_' + df['Attribute']
    return df


def merge_dataframes(output_df: pd.DataFrame, gold_df: pd.DataFrame) -> pd.DataFrame:
    """Merge output and gold DataFrames."""
    return pd.merge(
        output_df, gold_df, on='unique_id',
        suffixes=('_output', '_gold'), how='outer'
    )


def remove_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where both job_id_gold and Value_output are NaN."""
    return df[~(df['job_id_gold'].isna() & df['Value_output'].isna())]


def get_base_field(attr: Any) -> str:
    """Extract base field name without array indices.
    
    Examples:
        'field[0]' -> 'field'
        'field[123]' -> 'field'
        'field()' -> 'field'
    """
    if pd.isna(attr):
        return ''
    return re.sub(r'\[\d+\]|\(\)', '', str(attr))


def similarity_ratio(a: Any, b: Any) -> float:
    """Calculate similarity ratio between two values."""
    return difflib.SequenceMatcher(None, str(a), str(b)).ratio()


def compute_validity(
    row: pd.Series,
    merged_df: pd.DataFrame,
    compare_fields: list,
    threshold: float
) -> str:
    """Compute validity status for a row based on comparison rules."""
    val_output = row['Value_output']
    val_gold = row['Value_gold']
    attribute_output = row['Attribute_output']
    job_name_output = row['job_name_output']
    
    base_attr = get_base_field(attribute_output)
    in_compare = base_attr in compare_fields
    
    # Check if it's an array field
    is_array = (
        pd.notna(attribute_output) and 
        isinstance(attribute_output, str) and 
        '[' in attribute_output and ']' in attribute_output
    )
    
    if in_compare:
        # Use similarity matching for fields in COMPARE_FIELDS
        if is_array:
            return _validate_array_similarity(
                val_output, job_name_output, attribute_output,
                merged_df, threshold
            )
        else:
            return _validate_single_similarity(val_output, val_gold, threshold)
    else:
        # Use exact matching for other fields
        if is_array:
            return _validate_array_exact(
                val_output, val_gold, job_name_output,
                attribute_output, merged_df
            )
        else:
            return _validate_single_exact(val_output, val_gold)


def _validate_array_similarity(
    val_output: Any,
    job_name_output: str,
    attribute_output: str,
    merged_df: pd.DataFrame,
    threshold: float
) -> str:
    """Validate array field using similarity matching."""
    attribute_prefix = get_base_field(attribute_output)
    relevant_rows = merged_df[
        (merged_df['job_name_output'] == job_name_output) &
        (merged_df['Attribute_output'].apply(get_base_field) == attribute_prefix)
    ]
    
    gold_values = set(relevant_rows['Value_gold'].dropna().unique())
    
    # Check if output is NaN and any gold value is NaN
    if pd.isna(val_output):
        if relevant_rows['Value_gold'].isna().any():
            return config.VALID_STATUS
    
    # Check similarity with all gold values
    for gold_val in gold_values:
        if similarity_ratio(val_output, gold_val) >= threshold:
            return config.VALID_STATUS
    
    return config.INVALID_STATUS


def _validate_single_similarity(val_output: Any, val_gold: Any, threshold: float) -> str:
    """Validate single field using similarity matching."""
    if pd.isna(val_output) and pd.isna(val_gold):
        return config.VALID_STATUS
    if pd.isna(val_output) or pd.isna(val_gold):
        return config.INVALID_STATUS
    return (
        config.VALID_STATUS 
        if similarity_ratio(val_output, val_gold) >= threshold 
        else config.INVALID_STATUS
    )


def _validate_array_exact(
    val_output: Any,
    val_gold: Any,
    job_name_output: str,
    attribute_output: str,
    merged_df: pd.DataFrame
) -> str:
    """Validate array field using exact matching."""
    attribute_prefix = get_base_field(attribute_output)
    relevant_rows = merged_df[
        (merged_df['job_name_output'] == job_name_output) &
        (merged_df['Attribute_output'].apply(get_base_field) == attribute_prefix)
    ]
    
    gold_values = set(relevant_rows['Value_gold'].dropna().unique())
    
    # Check if output is NaN and any gold value is NaN
    if pd.isna(val_output):
        if relevant_rows['Value_gold'].isna().any():
            return config.VALID_STATUS
    
    if val_output in gold_values:
        return config.VALID_STATUS
    if pd.isna(val_output) and pd.isna(val_gold):
        return config.VALID_STATUS
    
    return config.INVALID_STATUS


def _validate_single_exact(val_output: Any, val_gold: Any) -> str:
    """Validate single field using exact matching."""
    if pd.isna(val_output) and pd.isna(val_gold):
        return config.VALID_STATUS
    return config.VALID_STATUS if val_output == val_gold else config.INVALID_STATUS


def add_missing_gold_array_rows(
    merged_df: pd.DataFrame,
    compare_fields: list,
    threshold: float
) -> pd.DataFrame:
    """Add rows for gold array values that don't exist in output."""
    # Identify gold array rows
    gold_array_mask = merged_df['Attribute_gold'].str.contains(r'\[\d+\]', na=False)
    gold_array_rows = merged_df[gold_array_mask].copy()
    
    if gold_array_rows.empty:
        return merged_df
    
    # Prepare for matching
    gold_array_rows['attr_prefix'] = gold_array_rows['Attribute_gold'].apply(get_base_field)
    merged_df['attr_prefix_output'] = merged_df['Attribute_output'].apply(get_base_field)
    
    # Build lookup for output values
    output_lookup = (
        merged_df
        .dropna(subset=['job_name_output', 'attr_prefix_output'])
        .groupby(['job_name_output', 'attr_prefix_output'])['Value_output']
        .apply(lambda x: set(x.dropna().unique()))
        .to_dict()
    )
    
    new_rows = []
    for _, gold_row in gold_array_rows.iterrows():
        job_name = gold_row['job_name_gold']
        attr_prefix = gold_row['attr_prefix']
        gold_value = gold_row['Value_gold']
        in_compare = attr_prefix in compare_fields
        
        output_values = output_lookup.get((job_name, attr_prefix), set())
        
        # Check if gold value exists in output
        is_found = False
        if in_compare:
            is_found = any(
                similarity_ratio(gold_value, output_val) >= threshold
                for output_val in output_values
            )
        else:
            is_found = str(gold_value) in {str(val) for val in output_values}
        
        if not is_found:
            new_rows.append({
                'job_id_output': config.NO_ID_PLACEHOLDER,
                'job_name_output': gold_row['job_name_gold'],
                'Attribute_output': gold_row['Attribute_gold'],
                'Value_output': config.FIELD_IN_GOLD_NOT_TEST,
                'unique_id': gold_row['unique_id'],
                'job_id_gold': gold_row['job_id_gold'],
                'job_name_gold': gold_row['job_name_gold'],
                'Attribute_gold': gold_row['Attribute_gold'],
                'Value_gold': gold_value,
                'validity': config.INVALID_STATUS
            })
    
    if new_rows:
        merged_df = pd.concat([merged_df, pd.DataFrame(new_rows)], ignore_index=True)
    
    return merged_df


def aggregate_base_attributes(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Calculate accuracy statistics grouped by base attribute."""
    # Extract base attribute
    attr_output = df['Attribute_output'].fillna('')
    attr_gold = df['Attribute_gold'].fillna('')
    
    df = df.copy()
    df['base_attribute'] = (
        attr_output
        .where(attr_output != '', attr_gold)
        .str.replace(r'\[\d+\]', '', regex=True)
        .str.strip()
    )
    
    # Group and aggregate
    grouped = df.groupby('base_attribute')['validity'].agg([
        ('valid', lambda x: (x == config.VALID_STATUS).sum()),
        ('total', 'count')
    ]).reset_index()
    
    grouped['accuracy'] = (grouped['valid'] / grouped['total'] * 100).round(2)
    
    return grouped.set_index('base_attribute')[['valid', 'total', 'accuracy']].to_dict('index')