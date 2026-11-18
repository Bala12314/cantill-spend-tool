# APPROACH

## Pipeline
1. Read company configuration and source CSVs.
2. Normalize identifiers/text without altering source data.
3. Apply company-specific spend and inclusion rules.
4. Build deterministic supplier/item keys.
5. For A, reconcile tool rows to ERP rows using PO+item first and exact normalized description second; reuse the ERP label keys when matched.
6. Train a lightweight text classifier from available labels and classify unlabeled lines to the taxonomy leaf.
7. Reconstruct parent taxonomy levels from the runtime taxonomy file.
8. Emit exactly one output row per input record.

## Matching
A PO references are parsed into PO number and PO item and looked up in an indexed ERP map. This avoids an all-pairs fuzzy search. Exact normalized line-description matching is a secondary path. Unmatched rows receive deterministic keys derived from normalized source text.

## Classification
The supplied taxonomy is read at runtime. Training uses TF-IDF word and character features with LinearSVC. This avoids an external paid API and is fast enough for the supplied A/B data. Confidence is derived from the classifier decision margin through a sigmoid transform.

## Zero-label operation
The classifier path requires labels only when training data exist. If a future company has no labels, the pipeline can be extended with taxonomy-name matching/fallback; this build's A/B execution uses the labels explicitly supplied by the task.

## Spend
A ERP values are treated as net of tax. A tool gross values are divided by `(1 + VAT rate)`, with blank VAT defaulting to 15%. B amounts are divided by `currency_rate` (units of local currency per USD); if missing, the monthly FX table is used.

## Runtime and cost
No LLM or paid API is used. Runtime is measured by the single build command. The implementation deliberately avoids global fuzzy matching over tens of thousands of rows, which would make the 25k-line runtime requirement harder to satisfy.

## A accuracy
The repository should report validation metrics only when they are actually measured during a held-out evaluation. The supplied labels are used for A's known ERP rows; tool rows are classified from the trained model or inherited from a matched ERP record.
