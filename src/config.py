"""Configuration settings for CSV Field Comparison Tool."""

from typing import List

# Column identifiers
ID_COLUMN: str = 'job_id'
JOB_NAME_COLUMN: str = 'job_name'
GOLD_JOB_NAME_COLUMN: str = 'job_name_gold'
OUTPUT_JOB_NAME_COLUMN: str = 'job_name_output'

# Fields requiring similarity-based matching (fuzzy matching)
# Add fields here that may have minor variations like addresses or names
COMPARE_FIELDS: List[str] = [
    'loss_details.loss_location_address',
    'contact_details.contact_address',
    'insured_details.insured_address',
    'insured_details.insured_organization_name'
]

# Similarity threshold for fuzzy matching (0.0 to 1.0)
# 0.8 means 80% similarity is required for a match
THRESHOLD: float = 0.8

# Placeholder values
EMPTY_CELL_PLACEHOLDER: str = "false"
NO_VALUE_PLACEHOLDER: str = "No Value"
NO_ID_PLACEHOLDER: str = "No ID"

# Status messages
VALID_STATUS: str = 'Valid'
INVALID_STATUS: str = 'No Valid'
FIELD_IN_TEST_NOT_GOLD: str = "This field value exists in TEST DATA but not in gold"
FIELD_IN_GOLD_NOT_TEST: str = "This field value exists in GOLD DATA but not in output"