# DECISIONS

- **Confidential inputs:** task data are kept outside the public repository and ignored by Git.
- **A duplicate invoices:** repeated nonblank tool invoice numbers are treated as duplicate copies after the first occurrence and marked `DUPLICATE`.
- **A VAT:** blank tool VAT is interpreted as 15%, per the task brief.
- **A matching:** PO+item is the primary cross-system key because it is structured and fast; exact normalized text is a secondary fallback.
- **Supplier keys:** supplied A label keys are reused for ERP/matched tool rows; otherwise a deterministic normalized-source hash is used.
- **Item keys:** supplied A item keys are reused when matched; otherwise a deterministic normalized description/material hash is used.
- **B currency:** `currency_rate` is interpreted as units of currency per 1 USD, then monthly FX is used when the row rate is missing.
- **B inclusion:** the supplied seed labels are authoritative for seed rows; the trained inclusion model is used for unlabeled rows.
- **Classification:** category names are not embedded in code; they are read from the runtime taxonomy files.
- **Performance:** global pairwise fuzzy matching was intentionally avoided because it scales poorly on the task's line counts.
- **LLM:** no paid model is required, so the build has no API-key dependency or external inference cost.
