<!-- Syntax Corporation © 2026 — EBS AP PAF · v1.0.0 · 2026-06-02 -->

# EBS Interface Contract

How the agent reads from and writes to Oracle EBS. All access is via the `APPS`
schema's public synonyms and is **read-only** except the optional, explicitly
gated interface-table INSERT.

## Source tables (READ)

| Lookup | Tables (via `apps.` synonyms) | Notes |
|--------|-------------------------------|-------|
| `get_supplier` | `ap_suppliers`, `ap_supplier_sites_all`, `ap_terms` | Resolution order: `num_1099` (tax id) → `segment1` (vendor num) → exact name → fuzzy. Org-scoped via `ap_supplier_sites_all.org_id`. |
| `get_purchase_order` | `po_headers_all`, `po_lines_all`, `po_line_locations_all`, `po_distributions_all`, `gl_code_combinations_kfv`, `mtl_system_items_b`, `mtl_categories_b` | Returns header + lines with inherited distribution string + item number + category. |
| `get_receipts` | `rcv_transactions` (+ `po_lines_all`, `po_headers_all`) | `SUM(quantity)` per PO line where `transaction_type = 'RECEIVE'`. |
| `get_tax_code` | `zx_rates_b` | Active rate matched on `percentage_rate`; returns `tax_rate_code` as the classification code. |
| `get_gl_segments` | `gl_code_combinations_kfv` | Fallback only — validates a known enabled suspense combination. PO lines inherit their own distribution. |
| `check_duplicate_invoice` | `ap_invoices_all` | `vendor_id + invoice_num + org_id`. |

All dynamic values are passed as **bind variables** (no string interpolation).

## Target tables (WRITE — via interface only)

The agent populates a pragmatic subset of the two interface tables (full
`AP_INVOICES_INTERFACE` has ~150 columns; these cover standard invoices). Column
names mirror the EBS data dictionary so output drops into SQL*Loader / OIC
without remapping.

### `AP_INVOICES_INTERFACE` (header) — 25 columns
`INVOICE_ID, INVOICE_NUM, INVOICE_TYPE_LOOKUP_CODE, INVOICE_DATE, VENDOR_ID,
VENDOR_NUM, VENDOR_NAME, VENDOR_SITE_ID, VENDOR_SITE_CODE, INVOICE_AMOUNT,
INVOICE_CURRENCY_CODE, EXCHANGE_RATE, EXCHANGE_RATE_TYPE, EXCHANGE_DATE,
TERMS_NAME, TERMS_ID, DESCRIPTION, SOURCE, GROUP_ID, PO_NUMBER,
PAYMENT_METHOD_LOOKUP_CODE, ORG_ID, GL_DATE, ATTRIBUTE1, ATTRIBUTE2`

* `ATTRIBUTE1` = agent run-id, `ATTRIBUTE2` = confidence score (explainability).
* `SOURCE` = `EBS_AGENT_PAF`; `GROUP_ID` batches a run.
* `INVOICE_AMOUNT` **equals the sum of all interface lines (items + tax)** — the
  document balances. (Fixes the reference PoC, which dropped tax and would be
  rejected at import.)
* Foreign currency: `EXCHANGE_RATE_TYPE = 'Corporate'`, rate left blank (EBS
  derives it from GL daily rates), `EXCHANGE_DATE = invoice date`.

### `AP_INVOICE_LINES_INTERFACE` (lines) — 18 columns
`INVOICE_ID, INVOICE_LINE_ID, LINE_NUMBER, LINE_TYPE_LOOKUP_CODE, AMOUNT,
DESCRIPTION, DIST_CODE_CONCATENATED, PO_NUMBER, PO_LINE_NUMBER,
INVENTORY_ITEM_ID, ITEM_DESCRIPTION, QUANTITY_INVOICED, UNIT_PRICE,
UNIT_OF_MEAS_LOOKUP_CODE, TAX_CLASSIFICATION_CODE, ORG_ID, ATTRIBUTE1, ATTRIBUTE2`

* One `ITEM` line per invoice line; one `TAX` line when tax > 0.
* `ATTRIBUTE1` = match status (`AUTO`/`HOLD`/`NON_PO_REVIEW`), `ATTRIBUTE2` =
  `;`-joined exceptions.

## Tolerances (policy_engine)

| Check | Rule |
|-------|------|
| Unit price | held only if variance **> 2%** *and* dollar impact **> $25** |
| Quantity | held only if invoiced-over-received **> 5%** *and* dollar impact **> $25** |
| Receipt | held if no receipt recorded for the PO line |
| PO line | held if no PO line matches by `po_line_num` or `item_number` |

The dual percentage-AND-dollar gate prevents trivial cent-level variances from
holding large invoices while still catching material over-charges.

## Running the import (after CSVs land)

1. Place CSVs in `$APPLCSF/$APPLIN/inbound/` (or SQL*Loader into the interface).
2. Submit **Payables Open Interface Import** with the matching `SOURCE` /
   `GROUP_ID`.
3. Review the import audit + rejections report; `HOLD` invoices route to AME.
