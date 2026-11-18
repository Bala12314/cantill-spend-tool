# APPROACH

## End-to-end flow
1. Load the JSON build configuration supplied with the repository.
2. Read the required company-specific CSV inputs from the configured local data directory.
3. Normalize identifiers and text for matching while retaining the original source values.
4. Apply inclusion, exclusion, spend, and currency rules.
5. Build deterministic supplier and item keys.
6. Reconcile Company A tool invoices to ERP records using PO number + PO item first, followed by exact normalized description matching.
7. Build text-label prototypes from the available labelled records and compare input text against those prototypes using TF-IDF cosine similarity.
8. Map predicted taxonomy leaf labels back to their parent levels using the runtime taxonomy file.
9. Write one output row per input record to the configured output path.

## Company A
ERP goods-receipt rows retain their supplied labels and use the ERP net value as spend. Tool invoice rows are checked for duplicate invoice numbers and disallowed statuses. Gross tool amounts are converted to net spend using the row VAT rate, with a 15% default when VAT is blank.

Tool rows are matched to ERP rows using an indexed PO + item lookup. Exact normalized line-description matching is the secondary route. Where a match exists, the ERP supplier and item keys are reused; unmatched rows receive deterministic keys derived from normalized source values.

## Company B
Seed inclusion labels are preserved for known seed rows. A TF-IDF prototype model is trained from seed examples to infer inclusion for unlabelled rows. Category prototypes are built from included seed rows with available taxonomy labels.

Spend is converted to USD using the row's currency rate when present. Missing rates fall back to the monthly FX table. Taxonomy levels are reconstructed from the supplied taxonomy file.

## Classification method
The implementation uses TF-IDF text vectors and label-level text prototypes. A row is assigned the label whose prototype has the highest cosine similarity. The confidence field is a bounded score derived from the best-versus-second-best similarity margin; it is a heuristic ranking signal, not a calibrated probability.

This implementation does not use LinearSVC, an LLM, or a paid external API.

## Runtime considerations
PO matching uses indexed dictionaries rather than global pairwise fuzzy matching. This reduces matching work for larger input files. Run the complete build from the repository root with:

```bash
python run.py --config build.json
```

The run requires the confidential task CSVs to be present locally in the configured `data/` directory. Those inputs are intentionally not stored in the public repository.

## Validation
The repository includes a QA summary for the submitted output snapshots. Do not interpret those recorded counts as a fresh execution result: rerun the command with the task data to reproduce and validate the outputs.
