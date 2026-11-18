# Cantill Spend Data Pipeline — Abhishek Kaushal

Author: **Abhishek Kaushal**  
GitHub: **Bala12314**

## Run end-to-end

Install dependencies, place the confidential task data in `data/`, then run one command from the repository root:

```bash
python -m spendkit.run --config configs/build.json
```

The command generates `outputs/Abhishek_Kaushal__A.csv` and `outputs/Abhishek_Kaushal__B.csv`.

## Repository hygiene

The task data are confidential. They are intentionally excluded by `.gitignore` and must never be committed to the public repository.

## Required output

Each output contains one row per input record with: `record_id`, `include`, `exclusion_reason`, `supplier_key`, `item_key`, `spend`, `l1`, `l2`, `l3`, `l4`, and `confidence`.

## Design

- A: ERP rows use the supplied A labels for supplier/item/category keys and tool invoices are matched by PO+item or exact normalized line text where possible.
- A tool invoice duplicates are excluded as `DUPLICATE`; gross tool amounts are converted to net-of-tax using the row VAT rate, defaulting blank VAT to 15%.
- B: seed labels train inclusion and category models; currency is converted using `currency_rate` or monthly USD FX fallback.
- Taxonomy is loaded from the configured taxonomy files rather than hard-coded category names.
- The classifier uses TF-IDF word/character features with a linear SVM for fast, unattended execution.

See `APPROACH.md` and `DECISIONS.md` for details and limitations.
