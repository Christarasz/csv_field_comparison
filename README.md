# CSV Field Comparison Tool

A Streamlit application for comparing TEST and GOLD CSV datasets with configurable field matching and accuracy metrics.

## Features

- **Multiple Comparison Modes:**
  - Exact matching for standard fields
  - Array field comparison (e.g., `field[0]`, `field[1]`)
  - Similarity-based matching for fuzzy fields (addresses, names)

- **Interactive UI:**
  - Upload TEST and GOLD CSV files
  - Select specific fields or all fields for comparison
  - Real-time validation and feedback

- **Comprehensive Results:**
  - Field-level accuracy metrics
  - Overall accuracy summary
  - Downloadable Excel report with detailed comparison

## Quick Start

### Installation

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment:**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Run Application

```bash
streamlit run src/app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### 1. Prepare Your CSV Files

Both TEST and GOLD files must have:
- `job_id` column (unique identifier)
- `job_name` column (job type identifier)
- Other fields to compare

**Example CSV structure:**
```csv
job_id,job_name,field_name,address[0],address[1]
123,ClaimA,Value1,123 Main St,Apt 4
124,ClaimB,Value2,456 Oak Ave,Suite 200
```

### 2. Upload Files

- Click "Upload TEST (output) CSV file"
- Click "Upload GOLD CSV file"
- Wait for validation

### 3. Select Fields

- Use filter box to search fields
- Check individual fields or "Select All"
- Click "Run Analysis"

### 4. Review Results

- View accuracy metrics table
- Check overall accuracy summary
- Download detailed Excel report

## Configuration

Edit `src/config.py` to customize:

```python
# Fields requiring fuzzy matching (similarity-based)
COMPARE_FIELDS = [
    'loss_details.loss_location_address',
    'contact_details.contact_address',
    'insured_details.insured_address'
]

# Similarity threshold (0.0-1.0)
THRESHOLD = 0.8  # 80% similarity required
```

## Comparison Logic

### 1. Exact Match Fields
Standard fields not in `COMPARE_FIELDS` require exact matches.

### 2. Array Fields
Fields with brackets (e.g., `field[0]`, `field[1]`):
- Compared across all indices
- Accuracy calculated at base field level (without indices)

### 3. Similarity Match Fields
Fields in `COMPARE_FIELDS` use fuzzy matching:
- Similarity ratio ≥ threshold (default: 0.8)
- Useful for addresses, names with minor variations

## Output

### Accuracy Metrics
- **Attribute:** Base field name
- **Valid Count:** Number of valid matches
- **Total Count:** Total comparisons
- **Accuracy (%):** Percentage of valid matches

### Excel Export
Two sheets:
1. **Comparison Results:** Row-by-row comparison details
2. **Accuracy Metrics:** Field-level accuracy summary

## Project Structure

```
csv_field_comparison/
├── src/
│   ├── __init__.py
│   ├── app.py          # Main Streamlit application
│   ├── config.py       # Configuration settings
│   └── utils.py        # Utility functions
├── .gitignore
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.8+
- streamlit 1.29.0
- pandas 2.1.4
- openpyxl 3.1.2
- xlsxwriter 3.1.9

## Troubleshooting

**Issue:** "Error reading CSV"
- Ensure CSV has required columns (`job_id`, `job_name`)
- Check file encoding (should be UTF-8)

**Issue:** "No fields available"
- Verify CSV has columns beyond `job_id` and `job_name`

**Issue:** Large file performance
- Process datasets with fewer rows first
- Select specific fields instead of all fields

## License

MIT License - See LICENSE file for details