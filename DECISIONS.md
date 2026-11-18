# DECISIONS

- **Confidential inputs:** the task-provided source data are kept locally under `data/` and excluded from Git.
- **Single entry point:** `python run.py --config build.json` is the canonical end-to-end command; shell and Windows launchers delegate to it.
- **A duplicate invoices:** repeated nonblank tool invoice numbers after the first occurrence are excluded as `DUPLICATE`.
- **A approval status:** cancelled, rejected, not-approved, and unapproved tool rows are excluded.
- **A VAT:** blank tool VAT is interpreted as 15%; tool gross amounts are divided by one plus the VAT rate.
- **A matching:** PO number + PO item is the primary cross-system key; exact normalized description is the secondary fallback.
- **Supplier and item keys:** supplied A keys are reused for matched ERP/tool rows; otherwise deterministic hashes of normalized source values are generated.
- **B currency:** `currency_rate` is interpreted as units of local currency per 1 USD. The monthly FX table is the fallback when the row rate is missing.
- **B inclusion:** supplied seed inclusion labels are authoritative for seed rows; text prototypes infer inclusion for unlabelled rows.
- **Classification:** TF-IDF vectors are compared with label-level text prototypes using cosine similarity. The confidence field is a heuristic similarity-margin score, not a calibrated probability.
- **Taxonomy:** category hierarchy is loaded from the task taxonomy files rather than hard-coded in the pipeline.
- **Performance:** indexed PO matching is preferred over global pairwise fuzzy matching to keep runtime practical at the task's data volume.
- **External services:** no LLM, paid API, or API key is required.
- **Reproducibility:** the QA JSON describes the checked-in output snapshots; a fresh run with local task inputs is required to reproduce those outputs.
