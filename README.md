# Cantill Spend Data Pipeline

Author: **Abhishek Kaushal**  
GitHub: [Bala12314](https://github.com/Bala12314)

A config-driven Python pipeline for processing the Cantill Company A and Company B spend datasets.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`

Install dependencies once:

```bash
python -m pip install -r requirements.txt
```

## Run the complete pipeline

From the repository root, run:

```bash
python run.py --config build.json
```

On Windows, you can also run `run.bat`; on macOS/Linux, run `bash run.sh`.

The build configuration reads the confidential input files from the local `data/` directory and writes:

- `outputs/Abhishek_Kaushal__A.csv`
- `outputs/Abhishek_Kaushal__B.csv`

The repository also retains the submitted A and B output CSV snapshots in its root directory.

## Required local input files

Place the task-provided files in `data/` before running the pipeline:

**Company A**
- `erp_goods_receipts.csv`
- `invoice_tool_export.csv`
- `labels_A.csv`
- `taxonomy_A.csv`

**Company B**
- `invoice_lines.csv`
- `seed_labels.csv`
- `taxonomy_B.csv`
- `fx_rates_usd.csv`

These source files are not included in the public repository.

## Output schema

Each generated output contains one row per input record and these columns:

`record_id`, `include`, `exclusion_reason`, `supplier_key`, `item_key`, `spend`, `l1`, `l2`, `l3`, `l4`, `confidence`.

## Implementation notes

- Company A reconciles tool invoices to ERP rows using PO number + item first, then exact normalized description matching.
- Duplicate tool invoice numbers after the first occurrence are excluded as `DUPLICATE`.
- Company A tool gross amounts are converted to net-of-tax using the VAT rate; blank VAT defaults to 15%.
- Company B uses row-level currency rates and falls back to the monthly USD FX table.
- Taxonomy labels are loaded from the supplied taxonomy files at runtime.
- Classification uses TF-IDF text features and a lightweight similarity-based label prototype approach; no paid API key is required.

See [APPROACH.md](APPROACH.md) and [DECISIONS.md](DECISIONS.md) for implementation details and assumptions.

## Repository hygiene

Task input data is confidential and must not be committed. The `.gitignore` excludes CSV and Excel files placed in `data/`. Only source code, configuration, documentation, and approved output artifacts belong in the public repository.
